# Makefile mirrors tasks.py. On machines without GNU make (e.g. stock Windows),
# use: python tasks.py <target>
#
# Prefers `uv` when available, otherwise falls back to the .venv python.

PY := python
RUN := $(PY) tasks.py

.PHONY: setup run mock-apis sandbox test lint type eval ui deploy-local

setup:        ## Create venv + install package and dev deps
	$(RUN) setup

run:          ## Boot the FastAPI service on :8000
	$(RUN) run

mock-apis:    ## Boot the mock partner APIs on :9000
	$(RUN) mock-apis

sandbox:      ## Boot mock-apis + service + dashboard
	$(RUN) sandbox

test:         ## Run the pytest suite
	$(RUN) test

lint:         ## Ruff + Black format-check
	$(RUN) lint

type:         ## mypy type-check
	$(RUN) type

eval:         ## Run eval harness + scorecard
	$(RUN) eval

ui:           ## Run the React dashboard dev server
	$(RUN) ui

deploy-local: ## Provision LocalStack + smoke test
	$(RUN) deploy-local
