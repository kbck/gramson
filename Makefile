.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
HOST ?= 127.0.0.1
PORT ?= 8765

.PHONY: help setup setup-release generate example lint lint-openapi test check build check-dist serve

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV_PYTHON):
	$(PYTHON) -m venv "$(VENV)"

setup: $(VENV_PYTHON) ## Create the virtual environment and install the CLI and development dependencies
	"$(VENV_PYTHON)" -m pip install -r requirements-dev.txt
	"$(VENV_PYTHON)" -m pip install -e .

setup-release: setup ## Install development and release tooling
	"$(VENV_PYTHON)" -m pip install -r requirements-release.txt

generate: ## Generate JSON Schemas from the operator specification
	"$(VENV_PYTHON)" tools/generate_schema.py

example: ## Generate and validate the ready-to-run core extension example
	"$(VENV_PYTHON)" -m gramson generate --manifest examples/extension/language.yaml --output-directory build/examples/extension
	"$(VENV_PYTHON)" -m gramson validate examples/extension/expressions/nested.yaml --schema build/examples/extension/expression.schema.yaml
	"$(VENV_PYTHON)" -m gramson validate examples/extension/expressions/nested.json --schema build/examples/extension/expression.schema.yaml

lint: lint-openapi ## Run specification linting

lint-openapi: ## Validate the OpenAPI document and its external references
	"$(VENV_PYTHON)" -m openapi_spec_validator docs/openapi.yaml

test: ## Run all tests, including generated-schema freshness checks
	"$(VENV_PYTHON)" -m unittest discover -s tests -v

check: lint test ## Run lint and tests without regenerating files

build: ## Build a source distribution and a wheel from that source distribution
	"$(VENV_PYTHON)" -m build

check-dist: build ## Check package metadata, bundled schemas, and installed CLI
	"$(VENV_PYTHON)" tools/check_distribution.py dist

serve: generate ## Generate schemas and serve the Swagger viewer locally
	@printf 'Swagger viewer: http://%s:%s/docs/\n' "$(HOST)" "$(PORT)"
	"$(VENV_PYTHON)" -m http.server "$(PORT)" --bind "$(HOST)"
