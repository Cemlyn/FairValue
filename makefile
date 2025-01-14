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

.PHONY: test
test: # run unit tests
	pytest test

.PHONY: fmt

# Check the operating system
ifeq ($(OS),Windows_NT)
    # Use cmd.exe to execute the Windows command
    #FMT_CMD = cmd /C "for /r %%G in (*.py) do black %%G"
	FMT_CMD = echo "heelo"
else
    # Use Unix-like command
    FMT_CMD = find test models process_company_facts.py -type f -name '*.py' | xargs black
endif

# Rule to format Python files
fmt:
	@$(FMT_CMD)