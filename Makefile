PYTHON ?= python3
PYTHONPATH := src

.PHONY: help check compile test schema-check examples-check security-check

help: ## List available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "%-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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
