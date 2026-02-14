.PHONY: help dev test lint clean migrate reset-db

# 默认目标
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start development server
	@uvicorn main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	@pytest tests/ -v --cov=app --cov-report=html

lint: ## Run code linting
	@flake8 app/
	@black --check app/
	@mypy app/

format: ## Format code
	@black app/
	@isort app/

migrate: ## Run database migrations
	@alembic upgrade head

migrate-create: ## Create new migration
	@alembic revision --autogenerate -m "$(MSG)"

reset-db: ## Reset database
	@alembic downgrade base
	@alembic upgrade head

init-db: ## Initialize database with seed data
	@python scripts/init_db.py

docker-up: ## Start Docker containers
	@docker-compose up -d

docker-down: ## Stop Docker containers
	@docker-compose down

docker-logs: ## Show Docker logs
	@docker-compose logs -f api

clean: ## Clean up
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '.pytest_cache' -delete
	@rm -rf htmlcov/ .coverage

install: ## Install dependencies
	@pip install -r requirements.txt
