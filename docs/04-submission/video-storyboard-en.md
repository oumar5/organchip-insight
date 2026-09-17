# Demonstration storyboard — English version

Controlled duration: **3:00**, leaving 2 minutes below the five-minute
limit. The real product appears immediately. The English capture forces the
interface to English; the French capture forces it to French. Actions, public
data, and scene timing remain identical.

## Reproducible build

`make demo-video` starts an isolated Docker stack, verifies the three public
image hashes, records one Playwright capture per language, and then uses Demo
Studio to add local neural narration, a Rhubarb-synchronized presenter,
licensed music, and subtitles. The frozen test set is never opened.
`make demo-video-check` verifies duration, codecs, resolution, size, the audio
track, and fourteen subtitle cues. Each of the seven visual scenes is narrated
with two short successive phrases, retaining technical substance without
covering the interface with a large text block.

## Shot list

### 0:00–0:16 — One auditable experiment

State the promise: images, measurements, provenance, and scientific limits
inside one local experiment.

### 0:16–0:42 — A protocol before analysis

Create the experiment, record its objective, and import the three public,
hash-locked images. Show that upload is separate from inference.

### 0:42–1:12 — Local and source-faithful analysis

Open the TIFF, distinguish the 8-bit PNG preview from the original source,
and run the weight-free adaptive CPU engine.

### 1:12–1:45 — Measurements with explicit limits

Compare source and overlay in the synchronized zoom viewer. Show connected
components, pixel-based geometry, and the reservation that prevents components
from being presented as validated cells.

### 1:45–2:08 — Reproducible exports

Download JSON and CSV, then descriptively compare a second experiment. The
screen states that this is not a biological between-group test.

### 2:08–2:36 — Accuracy and cost together

Show BBBC019, BBBC038, iOrganoAssay, intervals, time, memory, decisions, and
report hashes.

### 2:36–3:00 — Honest abstention

Show the engine registry and the unavailable or abstaining experimental CNN.
Close on acquisition shortcuts, the unopened frozen test, checksums, and
explicit limitations.

## Checks before publication

- duration at or below 5:00;
- interface, narration, and subtitles use the same language;
- presenter visible during narration and music covered by its licence;
- no secret, personal path, or frozen-test data;
- repository, report, and video accessible without authentication after publication.
