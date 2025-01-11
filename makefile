# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
TESTS = tests/
SRC = src/
REQS = requirements.txt

.PHONY: install
install: venv # Install dependencies
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQS)

.PHONY: process-data
process-data: # Process the data
	$(PYTHON) process_company_facts.py

.PHONY: fmt
fmt:
	@find test models process_company_facts.py -type f -name '*.py' | xargs black