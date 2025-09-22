.PHONY: install setup run test lint clean

install:
	pip install -e .[dev]

setup:
	pre-commit install

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

run-docker:
	docker-compose up --build

test:
	pytest

lint:
	ruff check .
	ruff format .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f .coverage .coverage.*
