.PHONY: backend-dev backend-test backend-lint frontend-dev frontend-build frontend-typecheck check docker-up docker-down data-fetch data-verify data-audit split-ooc train-ooc-baseline benchmark-bbbc019 benchmark-bbbc019-microsam cnn-build-manifests cnn-protocol-test cnn-smoke cnn-export cnn-notebook-check

MICROSAM_PYTHON ?= conda run --name organchip-microsam python
CNN_PYTHON ?= conda run --name organchip-ooc-cnn-cpu python
CNN_RUN_ID ?= smoke-local-manual
CNN_CHECKPOINT ?=
CNN_CHECKPOINT_SHA256 ?=
CNN_SELECTION_REPORT ?=
CNN_SELECTION_REPORT_SHA256 ?=
CNN_EXPORT_DIR ?=

backend-dev:
	uv run --project backend uvicorn app.main:app --reload

backend-test:
	uv run --project backend --extra dev --extra ml pytest backend/tests

backend-lint:
	uv run --project backend --extra dev ruff check backend/app backend/tests backend/inference.py backend/training backend/evaluation backend/scripts

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	npm --prefix frontend run build

frontend-typecheck:
	npm --prefix frontend run typecheck

check: backend-lint backend-test frontend-typecheck frontend-build cnn-notebook-check
	docker compose config --quiet

data-fetch:
	uv run --project backend python backend/scripts/acquire_datasets.py

data-verify:
	uv run --project backend python backend/scripts/acquire_datasets.py --verify-only

data-audit:
	uv run --project backend --extra ml python backend/evaluation/audit_data.py

split-ooc:
	uv run --project backend python backend/training/split_ooc.py --config backend/training/configs/ooc-grouped-split-v1.json

train-ooc-baseline:
	uv run --project backend --extra ml python backend/training/train_ooc_baseline.py --config backend/training/configs/ooc-handcrafted-baseline-v1.json

cnn-build-manifests:
	PYTHONPATH=backend uv run --project backend python -m training.ooc_cnn.build_manifests

cnn-protocol-test:
	uv run --project backend --extra dev pytest -q backend/tests/test_ooc_cnn_protocol.py backend/tests/test_ooc_cnn_data.py backend/tests/test_ooc_cnn_metrics.py backend/tests/test_ooc_cnn_runtime.py

cnn-smoke:
	PYTHONPATH=backend $(CNN_PYTHON) -m training.ooc_cnn.cli train --mode smoke --device cpu --run-id $(CNN_RUN_ID)

cnn-export:
	@test -n "$(CNN_CHECKPOINT)" || (echo "CNN_CHECKPOINT is required"; exit 2)
	@test -n "$(CNN_CHECKPOINT_SHA256)" || (echo "CNN_CHECKPOINT_SHA256 is required"; exit 2)
	@test -n "$(CNN_SELECTION_REPORT)" || (echo "CNN_SELECTION_REPORT is required"; exit 2)
	@test -n "$(CNN_SELECTION_REPORT_SHA256)" || (echo "CNN_SELECTION_REPORT_SHA256 is required"; exit 2)
	@test -n "$(CNN_EXPORT_DIR)" || (echo "CNN_EXPORT_DIR is required"; exit 2)
	PYTHONPATH=backend $(CNN_PYTHON) -m training.ooc_cnn.cli export --checkpoint "$(CNN_CHECKPOINT)" --checkpoint-sha256 "$(CNN_CHECKPOINT_SHA256)" --selection-report "$(CNN_SELECTION_REPORT)" --selection-report-sha256 "$(CNN_SELECTION_REPORT_SHA256)" --output-directory "$(CNN_EXPORT_DIR)"

cnn-notebook-check:
	uv run --project backend python backend/scripts/check_ooc_cnn_notebook.py
	uv run --project backend python backend/scripts/build_runtime_probe_notebook.py --check

benchmark-bbbc019:
	uv run --project backend python backend/evaluation/evaluate.py --config backend/evaluation/configs/bbbc019-microfluidic.json

benchmark-bbbc019-microsam:
	cd backend && $(MICROSAM_PYTHON) -m evaluation.evaluate --config backend/evaluation/configs/bbbc019-microfluidic-microsam-vit-b-lm-apg.json

docker-up:
	docker compose up --build

docker-down:
	docker compose down
