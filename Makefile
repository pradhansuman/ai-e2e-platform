.PHONY: install install-browsers dev test lint docker-up docker-down migrate migration

install:
	cd backend && pip install -r requirements.txt

install-browsers:
	python -m playwright install --with-deps chromium

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && pytest ../../tests -q

lint:
	cd backend && python -m compileall app

docker-up:
	docker compose up --build

docker-down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate
