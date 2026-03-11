#!/usr/bin/env python3
"""
html_extraction - neosec内置脚本插件

从ffuf等工具发现的URL中批量抓取HTML，去除噪声节点后保存为文本。

输入 (stdin JSON):
  args:
    source        : context.results中的key（ffuf结果），与url_list二选一
    base_url      : URL前缀，用于拼接entries中的相对path（需配合source使用）
    url_list      : 直接指定URL列表，如 ["http://x.x.x.x/path"]
    filter_status : 只处理这些状态码（逗号分隔），默认 "200"
    timeout       : 单请求超时秒数，默认 10
    verify_ssl    : 是否验证SSL证书，默认 false
  context.results : 来自workflow上下文的工具结果
  result_dir      : ~/.neosec/result/<ip>/ 目录路径
  step_id         : 当前step id，用于命名输出文件

输出 (stdout JSON):
  status      : "success" | "error"
  pages       : 成功抓取的页面数
  output_file : 保存路径
  urls        : 处理的URL列表
  errors      : 失败的URL列表
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

# ── 依赖检查 ────────────────────────────────────────────────────────────────
try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print(json.dumps({
        "status": "error",
        "error": "缺少依赖: beautifulsoup4。请运行: pip install beautifulsoup4"
    }), flush=True)
    sys.exit(1)

try:
    import httpx
except ImportError:
    print(json.dumps({
        "status": "error",
        "error": "缺少依赖: httpx。请运行: pip install httpx"
    }), flush=True)
    sys.exit(1)


# ── 需要完全移除的标签（含内容）─────────────────────────────────────────────
_REMOVE_TAGS = {
    "script", "style", "svg", "canvas",
    "video", "audio", "iframe", "embed", "object",
    "noscript",
}

# ── 需要移除的属性 ────────────────────────────────────────────────────────────
_REMOVE_ATTRS = {
    "style", "onclick", "onload", "onerror", "onmouseover",
    "onmouseout", "onfocus", "onblur", "onchange", "onsubmit",
    "onkeydown", "onkeyup", "onkeypress",
}

# ── 外联资源标签（移除标签但不移除内容）────────────────────────────────────
_UNWRAP_RESOURCE_TAGS = {"img", "picture", "source", "track", "map", "area"}


def clean_html(html: str, url: str = "") -> str:
    """
    清理HTML：去除噪声节点，保留有语义价值的结构。

    保留：title, h1-h6, p, a(href), form, input, textarea,
          select, option, button, label, table, th, td, li,
          meta(name/content), header, main, nav, footer, section, article
    移除：script, style, svg, img, video, audio, iframe,
          外联CSS, HTML注释, 所有事件属性(onclick等)
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. 移除HTML注释
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 2. 移除噪声标签（含内容）
    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()

    # 3. 移除外联资源标签（img等，只移除标签不移除内容）
    for tag in soup.find_all(_UNWRAP_RESOURCE_TAGS):
        tag.decompose()

    # 4. 移除外联CSS/favicon的link标签，保留其他link
    for tag in soup.find_all("link"):
        rel = tag.get("rel", [])
        if isinstance(rel, list):
            rel_str = " ".join(rel).lower()
        else:
            rel_str = str(rel).lower()
        if any(r in rel_str for r in ("stylesheet", "icon", "preload", "prefetch", "dns-prefetch")):
            tag.decompose()

    # 5. 移除事件属性和style属性
    for tag in soup.find_all(True):
        for attr in _REMOVE_ATTRS:
            tag.attrs.pop(attr, None)
        # 移除data-*属性（噪声）
        data_attrs = [a for a in list(tag.attrs.keys()) if a.startswith("data-")]
        for attr in data_attrs:
            del tag.attrs[attr]
        # 移除class/id（对AI分析无帮助）
        tag.attrs.pop("class", None)
        tag.attrs.pop("id", None)

    # 6. 清理空白行
    text = str(soup)
    lines = [l.rstrip() for l in text.splitlines()]
    # 合并连续空行为单个空行
    result_lines: list[str] = []
    prev_empty = False
    for line in lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        result_lines.append(line)
        prev_empty = is_empty

    return "\n".join(result_lines).strip()


def build_url_list(
    args: dict,
    context_results: dict,
    filter_statuses: set[int],
) -> list[str]:
    """从args或context results构建要抓取的URL列表。"""
    # 直接指定URL列表
    if "url_list" in args:
        raw = args["url_list"]
        if isinstance(raw, str):
            return [u.strip() for u in raw.split(",") if u.strip()]
        if isinstance(raw, list):
            return [str(u) for u in raw]

    # 从ffuf等工具的结果中读取
    source_key = args.get("source", "")
    base_url = args.get("base_url", "").rstrip("/")

    if not source_key:
        return []

    source_data = context_results.get(source_key, {})
    entries = source_data.get("entries", [])

    urls: list[str] = []
    for entry in entries:
        status = entry.get("status")
        if filter_statuses and status not in filter_statuses:
            continue

        # 优先用entry自带的完整url字段
        url = entry.get("url", "")
        if not url and base_url:
            path = entry.get("path", "/")
            if not path.startswith("/"):
                path = "/" + path
            url = base_url + path

        if url:
            urls.append(url)

    return urls


def fetch_and_clean(
    urls: list[str],
    timeout: int,
    verify_ssl: bool,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    同步批量请求并清理HTML。
    返回: (成功列表[(url, cleaned_html)], 失败列表[(url, error)])
    """
    successes: list[tuple[str, str]] = []
    failures: list[tuple[str, str]] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; neosec-scanner/1.0)",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    with httpx.Client(
        timeout=timeout,
        verify=verify_ssl,
        follow_redirects=True,
        headers=headers,
    ) as client:
        for url in urls:
            try:
                resp = client.get(url)
                ct = resp.headers.get("content-type", "")
                if "html" not in ct.lower() and "text" not in ct.lower():
                    # 非HTML内容，跳过
                    failures.append((url, f"非HTML内容: {ct}"))
                    continue
                cleaned = clean_html(resp.text, url)
                successes.append((url, cleaned))
            except Exception as e:
                failures.append((url, str(e)))

    return successes, failures


def write_output(
    result_dir: str,
    step_id: str,
    successes: list[tuple[str, str]],
    failures: list[tuple[str, str]],
) -> str:
    """将清理后的HTML写入输出文件，返回文件路径。"""
    out_path = Path(result_dir) / f"{step_id}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    total = len(successes) + len(failures)
    lines.append(f"# HTML Extraction Results")
    lines.append(f"# Total: {total} URLs | Success: {len(successes)} | Failed: {len(failures)}")
    lines.append("")

    for i, (url, cleaned) in enumerate(successes, 1):
        lines.append(f"{'\u2550' * 60}")
        lines.append(f"[{i}/{len(successes)}] {url}")
        lines.append(f"{'\u2550' * 60}")
        lines.append(cleaned)
        lines.append("")

    if failures:
        lines.append(f"{'─' * 60}")
        lines.append("# 失败的URL:")
        for url, err in failures:
            lines.append(f"  ✗ {url}  ({err})")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


def main() -> None:
    # 读取stdin
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"stdin JSON解析失败: {e}"}), flush=True)
        sys.exit(1)

    args: dict = payload.get("args", {})
    context_results: dict = payload.get("context", {}).get("results", {})
    result_dir: str = payload.get("result_dir", ".")
    step_id: str = payload.get("step_id", "html_extraction")

    # 解析参数
    filter_status_str = str(args.get("filter_status", "200"))
    filter_statuses: set[int] = set()
    for s in filter_status_str.split(","):
        s = s.strip()
        if s.isdigit():
            filter_statuses.add(int(s))

    req_timeout = int(args.get("timeout", 10))
    verify_ssl = str(args.get("verify_ssl", "false")).lower() in ("true", "1", "yes")

    # 构建URL列表
    urls = build_url_list(args, context_results, filter_statuses)

    if not urls:
        print(json.dumps({
            "status": "success",
            "pages": 0,
            "urls": [],
            "errors": [],
            "output_file": "",
            "message": "未找到符合条件的URL",
        }), flush=True)
        return

    # 打印进度到stderr（不影响stdout JSON）
    print(f"[html_extraction] 开始处理 {len(urls)} 个URL...", file=sys.stderr, flush=True)

    # 抓取并清理
    successes, failures = fetch_and_clean(urls, req_timeout, verify_ssl)

    print(
        f"[html_extraction] 完成: {len(successes)} 成功, {len(failures)} 失败",
        file=sys.stderr, flush=True
    )

    # 写入结果文件
    output_file = ""
    if successes or failures:
        output_file = write_output(result_dir, step_id, successes, failures)
        print(f"[html_extraction] 已保存: {output_file}", file=sys.stderr, flush=True)

    # 输出JSON结果到stdout
    print(json.dumps({
        "status": "success",
        "pages": len(successes),
        "urls": [u for u, _ in successes],
        "errors": [{"url": u, "error": e} for u, e in failures],
        "output_file": output_file,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
