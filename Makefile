.PHONY: help install test lint clean run-scan validate

# 默认目标
help:
	@echo "NeoSec - 企业级自动化渗透测试框架"
	@echo ""
	@echo "可用命令:"
	@echo "  make install      - 安装 Python 依赖"
	@echo "  make test         - 运行所有测试"
	@echo "  make lint         - 代码风格检查"
	@echo "  make clean        - 清理临时文件"
	@echo "  make validate     - 验证依赖和配置"
	@echo "  make run-scan     - 运行示例扫描（需要设置 TARGET 变量）"
	@echo ""
	@echo "示例:"
	@echo "  make run-scan TARGET=192.168.1.1"

# 安装依赖
install:
	pip install -r requirements.txt

# 运行测试
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# 代码风格检查
lint:
	@echo "运行 flake8..."
	flake8 src/ --max-line-length=120 --ignore=E501,W503
	@echo "运行 mypy..."
	mypy src/ --ignore-missing-imports

# 清理临时文件
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ dist/ build/

# 验证依赖
validate:
	python main.py validate

# 运行扫描（需要设置 TARGET 变量）
run-scan:
	@if [ -z "$(TARGET)" ]; then \
		echo "错误: 请设置 TARGET 变量"; \
		echo "示例: make run-scan TARGET=192.168.1.1"; \
		exit 1; \
	fi
	python main.py scan -t $(TARGET) -w configs/default_workflow.yaml -v

# 列出工具
list-tools:
	python main.py list-tools

# 初始化配置
init-config:
	python main.py init-config
