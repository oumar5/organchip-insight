# Demonstration storyboard — English version

Target duration: **3:18**, leaving 1 minute 42 seconds below the five-minute
limit. The real product appears immediately. The English capture forces the
interface to English; the French capture forces it to French. Actions, public
data, and scene timing remain identical.

## Reproducible build

`make demo-video` starts an isolated Docker stack, verifies the three public
image hashes, records one Playwright capture per language, and then uses Demo
Studio to add local neural narration, a Rhubarb-synchronized presenter,
licensed music, and subtitles. The frozen test set is never opened.
`make demo-video-check` verifies duration, codecs, resolution, size, the audio
track, and seven subtitle scenes.

## Shot list

### 0:00–0:18 — One auditable experiment

State the promise: images, measurements, provenance, and scientific limits
inside one local experiment.

### 0:18–0:50 — A protocol before analysis

Create the experiment, record its objective, and import the three public,
hash-locked images. Show that upload is separate from inference.

### 0:50–1:26 — Local and source-faithful analysis

Open the TIFF, distinguish the 8-bit PNG preview from the original source,
and run the weight-free adaptive CPU engine.

### 1:26–1:56 — Measurements with explicit limits

Compare source and overlay. Show connected components, pixel-based geometry,
and the reservation that prevents components from being presented as
validated cells.

### 1:56–2:16 — Reproducible exports

Download JSON and CSV, then show the evidence and provenance panel.

### 2:16–2:52 — Accuracy and cost together

Show BBBC019, BBBC038, iOrganoAssay, intervals, time, memory, decisions, and
report hashes.

### 2:52–3:18 — Honest abstention

Show the engine registry and the unavailable or abstaining experimental CNN.
Close on acquisition shortcuts, the unopened frozen test, checksums, and
explicit limitations.

## Checks before publication

- duration at or below 5:00;
- interface, narration, and subtitles use the same language;
- presenter visible during narration and music covered by its licence;
- no secret, personal path, or frozen-test data;
- repository, report, and video accessible without authentication after publication.
