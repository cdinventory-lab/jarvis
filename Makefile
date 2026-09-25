.PHONY: venv install test lint demo run doctor clean

VENV ?= .venv
PY := $(VENV)/bin/python

venv:
	python3 -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(VENV)/bin/ruff check jarvis tests

demo:
	$(PY) -m jarvis --backend simulated --demo notepad

run:
	$(PY) -m jarvis

doctor:
	$(PY) -m jarvis --doctor

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
