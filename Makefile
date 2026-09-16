.PHONY: backend-dev backend-test backend-lint frontend-dev frontend-build frontend-typecheck check docker-up docker-down

backend-dev:
	uv run --project backend uvicorn app.main:app --reload

backend-test:
	uv run --project backend pytest backend/tests

backend-lint:
	uv run --project backend ruff check backend/app backend/tests backend/inference.py backend/training backend/evaluation

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	npm --prefix frontend run build

frontend-typecheck:
	npm --prefix frontend run typecheck

check: backend-lint backend-test frontend-typecheck frontend-build
	docker compose config --quiet

docker-up:
	docker compose up --build

docker-down:
	docker compose down
