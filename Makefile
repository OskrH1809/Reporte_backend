.PHONY: up down logs migrations-check lint test audit check

up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
migrations-check:
	docker compose run --rm --build api alembic check
lint:
	docker compose run --rm --build api ruff check .
	docker compose run --rm --build api ruff format --check .
	npm --prefix frontend run lint
	npm --prefix frontend run format:check
test:
	docker compose run --rm --build api pytest -q
	npm --prefix frontend run test
audit:
	gitleaks detect --no-git -v
	docker compose run --rm --build api sh -c "bandit -r app -ll && pip-audit"
	npm --prefix frontend audit --audit-level=high
check: migrations-check lint test audit
