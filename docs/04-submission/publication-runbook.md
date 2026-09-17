# Publication runbook

This is the final ordered procedure once the project owner supplies the missing
publication decisions. Apache-2.0 and the solo team led by Ben Lol OUMAR are
already fixed. The procedure prevents a partially public or internally
inconsistent submission.

## Current verified state — 18 September 2026

- `dev` and `main` are public and synchronized at the validated product state;
- the GitHub repository is public and `main` is the default branch;
- the `main` CI passed on the exact product commit before release finalization;
- tag, release assets and Kaggle submission are the remaining publication steps;
- both candidate videos passed the automated codec, audio, duration and
  subtitle checks again on 18 September 2026.

## 1. Owner-controlled fields

Record all of the following before submission:

- confirmation that the organizer's external registration form was submitted;
- authorization to merge linearly to `main`, make the repository public and
  create the release — granted on 18 September 2026;
- final tag: `v1.0.0-ai4s`.

## 2. Finalize the tracked content on `dev`

1. Verify the Apache-2.0 `LICENSE` file and third-party attributions.
2. Verify the author identity in the report and Writeup.
3. Rebuild and inspect the PDF with `make report-pdf` and
   `make report-pdf-check`.
4. Run `make check demo-video-check`.
5. Regenerate `make release-checksums`, review the diff, and rerun
   `make release-checksums-check`.
6. Commit only this coherent finalization block on `dev`.

Do not add or publish the optional ONNX bundle unless its licence and SHA-256
are settled. Do not open the frozen classification test.

## 3. Publish the exact validated state

1. `dev` is already pushed at the validated commit above.
2. Merge `dev` linearly into `main` only after explicit authorization.
3. Confirm CI/CD succeeds on the exact `main` commit.
4. Select `main` as the GitHub default branch before anonymous verification.
5. Create the approved annotated tag and GitHub release from that commit.
6. Paste `docs/05-release/RELEASE_NOTES_CANDIDATE.md` after replacing “candidate”
   fields, and attach the checksum file, PDF, MP4 and SRT.
7. Make the repository and release public **before** submitting the Writeup;
   keep them public throughout evaluation.

## 4. Verify anonymously

In a private browser window with no GitHub or Kaggle session, verify:

- repository root, README, licence, Docker files and release tag;
- PDF download and visual opening;
- video playback with readable English captions and duration under five minutes;
- checksum downloads and hashes;
- every dataset or model acquisition instruction used for reproduction.

Record the public repository, release, PDF and video URLs plus the verified UTC
time in a local submission receipt. Do not store authentication tokens or
browser cookies in that receipt.

## 5. Submit Kaggle

1. Replace the four public-link fields in `kaggle-writeup-en.md`.
2. Copy the final content into the Kaggle Writeup and select **Tool & Platform**.
3. Preview every section and open every link from a private window.
4. Submit the Writeup by **9 October 2026** internally (official deadline:
   10 October 2026, 15:59:59 UTC).
5. Save the submission confirmation, final URLs, commit SHA, tag and checksum
   inventory in the local receipt.

Saving a draft is not submission. The terminus is reached only when Kaggle
shows the Writeup as submitted and all public assets remain accessible without
authentication.
