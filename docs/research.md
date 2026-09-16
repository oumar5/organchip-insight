# Recherche et décisions

Dernière revue : **16 septembre 2026**.

## Challenge

La page officielle [AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien)
autorise modèles, outils, plateformes et systèmes complets. Le livrable officiel
est un Writeup Kaggle comprenant vidéo, dépôt public et rapport technique.

La notation annoncée est :

| Critère | Poids | Réponse du projet |
|---|---:|---|
| Importance et impact | 30 % | workflow OoC concret, réduction du temps d'analyse |
| Approche et innovation | 30 % | registre de moteurs, inférence avant entraînement, provenance |
| Résultats et validation | 20 % | benchmarks publics, overlays, intervalles et erreurs |
| Reproductibilité | 10 % | Docker, CLI, API, tests, données ouvertes |
| Présentation | 10 % | parcours en trois étapes et vidéo réelle |

Le challenge recommande explicitement l'analyse d'images cellulaires, la
prédiction de réponse aux médicaments et l'analyse de phénotypes. Il ne fournit
pas de dataset imposé. La date limite publiée est le **10 octobre 2026**.

## Jeux de données retenus pour l'audit

### 1. Organ-On-A-Chip Image Dataset

- 3 072 images bright-field issues d'un dispositif OoC ;
- métadonnées partielles : type cellulaire, densité, temps et débit ;
- licence Zenodo vérifiée CC-BY-4.0 ;
- usage : démonstration principale et analyse de robustesse par condition.

Source : [article et description du dataset](https://doi.org/10.3390/data9020028),
[archive Zenodo](https://doi.org/10.5281/zenodo.10203721).

### 2. BBBC019, sous-ensemble Microfluidics

- 13 images DIC de cellules MDCK sur plaque microfluidique ;
- masques de premier plan annotés manuellement ;
- licence CC-BY 3.0 ;
- usage : validation proche du contexte microfluidique, précision/rappel/F1.

Source : [BBBC019 v2](https://bbbc.broadinstitute.org/BBBC019).

### 3. BBBC038

- images de noyaux très diverses avec masques d'instances ;
- jeu d'entraînement de 82,9 Mo, donc compatible avec une itération rapide ;
- licence CC0 ;
- usage : Dice/IoU, précision et rappel par objet, test de généralisation.

Source : [BBBC038 v1](https://bbbc.broadinstitute.org/BBBC038).

## Alternatives analysées

| Ressource | Intérêt | Risque / décision |
|---|---|---|
| RxRx1 | perturbations et effets de lot | 296 Go, CC-BY-NC-SA ; non prioritaire |
| JUMP Cell Painting | phénotypes à grande échelle | plusieurs téraoctets ; profils agrégés possibles plus tard |
| BBBC047 | 30 616 composés, licence commerciale permise | 919 265 champs ; sous-échantillon futur |
| IDR | images et métadonnées de publications | hétérogène ; validation externe ciblée |
| BioImage Model Zoo | modèles normalisés | licence à vérifier modèle par modèle |

Sources : [RxRx1](https://www.rxrx.ai/rxrx1),
[JUMP Hub](https://broadinstitute.github.io/jump_hub/),
[BBBC047](https://bbbc.broadinstitute.org/BBBC047),
[IDR](https://idr.openmicroscopy.org/about/),
[BioImage Model Zoo](https://bioimage.io/).

## Standards et écosystème

- OME-Zarr est la cible recommandée pour les données multidimensionnelles ; le
  support PNG/JPEG/TIFF du MVP est une étape d'entrée, pas le format final.
- Pycytominer formalise l'agrégation, l'annotation, la normalisation, la sélection
  de caractéristiques et les signatures consensuelles pour le profilage.
- Les recommandations BBBC insistent sur une vérité terrain adaptée : comptage,
  premier plan, contours ou labels biologiques nécessitent des métriques distinctes.

Sources : [OME-NGFF](https://ngff.openmicroscopy.org/),
[Pycytominer](https://github.com/cytomining/pycytominer),
[méthodologie BBBC](https://bbbc.broadinstitute.org/benchmarking).

## Décision de portée

Le premier résultat défendable sera :

> une plateforme qui exécute et compare des moteurs de segmentation sur des
> images OoC, expose visuellement leurs erreurs, puis agrège des descripteurs
> morphologiques pour comparer des conditions expérimentales.

La prédiction de toxicité demeure une extension. Elle ne sera annoncée que si un
dataset relie réellement images, dose, réplication et mesure de viabilité.
