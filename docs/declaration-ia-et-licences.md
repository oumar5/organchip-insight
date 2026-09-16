# Déclaration des outils d'IA, des modèles et des licences

Le règlement du challenge exige de déclarer les outils d'IA, modèles ouverts,
bibliothèques et données utilisés, avec leur source, leur licence et leur
usage. Cette page est la source unique de cette déclaration ; elle doit être
recopiée dans le rapport technique et le Writeup.

Dernière mise à jour : 16 septembre 2026. Les lignes marquées `à compléter`
doivent être finalisées avant la release.

## Outils d'IA utilisés pour développer le projet

| Outil | Usage | Contrôle humain |
|---|---|---|
| Claude Code (Anthropic), modèles de la famille Claude | assistance à l'écriture de code, de tests, de documentation et à la recherche bibliographique | chaque commit est relu ; les métriques proviennent exclusivement de scripts versionnés ; aucune sortie générée n'est présentée comme un résultat expérimental |
| autres assistants (`à compléter` si utilisés) | — | — |

Aucune fonction du produit ne dépend d'un grand modèle de langage ou d'une
API commerciale.

## Modèles et poids

| Modèle | Rôle | Code | Poids | Provenance vérifiée |
|---|---|---|---|---|
| `adaptive-segmentation-v1` | moteur par défaut, sans poids | code du projet | aucun | — |
| µSAM `vit_b_lm` + APG, micro-sam 1.8.14 | benchmark isolé BBBC019 | MIT | CC-BY-4.0, BioImage.IO `diplomatic-bug` 1.2 | SHA-256 dans `data/manifests/models.json` |
| MobileNetV3-Small (torchvision) | classifieur de qualité expérimental | BSD-3 (torchvision) | poids ImageNet BSD-3, fournis localement avec SHA-256 | `à compléter` après le run `validation` |
| Cellpose / Cellpose-SAM | non utilisé | BSD-3 | données d'entraînement CC-BY-NC | statut `license-review`, jamais chargé |

## Données

| Jeu | Version | Licence | Usage | Checksum |
|---|---|---|---|---|
| OOC Image Dataset, Zenodo 10203721 | v1 (2023) | CC-BY-4.0 | classification de qualité, split groupé | md5 archive, sha256 tableur |
| BBBC019 Microfluidics | v2 | CC-BY-3.0 | benchmark de segmentation | sha256 |
| BBBC038 | v1 | CC0 | prévu, non exécuté | — |

Aucune donnée personnelle, clinique ou privée n'est utilisée.

## Bibliothèques principales

FastAPI, Uvicorn, Pydantic (MIT) ; NumPy, scikit-image, scikit-learn, pandas
(BSD-3) ; Pillow (MIT-CMU) ; PyTorch, torchvision (BSD-3) ; ONNX, ONNX
Runtime (Apache-2.0/MIT) ; React (MIT) ; Vite (MIT) ; TypeScript (Apache-2.0).
Les versions exactes sont figées dans `backend/uv.lock`,
`frontend/package-lock.json` et les fichiers `environment*.yml`.

## Licence du projet

`à compléter` : le dépôt n'a pas encore de fichier `LICENSE`. Recommandation :
Apache-2.0, compatible avec toutes les dépendances ci-dessus et explicite sur
les brevets.

## Citations attendues dans le rapport

- Movčana et al., « Organ-On-A-Chip (OOC) Image Dataset for Machine Learning
  and Tissue Model Evaluation », *Data* 9(2):28, 2024.
- Ljosa, Sokolnicki & Carpenter, « Annotated high-throughput microscopy image
  sets for validation », *Nature Methods* 9:637, 2012 (BBBC).
- Archit et al., « Segment Anything for Microscopy », *Nature Methods* 2025 ;
  Archit & Pape, « Revisiting foundation models for cell instance
  segmentation », MIDL 2026.
- Howard et al., « Searching for MobileNetV3 », ICCV 2019.
