.PHONY: backend-dev backend-test backend-lint frontend-dev frontend-build frontend-typecheck check docker-up docker-down data-fetch data-verify data-audit split-ooc benchmark-bbbc019 benchmark-bbbc019-microsam

MICROSAM_ENV ?= $(CURDIR)/data/cache/microsam-env

backend-dev:
	uv run --project backend uvicorn app.main:app --reload

backend-test:
	uv run --project backend --extra dev pytest backend/tests

backend-lint:
	uv run --project backend --extra dev ruff check backend/app backend/tests backend/inference.py backend/training backend/evaluation backend/scripts

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	npm --prefix frontend run build

frontend-typecheck:
	npm --prefix frontend run typecheck

check: backend-lint backend-test frontend-typecheck frontend-build
	docker compose config --quiet

data-fetch:
	uv run --project backend python backend/scripts/acquire_datasets.py

data-verify:
	uv run --project backend python backend/scripts/acquire_datasets.py --verify-only

data-audit:
	uv run --project backend --extra ml python backend/evaluation/audit_data.py

split-ooc:
	uv run --project backend python backend/training/split_ooc.py --config backend/training/configs/ooc-grouped-split-v1.json

benchmark-bbbc019:
	uv run --project backend python backend/evaluation/evaluate.py --config backend/evaluation/configs/bbbc019-microfluidic.json

benchmark-bbbc019-microsam:
	cd backend && conda run -p $(MICROSAM_ENV) python -m evaluation.evaluate --config backend/evaluation/configs/bbbc019-microfluidic-microsam-vit-b-lm-apg.json

docker-up:
	docker compose up --build

docker-down:
	docker compose down
