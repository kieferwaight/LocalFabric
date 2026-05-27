PYTHON_VERSION ?= 3.12

.PHONY: help venv clean-pycache clean-egg-info clean-venv clean-lock clean \
        install install-dev install-all lock sync reset docs docs-all docs-check audit \
        format format-check lint lint-fix pre-commit-install

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
	@echo "  docs           Regenerate the YAML API reference + README via the docs workflow"
	@echo "  docs-all       Regenerate 18_docs/ — one page per repo-wide definition id"
	@echo "  docs-check     Verify 18_docs/ is up to date (exits non-zero if stale)"
	@echo "  audit          Run the classification-boundary audit workflow"
	@echo "  format         Auto-format py / yaml / md (ruff, yamlfix, mdformat)"
	@echo "  format-check   Check formatting without writing (CI mode)"
	@echo "  lint           Lint py + yaml (ruff check, yamllint); read-only"
	@echo "  lint-fix       Lint with autofix where supported"
	@echo "  pre-commit-install   Install the local pre-commit hook"
	@echo "  reset          clean + venv + install-all (full rebuild)"

# Files / dirs the formatters and linters should skip.
LINT_EXCLUDES := --exclude .venv --exclude 14_data --exclude 18_docs --exclude node_modules

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
	.venv/bin/python 02_core/runtimes/yaml/interpreter.py 06_workflows/docs.generate.workflow.yaml docs.generate.workflow

docs-all:
	.venv/bin/python -m core.runtimes.yaml.regenerate_docs

docs-check:
	.venv/bin/python -m core.runtimes.yaml.regenerate_docs --mode=check

audit:
	.venv/bin/python 02_core/runtimes/yaml/interpreter.py 06_workflows/audit.classifications.scan.workflow.yaml audit.classifications.scan.workflow

reset: clean venv install-all

# ── Format / lint ─────────────────────────────────────────────────────────────

format:
	.venv/bin/ruff format .
	# --exit-zero so a remaining unfixable lint doesn't block the rest of
	# the format pass (yamlfix / mdformat / block scalars).
	.venv/bin/ruff check --fix --exit-zero .
	find . -type f \( -name '*.yaml' -o -name '*.yml' \) \
	    -not -path './.venv/*' -not -path './14_data/*' \
	    -not -path './18_docs/*' -not -path './node_modules/*' \
	    -print0 | xargs -0 .venv/bin/yamlfix
	.venv/bin/python scripts/yaml_block_scalars.py
	find . -type f -name '*.md' \
	    -not -path './.venv/*' -not -path './18_docs/*' \
	    -not -path './node_modules/*' \
	    -print0 | xargs -0 .venv/bin/mdformat

format-check:
	.venv/bin/ruff format --check .
	find . -type f \( -name '*.yaml' -o -name '*.yml' \) \
	    -not -path './.venv/*' -not -path './14_data/*' \
	    -not -path './18_docs/*' -not -path './node_modules/*' \
	    -print0 | xargs -0 .venv/bin/yamlfix --check
	.venv/bin/python scripts/yaml_block_scalars.py --check
	find . -type f -name '*.md' \
	    -not -path './.venv/*' -not -path './18_docs/*' \
	    -not -path './node_modules/*' \
	    -print0 | xargs -0 .venv/bin/mdformat --check

lint:
	.venv/bin/ruff check .
	.venv/bin/yamllint .

lint-fix:
	.venv/bin/ruff check --fix .
	.venv/bin/yamllint .

pre-commit-install:
	.venv/bin/pre-commit install
