PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHONPATH := src

.PHONY: help venv install check compile test schema-check examples-check security-check

help: ## List available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "%-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON) ## Create .venv and install the package in editable mode
	$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	$(VENV_PYTHON) -m pip install -e .

install: $(VENV_PYTHON) ## Install or update the package in editable mode in .venv
	$(VENV_PYTHON) -m pip install -e .

check: compile test schema-check examples-check security-check ## Run canonical local validation

compile: ## Compile Python source and tests
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m compileall -q src tests

test: ## Run unit tests
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests/unit

schema-check: ## Validate checked-in JSON schema files are parseable
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m trusted_network_registry.cli validate-config examples/publisher-config.example.toml
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m trusted_network_registry.cli validate-registry examples/registry.example.json

examples-check: ## Render example config and generated tfvars JSON
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m trusted_network_registry.cli publish --once --config examples/publisher-config.example.toml --output .check-output/registry.example.json --tfvars-output .check-output/trusted-registry.auto.tfvars.json --generated-at 2026-05-17T00:00:00Z

security-check: ## Run local public-safety checks
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest tests.unit.test_public_safety
