# Bilingual competition video

This Demo Studio project turns one deterministic Playwright capture of the real
product into two submission candidates:

- `organchip-insight-demo-candidate-en.mp4` with English narration and subtitles;
- `organchip-insight-demo-candidate-fr.mp4` with French narration and subtitles.

The final composition adds a visible presenter, locally generated narration,
licensed background music, and an SRT sidecar for each language. The product
capture uses the three public, hash-locked images from
`data/manifests/product-real-smoke-v1.json`; it never opens the frozen
classification test set.

## Rebuild

On macOS, make sure Docker, FFmpeg, Node, the local Demo Studio checkout, and a
compatible Chatterbox/Rhubarb runtime are available. Demo Studio defaults to
the sibling directory `../demo-studio`; the natural-voice runtime defaults to
`../solmik/product-demos/.runtime`. Set `DEMO_STUDIO_ROOT` or
`ORGANCHIP_NATURAL_VOICE_ROOT` to override either location.

```bash
make demo-video
make demo-video-check
```

Narration uses the local Chatterbox neural runtime and Rhubarb generates mouth
cues for the presenter. No reference voice, voice clone or remote speech
service is used. The soundtrack and its Pixabay licence notice are stored
under `public/music/`.
