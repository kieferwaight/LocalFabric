PYTHON_VERSION ?= 3.14

.PHONY: help venv clean-pycache clean-egg-info clean-venv clean-lock clean \
        install install-dev install-all lock sync reset docs

help:
	@echo "Targets:"
	@echo "  venv           Create .venv with uv (python $(PYTHON_VERSION))"
	@echo "  clean-pycache  Remove all __pycache__ directories"
	@echo "  clean-egg-info Remove all *.egg-info directories"
	@echo "  clean-venv     Remove .venv"
	@echo "  clean-lock     Remove uv.lock"
	@echo "  clean          Run all clean-* targets"
	@echo "  lock           Regenerate uv.lock from pyproject.toml"
	@echo "  sync           uv sync (locked install, base deps only)"
	@echo "  install        Alias for 'sync'"
	@echo "  install-dev    uv sync --extra dev"
	@echo "  install-all    uv sync --all-extras"
	@echo "  docs           Regenerate README.md from README.template.md + pyproject.toml"
	@echo "  reset          clean + venv + install-all (full rebuild)"

venv:
	uv venv --python $(PYTHON_VERSION)

clean-pycache:
	find . -type d -name "__pycache__" -exec rm -rf {} +

clean-egg-info:
	find . -type d -name "*.egg-info" -exec rm -rf {} +

clean-venv:
	rm -rf .venv

clean-lock:
	rm -rf uv.lock

clean: clean-pycache clean-egg-info clean-venv clean-lock

lock:
	uv lock

sync:
	uv sync

install: sync

install-dev:
	uv sync --extra dev

install-all:
	uv sync --all-extras

docs:
	.venv/bin/python 02_core/runtimes/yaml/interpreter.py 06_workflows/generate-docs.yaml generate-docs

reset: clean venv install-all
