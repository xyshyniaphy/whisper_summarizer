.PHONY: help lint format lint-fix test test-cov clean run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: ## Run Ruff linting
	ruff check .

format: ## Format code with Ruff
	ruff format .

lint-fix: ## Fix linting issues automatically
	ruff check --fix .
	ruff format .

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=app --cov-report=html --cov-report=term-missing

clean: ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/

run: ## Run the development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
