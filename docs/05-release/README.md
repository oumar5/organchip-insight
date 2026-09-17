# Release evidence

`release-checksums.sha256` inventories every tracked competition deliverable:
dataset and model manifests, notebooks, benchmark and runtime reports, prediction
tables, the frontend benchmark summary, submission documents, the candidate PDF,
and the captioned demonstration video with its SRT sidecar. Model weights are
included automatically if they are ever deliberately tracked; none are distributed
in the current candidate while their publication licence is open.

Regenerate the inventory after any deliverable change:

```bash
make release-checksums
```

Verify it without changing files:

```bash
make release-checksums-check
```

The Git release tag identifies the exact source commit. The checksum inventory
authenticates the files delivered from that commit.
