.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_STAMP := $(VENV)/.installed-dev

.PHONY: install lint test verify

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(VENV_STAMP): pyproject.toml | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -U pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"
	touch $(VENV_STAMP)

install: $(VENV_STAMP)

lint: install
	$(VENV_PYTHON) -m ruff check dv_regression_lab tests

test: install
	$(VENV_PYTHON) -m pytest -q

verify: lint test
