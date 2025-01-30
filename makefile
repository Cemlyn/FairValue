# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
TESTS = tests/
SRC = FairValue/

.PHONY: install
install: venv # Install dependencies
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQS)

.PHONY: process-data
process-data: # Process the data
	$(PYTHON) process_company_facts.py

.PHONY: test
test: # run unit tests
	pytest

.PHONY: fmt
fmt:
	black --config pyproject.toml .

.PHONY: lint
lint: # Run pylint on the source code
	pylint $(SRC)
