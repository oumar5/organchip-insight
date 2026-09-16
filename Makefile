.PHONY: backend-dev backend-test frontend-dev frontend-build docker-up docker-down

backend-dev:
	cd backend && uvicorn app.main:app --reload

backend-test:
	cd backend && pytest

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

