.PHONY: help install dev test lint format security clean performance setup ci run

help:  ## Show available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"

setup:  ## Setup development environment
	$(MAKE) dev
	pre-commit install

run:  ## Run development server
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

run-docker:  ## Run with Docker
	docker-compose up --build

test:  ## Run all tests
	pytest tests/ -v

test-unit:  ## Run unit tests only
	pytest tests/ -v -m "unit"

test-integration:  ## Run integration tests only
	pytest tests/ -v -m "integration"

test-performance:  ## Run performance tests
	pytest tests/performance/ -v --benchmark-only

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:  ## Run linter
	ruff check .

format:  ## Format code
	ruff format .

format-check:  ## Check if code is formatted
	ruff format --check .

type-check:  ## Run type checker
	mypy src/ --ignore-missing-imports

security:  ## Run security checks
	bandit -r src/ --severity-level medium
	safety check

quality:  ## Run all quality checks
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security

performance-load:  ## Run load tests with Locust
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

clean:  ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache .ruff_cache dist/ build/

ci:  ## Run CI pipeline locally
	$(MAKE) quality
	$(MAKE) test-cov