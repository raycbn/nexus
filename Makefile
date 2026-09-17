.SHELL = cmd.exe
.SHELLFLAGS = /c

.PHONY: help install lint typecheck test test-all clean

PYTHON := python
PIP := pip

help:
	@echo "NEXUS Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install project and dev dependencies"
	@echo "  lint         Run ruff linter"
	@echo "  typecheck    Run mypy type checker"
	@echo "  test         Run pytest"
	@echo "  test-all     Run lint, typecheck, and test"
	@echo "  clean        Remove generated files"

install:
	$(PIP) install -e ".[dev]"

lint:
	ruff check apps/ packages/ tests/

typecheck:
	mypy apps/ packages/

test:
	pytest tests/

test-all: lint typecheck test

clean:
	@echo "Cleaning generated files..."
	rmdir /s /q __pycache__ 2>nul
	rmdir /s /q .pytest_cache 2>nul
	rmdir /s /q .mypy_cache 2>nul
	rmdir /s /q .ruff_cache 2>nul
	rmdir /s /q htmlcov 2>nul
	rmdir /s /q dist 2>nul
	rmdir /s /q build 2>nul
	del /s *.pyc 2>nul
	del /s *.pyo 2>nul
	del /s .coverage 2>nul
