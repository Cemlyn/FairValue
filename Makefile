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
	$(PYTHON) scripts/ingest_filings.py

.PHONY: unit-test
unit-test: # run unit tests
	pytest tests/unit

.PHONY: integration-test
integration-test: # run integration tests
	pytest tests/integration

.PHONY: test
test: # run unit tests
	pytest --cov tests  --cov-report=xml


.PHONY: test-stock-split-find
test-stock-split-find:
	pytest fairvalue/_stock_split_parser/tests/

.PHONY: fmt
fmt:
	black --config pyproject.toml .

.PHONY: lint
lint: # Run pylint on the source code
	pylint $(SRC)

.PHONY: stock-split-find
stock-split-find:
	python .\fairvalue\_stock_split_parser\extract_stock_splits.py --filepath .\fairvalue\_stock_split_parser\data\8K-2025-05-28-0001045810-25-000115.txt.gz --output_filepath .\results.json

.PHONY: stock-split-find-dir
stock-split-find-dir:
	python extract_stock_splits.py --dir .\fairvalue\_stock_split_parser\data --regex "8K-.*\.txt\.gz" --output_filepath .\results.json
