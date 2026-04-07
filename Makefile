.PHONY: dev test lint format check

dev:
	uvicorn src.flight_query_engine.main:app --reload --port 8000

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=src/flight_query_engine --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

check: lint test
