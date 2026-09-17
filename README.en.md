# OrganChip Insight

[Version française](README.md)

OrganChip Insight is a local, reproducible microscopy-image analysis platform
for organ-on-chip experiments.

It can create an experiment, import images, run training-free segmentation,
inspect overlays, export per-image results, and recover the experiment after a
restart. All current outputs are **exploratory**. They are neither a diagnosis
nor an automated biological conclusion.

## What the platform provides

- responsive React and TypeScript interface;
- FastAPI backend documented with OpenAPI;
- persistent experiments and results in SQLite;
- decoded uploads with file-size, pixel-count, and binary-duplicate checks;
- separate import and analysis steps, detailed rejections, and 16-bit
  grayscale TIFF support;
- CPU-only adaptive segmentation with no learned weights;
- connected-component, area, diameter, intensity, contrast, and relative
  contrast measurements explicitly labelled as heuristic;
- inspectable segmentation overlays;
- transparent engine registry with availability and scientific limits;
- optional ONNX CNN demonstrator that always abstains;
- complete JSON and per-image CSV exports;
- the same inference pipeline through the interface, API, and CLI;
- reproducible MobileNetV3 experimental pipeline with isolated `smoke`,
  `validation`, and `final-eval` modes;
- Docker Compose, unit tests, and an end-to-end Playwright browser scenario;
- a benchmark comparison generated from versioned scientific reports.

The connected-component count has **not** been validated as a cell or nucleus
count on the competition organ-on-chip images.

## Recommended start

Prerequisite: Docker Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- application: <http://localhost:8080>
- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>

Data is persisted in the `organchip_data` Docker volume.

The standard stack exposes the adaptive engine and reports the experimental
CNN as unavailable until its verified weight bundle is mounted. To run the
optional ONNX demonstrator with the locally authorized bundle:

```bash
export ORGANCHIP_QUALITY_MODEL_DIR_HOST="$(pwd)/data/experiments/ooc-cnn/kaggle-validation-campaign-v2-gray448/onnx"
docker compose -f docker-compose.yml -f docker-compose.quality.yml up --build
```

The Compose overlay mounts that directory read-only, and the runtime verifies
three SHA-256 identities before enabling the engine.

If a port is already in use, edit `.env` without changing the code:

```dotenv
ORGANCHIP_BACKEND_PORT=18000
ORGANCHIP_FRONTEND_PORT=18080
```

## Local development

Run the backend from the repository root:

```bash
uv sync --project backend --extra dev
uv run --project backend uvicorn app.main:app --reload
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the backend.

## Command-line inference

```bash
cd backend
uv run python inference.py image-1.png image-2.tif --output-dir artifacts/demo
```

The command writes the overlays and a traceable `result.json`.

## Verification

```bash
make check
```

The isolated browser scenario starts a disposable Docker stack, creates an
experiment, imports a synthetic image, runs the adaptive analysis, checks the
overlay and scientific reservations, verifies the benchmark view and JSON/CSV
downloads, audits text size and color contrast, and then removes its containers
and volume:

```bash
npm --prefix frontend exec playwright install chromium
make test-e2e
```

## Public data and benchmarks

The bounded data acquisition is checksum-verified and does not download the
6.7 GB organ-on-chip archive:

```bash
make data-fetch
make data-audit
make benchmark-bbbc019
```

Raw data remains under `data/raw/` and outside Git. Manifests, audit outputs,
and versioned results are described in [data/README.md](data/README.md).

The interface comparison is generated from locked JSON reports rather than
hand-entered values:

```bash
make benchmark-summary
```

On the 13 external BBBC019 DIC images, µSAM improves foreground segmentation
over the adaptive baseline but costs about 43 seconds per image and 8.7 GB of
memory in the measured CPU environment. On the preregistered 12-image BBBC038
instance audit, it fails two of three promotion criteria. µSAM therefore
remains an isolated benchmark; the adaptive engine remains the product engine.
Neither external benchmark validates cell counting on the competition images.

## Classification result and scientific boundary

The organ-on-chip CNN study is closed after the GPU validation and the A/B
ablations. No configuration met the preregistered balanced-accuracy floor for
both acquisition modes, and the frozen test set was never opened.

The fixed conclusion is:

> On this validation, no robust quality signal independent of acquisition and
> culture metadata is demonstrated; the residual observed in RGB for run B is
> modest, measured in-sample, and cannot be distinguished from a selection
> effect.

Run B can only be exposed as an experimental ONNX demonstrator. It always
returns “Needs review,” presents its softmax as uncalibrated, displays the
acquisition mode and provenance hashes, and makes no automatic good/bad
decision. The product quality-control path remains the adaptive engine plus
metadata. See the
[classification counter-audit](docs/audit-2026-09-17-classification-cnn.md)
and the [ONNX product REX](docs/retours-experience/2026-09-17-demonstrateur-cnn-onnx.md).

Model weights remain outside Git. Without ONNX Runtime or a conforming bundle,
the engine stays visible but unavailable and adaptive analysis still works.

## Architecture

```text
React frontend
    -> FastAPI API
        -> SQLite: experiments and results
        -> files: uploaded images and overlays
        -> engine registry
            -> adaptive segmentation v1 (available)
            -> run B CNN quality demonstrator (experimental, optional bundle, abstains)
            -> µSAM (experimental, isolated benchmark)
            -> Cellpose (licence review)
```

## Documentation

Start with the [documentation index](docs/README.md), then see:

- [product vision](docs/product-brief.md);
- [training-free inference](docs/inference.md);
- [research and decisions](docs/research.md);
- [data strategy](docs/data-strategy.md);
- [validation plan](docs/validation.md);
- [submission roadmap](docs/roadmap.md).

## Challenge positioning

Planned category: **Tool & Platform** for the
[AI4S Open Innovation: AI for Life Science challenge](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien),
the international track of the 5th Pazhou Algorithm Competition.

The repository emphasizes a complete and reproducible analysis workflow,
explicit uncertainty, acquisition-shortcut audits, a locked test set, and
scientific limits that remain visible in the product. The remaining work is
release preparation and submission material, not additional model selection.
