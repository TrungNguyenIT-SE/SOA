.PHONY: up down build logs ps reset test test-unit test-e2e

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

reset:
	docker compose down -v
	docker compose up --build -d

test-unit:
	docker compose run --rm payment python -m unittest discover -s tests -v
	docker compose run --rm notification python -m unittest discover -s tests -v

test-e2e:
	python tests/e2e/run_contract.py
	python tests/e2e/run_smoke.py
	python tests/e2e/run_concurrency.py
	python tests/e2e/run_resilience.py

test: test-unit test-e2e

