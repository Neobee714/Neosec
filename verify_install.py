#!/usr/bin/env python3
"""Neosec installation verification script."""

import sys
from pathlib import Path


def check_python_version():
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
        return True

    print(f"[FAIL] Python {version.major}.{version.minor}.{version.micro}; requires 3.10+")
    return False


def check_imports():
    print("\nChecking dependencies...")
    packages = {
        "typer": "Typer",
        "rich": "Rich",
        "yaml": "PyYAML",
        "aiofiles": "aiofiles",
    }

    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"[OK] {name}")
        except ImportError:
            print(f"[FAIL] {name}")
            all_ok = False

    return all_ok


def check_package_module():
    print("\nChecking package import...")
    try:
        import neobee

        print("[OK] neobee module import")
        print(f"      version: {neobee.__version__}")
        return True
    except ImportError as e:
        print(f"[FAIL] neobee module import: {e}")
        return False


def check_cli_command():
    print("\nChecking CLI command...")
    import shutil

    if shutil.which("neosec"):
        print("[OK] neosec command found")
        return True

    print("[FAIL] neosec command not found")
    print("       activate your virtualenv or install the package first")
    return False


def check_templates():
    print("\nChecking builtin templates...")
    try:
        builtin_dir = Path(__file__).parent / "src" / "neobee" / "templates"

        if not builtin_dir.exists():
            print(f"[FAIL] builtin template dir not found: {builtin_dir}")
            return False

        templates = list(builtin_dir.glob("*.json"))
        print(f"[OK] found {len(templates)} templates")
        for tmpl in templates:
            print(f"     - {tmpl.stem}")
        return True
    except Exception as e:
        print(f"[FAIL] template check error: {e}")
        return False


def main():
    print("=" * 60)
    print("Neosec installation verification")
    print("=" * 60)

    checks = [
        ("Python", check_python_version),
        ("Dependencies", check_imports),
        ("Package", check_package_module),
        ("CLI", check_cli_command),
        ("Templates", check_templates),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"[FAIL] {name} check crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Verification summary")
    print("=" * 60)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"{name:15} {status}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\nAll checks passed.")
        print("Next steps:")
        print("  1. neosec init")
        print("  2. neosec workflow --list-templates")
        return 0

    print("\nSome checks failed.")
    print("Suggestions:")
    print("  1. Ensure Python 3.10+ is installed")
    print("  2. Run: poetry install (or pip install -e .)")
    print("  3. Activate your virtualenv")
    return 1


if __name__ == "__main__":
    sys.exit(main())
