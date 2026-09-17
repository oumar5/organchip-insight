# Five-minute demonstration storyboard

Delivered duration: **3:18**, leaving 1 minute 42 seconds of safety below the
five-minute limit. The product is on screen immediately. Both candidates are
1280×720 and hide notifications and personal paths.

## Reproducible local candidate

Run `make demo-video` to build the **English and French 3:18 candidates** from
one capture of the locked real-image manifest. The command starts an isolated
Docker stack, checks every source hash, records the browser, generates local
Chatterbox narration without voice cloning, and uses Demo Studio with Rhubarb
to add a lip-synced presenter, licensed music and language-specific subtitles. It then
normalizes both outputs to H.264 yuv420p/AAC and validates duration, codecs,
resolution, file size, subtitle reservations and non-silent audio. Run
`make demo-video-check` for a read-only verification.

English and French use the same local neural pipeline without reference audio.
Rhubarb produces mouth cues for the presenter. The soundtrack licence notice
is versioned next to the audio.

## Recording prerequisites

- start from the release candidate and a fresh demo experiment;
- keep the adaptive engine selected;
- prepare the locked public smoke batch: one RGB OoC PNG, one grayscale OoC
  PNG, and one BBBC019 TIFF;
- prepare one intentionally rejected file if it can be shown without slowing
  the sequence;
- pre-start Docker and keep a terminal ready for the final verification shot;
- keep the optional CNN unavailable unless the licensed model bundle is part
  of the public release;
- never show or open the frozen test dataset.

## Shot list and narration

### 0:00–0:25 — Problem and promise

**Screen:** product home, then a quick pan across the empty workspace.  
**Narration:** “Bright-field organ-on-chip imaging produces many files, but a
measurement without acquisition context, provenance, and limits is difficult
to reuse. OrganChip Insight turns those files into a traceable local
experiment.”

### 0:25–1:05 — Create and import

**Screen:** create a named experiment, enter its objective, import the prepared
files, and show accepted/rejected counts and source formats.

**Narration:** “The experiment records its objective before analysis. Uploads are
decoded, bounded by pixel and file size, checked for binary duplicates, and
kept separate from inference. PNG, JPEG, and grayscale TIFF are supported,
including 16-bit sources when supplied.”

### 1:05–2:10 — Analyze and inspect

**Screen:** choose adaptive segmentation, run the analysis, open the per-image
table and overlay. Zoom on the scientific reservation.  
**Narration:** “The default engine is CPU-only and requires no learned weights.
It reports connected components, not cells: no instance annotation on the
competition images validates a cellular count. Areas and diameters remain in
pixels because physical calibration is unavailable.”

### 2:10–2:45 — Export and provenance

**Screen:** download JSON and CSV; open the JSON preview or download list long
enough to show that both files were produced.  
**Narration:** “Every result remains attached to its experiment, image,
engine, parameters, and generation time. The same pipeline is available from
the browser, API, or command-line tool.”

### 2:45–3:35 — Compare engines without hiding cost

**Screen:** scroll to “Engine comparison,” show BBBC019, BBBC038, confidence
intervals, time, memory, decisions, then expand provenance hashes.  
**Narration:** “The comparison is generated from versioned reports, never
typed into the interface. µSAM is stronger on BBBC019 foreground segmentation,
but costs about 43 seconds per image and 8.7 gigabytes in the measured CPU
environment. On the preregistered BBBC038 instance audit, it failed two of
three promotion criteria. It therefore remains an isolated benchmark.”

### 3:35–4:15 — Negative CNN result as evidence

**Screen:** engine registry and experimental CNN card; if unavailable, keep
that state visible. Briefly show the classification counter-audit document.  
**Narration:** “For quality classification, acquisition mode and culture
metadata were strong shortcuts. Grouped validation and preregistered ablations
did not demonstrate a robust independent signal, so we never opened the frozen
test set. The optional ONNX demonstrator always says ‘Needs review,’ labels its
softmax as uncalibrated, and makes no automatic good-or-bad decision.”

### 4:15–4:40 — Reproduce and close

**Screen:** terminal with `docker compose up --build`, `make check`, and the
successful Playwright line; finish on the product.  
**Narration:** “The whole platform runs locally with Docker. Data manifests,
checksums, protocols, tests, and dated decision records are public. OrganChip
Insight is a practical microscopy workspace where outputs, uncertainty, and
provenance travel together.”

## Mandatory post-production checks

- duration is at most 5:00 and the important content ends before 4:45;
- all captions are readable at normal playback size;
- no API key, local username, notification, private repository address, or
  unpublished dataset path appears;
- the public URL works in a private browser window without authentication;
- the description links to the exact release and technical report;
- only redistributable images, icons, fonts, and audio are present.
