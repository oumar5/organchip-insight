.PHONY: backend-dev backend-test backend-lint frontend-dev frontend-build frontend-typecheck test-e2e test-e2e-real test-release-persistence test-real-images release-audit release-checksums release-checksums-check report-pdf report-pdf-check benchmark-summary check docker-up docker-down data-fetch data-verify data-audit split-ooc split-ooc-campaign-v2 train-ooc-baseline evaluate-ooc-comparators-v2 benchmark-bbbc019 benchmark-bbbc019-microsam build-bbbc038-subset benchmark-bbbc038-instances cnn-build-manifests cnn-stage-kaggle-source cnn-stage-kaggle-ablation cnn-protocol-test cnn-smoke cnn-export cnn-archive cnn-notebook-check

MICROSAM_PYTHON ?= conda run --name organchip-microsam python
CNN_PYTHON ?= conda run --name organchip-ooc-cnn-cpu python
CNN_RUN_ID ?= smoke-local-manual
CNN_CHECKPOINT ?=
CNN_CHECKPOINT_SHA256 ?=
CNN_SELECTION_REPORT ?=
CNN_SELECTION_REPORT_SHA256 ?=
CNN_EXPORT_DIR ?=
CNN_RUN_DIRECTORY ?=
CNN_ARCHIVE_OUTPUT ?=
CNN_SOURCE_BUNDLE_SHA256 ?=
CNN_SOURCE_COMMIT ?=
CNN_ABLATION ?=

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

test-e2e:
	./scripts/run-e2e.sh

test-e2e-real:
	ORGANCHIP_REAL_E2E_MANIFEST="$(CURDIR)/data/manifests/product-real-smoke-v1.json" ./scripts/run-e2e.sh

test-release-persistence:
	./scripts/validate_release_persistence.sh

test-real-images:
	uv run --project backend python backend/scripts/run_real_image_smoke.py

release-audit:
	uv run --project backend python backend/scripts/audit_release_tree.py

release-checksums:
	uv run --project backend python backend/scripts/build_release_checksums.py

release-checksums-check:
	uv run --project backend python backend/scripts/build_release_checksums.py --check

report-pdf:
	uv run --project backend --extra report python backend/scripts/build_technical_report_pdf.py

report-pdf-check:
	uv run --project backend --extra report python backend/scripts/build_technical_report_pdf.py --check

benchmark-summary:
	uv run --project backend python backend/evaluation/build_benchmark_summary.py

check: backend-lint backend-test frontend-typecheck frontend-build cnn-notebook-check release-audit release-checksums-check report-pdf-check
	uv run --project backend python backend/evaluation/build_benchmark_summary.py --check
	docker compose config --quiet

data-fetch:
	uv run --project backend python backend/scripts/acquire_datasets.py

data-verify:
	uv run --project backend python backend/scripts/acquire_datasets.py --verify-only

data-audit:
	uv run --project backend --extra ml python backend/evaluation/audit_data.py

split-ooc:
	uv run --project backend python backend/training/split_ooc.py --config backend/training/configs/ooc-grouped-split-v1.json

split-ooc-campaign-v2:
	uv run --project backend python backend/training/build_ooc_campaign_split.py --config backend/training/configs/ooc-campaign-split-v2.json

train-ooc-baseline:
	uv run --project backend --extra ml python backend/training/train_ooc_baseline.py --config backend/training/configs/ooc-handcrafted-baseline-v1.json

evaluate-ooc-comparators-v2:
	uv run --project backend --extra ml python backend/training/evaluate_ooc_comparators.py --config backend/training/configs/ooc-classification-comparators-campaign-v2.json

cnn-build-manifests:
	PYTHONPATH=backend uv run --project backend python -m training.ooc_cnn.build_manifests

cnn-stage-kaggle-source:
	uv run --project backend python backend/scripts/stage_ooc_kaggle_source.py --output "$(OUTPUT)"

cnn-stage-kaggle-ablation:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required"; exit 2)
	@test -n "$(CNN_ABLATION)" || (echo "CNN_ABLATION is required (a or b)"; exit 2)
	@test -n "$(CNN_SOURCE_BUNDLE_SHA256)" || (echo "CNN_SOURCE_BUNDLE_SHA256 is required"; exit 2)
	uv run --project backend python backend/scripts/stage_ooc_kaggle_ablation.py --variant "$(CNN_ABLATION)" --source-bundle-sha256 "$(CNN_SOURCE_BUNDLE_SHA256)" --output "$(OUTPUT)"

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

cnn-archive:
	@test -n "$(CNN_RUN_DIRECTORY)" || (echo "CNN_RUN_DIRECTORY is required"; exit 2)
	@test -n "$(CNN_ARCHIVE_OUTPUT)" || (echo "CNN_ARCHIVE_OUTPUT is required"; exit 2)
	@test -n "$(CNN_SOURCE_BUNDLE_SHA256)" || (echo "CNN_SOURCE_BUNDLE_SHA256 is required"; exit 2)
	@test -n "$(CNN_SOURCE_COMMIT)" || (echo "CNN_SOURCE_COMMIT is required"; exit 2)
	PYTHONPATH=backend uv run --project backend python -m training.ooc_cnn.cli archive --run-directory "$(CNN_RUN_DIRECTORY)" --output "$(CNN_ARCHIVE_OUTPUT)" --source-bundle-sha256 "$(CNN_SOURCE_BUNDLE_SHA256)" --source-commit "$(CNN_SOURCE_COMMIT)"

cnn-notebook-check:
	uv run --project backend python backend/scripts/check_ooc_cnn_notebook.py
	uv run --project backend python backend/scripts/build_runtime_probe_notebook.py --check

benchmark-bbbc019:
	uv run --project backend python backend/evaluation/evaluate.py --config backend/evaluation/configs/bbbc019-microfluidic.json

benchmark-bbbc019-microsam:
	cd backend && $(MICROSAM_PYTHON) -m evaluation.evaluate --config backend/evaluation/configs/bbbc019-microfluidic-microsam-vit-b-lm-apg.json

build-bbbc038-subset:
	uv run --project backend python backend/evaluation/build_bbbc038_subset.py

benchmark-bbbc038-instances:
	cd backend && $(MICROSAM_PYTHON) -m evaluation.evaluate_instances --config backend/evaluation/configs/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json

docker-up:
	docker compose up --build

docker-down:
	docker compose down
