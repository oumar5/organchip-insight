# Déclaration des outils d'IA, des modèles et des licences

Le règlement du challenge exige de déclarer les outils d'IA, modèles ouverts,
bibliothèques et données utilisés, avec leur source, leur licence et leur
usage. Cette page est la source unique de cette déclaration ; elle doit être
recopiée dans le rapport technique et le Writeup.

Dernière mise à jour : 17 septembre 2026.

## Outils d'IA utilisés pour développer le projet

| Outil | Usage | Contrôle humain |
|---|---|---|
| OpenAI Codex, modèles de la famille GPT | développement, revue de code, tests, documentation, interface, orchestration locale et contre-analyse méthodologique | chaque modification est relue et validée par les suites du dépôt ; aucune métrique n'est inventée par le modèle |
| Claude Code (Anthropic), modèles de la famille Claude | revues indépendantes, assistance au code, aux tests, à la documentation et à la recherche bibliographique | les constats sont recoupés avec le code, les rapports versionnés et des commandes reproductibles |

La déclaration publique conserve les noms officiels des fournisseurs et des
produits. Les surnoms de sessions ou d'interfaces ne sont pas conservés, car
ils ne constituent pas des identifiants de modèle stables ou vérifiables. Les
versions exactes ne sont indiquées que lorsqu'un reçu ou un manifeste permet
de les prouver.

Aucune fonction du produit ne dépend d'un grand modèle de langage ou d'une
API commerciale.

## Modèles et poids

| Modèle | Rôle | Code | Poids | Provenance vérifiée |
|---|---|---|---|---|
| `adaptive-segmentation-v1` | moteur par défaut, sans poids | code du projet | aucun | — |
| µSAM `vit_b_lm` + APG, micro-sam 1.8.14 | benchmarks isolés BBBC019 et BBBC038 | MIT | CC-BY-4.0, BioImage.IO `diplomatic-bug` 1.2 | SHA-256 dans `data/manifests/models.json` et les rapports |
| MobileNetV3-Small (torchvision) | classifieur de qualité expérimental | BSD-3 (torchvision) | poids ImageNet BSD-3, fournis localement avec SHA-256 | rapports de validation, ablations A/B et manifestes ONNX verrouillés |
| Cellpose / Cellpose-SAM | non utilisé | BSD-3 | données d'entraînement CC-BY-NC | statut `license-review`, jamais chargé |

Le run MobileNetV3-Small sélectionné, son export ONNX et leurs SHA-256 sont
consignés dans les rapports de validation et d'ablation. Le bundle reste hors
de la soumission publique.

## Outils de production des vidéos

| Outil | Usage | Licence / réserve |
|---|---|---|
| Chatterbox Multilingual 0.1.7 (Resemble AI) | synthèse locale des narrations anglaise et française, sans audio de référence ni clonage de voix | code et modèle MIT ; runtime et poids non redistribués dans le dépôt |
| Rhubarb Lip Sync 1.14.0 | génération locale des repères de bouche de l'avatar | MIT ; les repères produits appartiennent au projet |
| Demo Studio | capture, montage reproductible, sous-titres et composition des livrables vidéo | outil local de production ; seul le résultat et les configurations OrganChip nécessaires sont distribués |

## Données

| Jeu | Version | Licence | Usage | Checksum |
|---|---|---|---|---|
| OOC Image Dataset, Zenodo 10203721 | v1 (2023) | CC-BY-4.0 | classification de qualité, split groupé | md5 archive, sha256 tableur |
| BBBC019 Microfluidics | v2 | CC-BY-3.0 | benchmark de segmentation | sha256 |
| BBBC038 stage 1 train | v1 | CC0-1.0 | benchmark borné d'instances et de comptage, 12 images | sha256 archive, images, arbres de masques et manifeste |

Aucune donnée personnelle, clinique ou privée n'est utilisée.

## Bibliothèques principales

FastAPI, Uvicorn, Pydantic (MIT) ; NumPy, scikit-image, scikit-learn, pandas
(BSD-3) ; Pillow (MIT-CMU) ; PyTorch, torchvision (BSD-3) ; ONNX, ONNX
Runtime (Apache-2.0/MIT) ; React (MIT) ; Vite (MIT) ; TypeScript (Apache-2.0).
Les versions exactes sont figées dans `backend/uv.lock`,
`frontend/package-lock.json` et les fichiers `environment*.yml`.

## Licence du projet

Le code original d'OrganChip Insight est distribué sous **Apache-2.0**, avec le
texte complet dans `LICENSE`. Cette licence permissive comprend une concession
explicite de brevets. Elle ne remplace pas les licences propres aux datasets,
poids, bibliothèques, musique et autres contenus tiers listés dans ce document.

## Citations attendues dans le rapport

- Movčana et al., « Organ-On-A-Chip (OOC) Image Dataset for Machine Learning
  and Tissue Model Evaluation », *Data* 9(2):28, 2024.
- Ljosa, Sokolnicki & Carpenter, « Annotated high-throughput microscopy image
  sets for validation », *Nature Methods* 9:637, 2012 (BBBC).
- Archit et al., « Segment Anything for Microscopy », *Nature Methods* 2025 ;
  Archit & Pape, « Revisiting foundation models for cell instance
  segmentation », MIDL 2026.
- Howard et al., « Searching for MobileNetV3 », ICCV 2019.
