.PHONY: etl run test

etl:
	python -m app.backend.etl.sheets_to_parquet

run:
	uvicorn app.backend.main:app --reload &
	npm --prefix app/frontend run dev

test:
	pytest -q
