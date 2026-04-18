.PHONY: help install lint format typecheck security check check-all test test-all integration docker-up docker-down changelog clean clean-all doctor release

PYTEST = python3 -m pytest
RUFF = ruff
MYPY = mypy
BANDIT = bandit
SRC = sqlalchemy_cubrid
TESTS = test

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install in development mode with all dependencies
	pip install -e ".[dev]"
	pre-commit install

lint: ## Run linter and format checks
	$(RUFF) check $(SRC)/ $(TESTS)/
	$(RUFF) format --check $(SRC)/ $(TESTS)/

format: ## Auto-fix lint issues and format code
	$(RUFF) check --fix $(SRC)/ $(TESTS)/
	$(RUFF) format $(SRC)/ $(TESTS)/

typecheck: ## Run mypy type checking
	$(MYPY) $(SRC)/ --config-file=pyproject.toml

security: ## Run security scans (bandit)
	$(BANDIT) -r $(SRC)/ -c pyproject.toml

check: lint typecheck ## Run lint + typecheck

check-all: check security ## Run lint + typecheck + security

test: ## Run offline tests with coverage (no DB required)
	$(PYTEST) $(TESTS)/ -v \
		--ignore=$(TESTS)/test_integration.py \
		--ignore=$(TESTS)/test_suite.py \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-all: ## Run tests across all Python versions via tox
	tox

integration: docker-up ## Run integration tests against CUBRID Docker
	@echo "Waiting for CUBRID to be ready..."
	@sleep 10
	CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb" \
		$(PYTEST) $(TESTS)/test_integration.py -v
	$(MAKE) docker-down

docker-up: ## Start CUBRID Docker container
	docker compose up -d
	@echo "CUBRID container starting... Use 'docker compose logs -f' to monitor."

docker-down: ## Stop and remove CUBRID Docker container
	docker compose down -v

changelog: ## Generate changelog with git-cliff
	git-cliff --output CHANGELOG.md

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

clean-all: clean ## Remove all artifacts including .mypy_cache and .tox
	rm -rf .mypy_cache/ .tox/ htmlcov/

doctor: ## Check development environment
	@echo "Checking development environment..."
	@python3 --version || echo "ERROR: python3 not found"
	@$(RUFF) --version || echo "ERROR: ruff not found"
	@$(MYPY) --version || echo "ERROR: mypy not found"
	@$(BANDIT) --version || echo "ERROR: bandit not found"
	@pre-commit --version || echo "ERROR: pre-commit not found"
	@echo "All checks passed!"

release: ## Bump version in pyproject.toml and __init__.py
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=x.y.z"; exit 1; fi
	@echo "Bumping version to $(VERSION)..."
	@sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' sqlalchemy_cubrid/__init__.py
	@echo "Verifying consistency..."
	@PYPROJECT_VER=$$(grep -oP '^version = "\K[^"]+' pyproject.toml); \
	 INIT_VER=$$(python3 -c "import ast; print(next(node.value.value for node in ast.walk(ast.parse(open('sqlalchemy_cubrid/__init__.py').read())) if isinstance(node, ast.Assign) and any(t.id == '__version__' for t in node.targets if isinstance(t, ast.Name))))"); \
	 if [ "$$PYPROJECT_VER" != "$$INIT_VER" ]; then \
	   echo "ERROR: Version mismatch — pyproject.toml=$$PYPROJECT_VER, __init__.py=$$INIT_VER"; exit 1; \
	 fi
	@echo "Version $(VERSION) set in pyproject.toml and sqlalchemy_cubrid/__init__.py"
