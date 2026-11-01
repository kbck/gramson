.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
HOST ?= 127.0.0.1
PORT ?= 8765

.PHONY: help setup generate lint lint-openapi test check serve

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV_PYTHON):
	$(PYTHON) -m venv "$(VENV)"

setup: $(VENV_PYTHON) ## Create the virtual environment and install development dependencies
	"$(VENV_PYTHON)" -m pip install -r requirements-dev.txt

generate: ## Generate JSON Schemas from the operator specification
	"$(VENV_PYTHON)" tools/generate_schema.py

lint: lint-openapi ## Run specification linting

lint-openapi: ## Validate the OpenAPI document and its external references
	"$(VENV_PYTHON)" -m openapi_spec_validator docs/openapi.yaml

test: ## Run all tests, including generated-schema freshness checks
	"$(VENV_PYTHON)" -m unittest discover -s tests -v

check: lint test ## Run lint and tests without regenerating files

serve: generate ## Generate schemas and serve the Swagger viewer locally
	@printf 'Swagger viewer: http://%s:%s/docs/\n' "$(HOST)" "$(PORT)"
	"$(VENV_PYTHON)" -m http.server "$(PORT)" --bind "$(HOST)"
