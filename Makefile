.PHONY: init dev up test db-upgrade seed lint fmt

init:
	command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	uv sync
	uv run pre-commit install

dev:
	uv run uvicorn main:app --reload

up:
	@docker info >/dev/null 2>&1 || { echo "Docker daemon is not reachable. Start Docker Desktop (or the Docker daemon) and try again." >&2; exit 1; }
	docker compose up -d --wait postgres

test:
	@docker info >/dev/null 2>&1 || { echo "Docker daemon is not reachable. Start Docker Desktop (or the Docker daemon) and try again." >&2; exit 1; }
	docker compose up -d --wait postgres
	uv run pytest

db-upgrade:
	uv run alembic upgrade head

seed:
	uv run python -m app.seed

lint:
	uv run ruff check --fix .
	uv run ruff format .

fmt:
	uv run ruff format .
