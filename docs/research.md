# Recherche et décisions

Dernière revue : **16 septembre 2026**.

## Challenge

Le règlement officiel, la grille d'évaluation, le calendrier et les livrables
sont tenus à jour dans
[competition-requirements.md](competition-requirements.md) ; le paysage
scientifique et concurrentiel est dans [etat-de-l-art.md](etat-de-l-art.md).
En résumé : Writeup Kaggle unique avec vidéo ≤ 5 min, dépôt public et rapport
technique ; aucune donnée ni tâche imposée ; date limite le **10 octobre
2026**, puis finale avec soutenance du 20 au 30 octobre.

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
| iOrganoAssay v1.1.0, 2026 | 234 bright-fields, essais, segmentation, morphométrie et 28 triplets officiels BF/GT/Seg | CC0-1.0, archive de 1,82 Go ; test externe borné exécuté une fois, macro-F1 0,822746 [0,772415 ; 0,867911], sans classification `good`/`bad` |
| Brain Organoid Dataset v2 | 1 400 images suivies dans deux laboratoires avec masques manuels | CC-BY-4.0 ; alternative pour robustesse inter-laboratoire |
| MultiOrg | 60 000 boîtes annotées par deux experts et trois jeux de labels | 35,4 Go, CC-BY-NC-SA-4.0 ; référence sur l'incertitude, non intégré avant soumission |
| SWIFT 2026 | pipeline YOLOv8s/SAM sur 417 bright-fields de côlon | état de l'art récent ; ne pas ajouter une nouvelle chaîne avant release |

Sources : [RxRx1](https://www.rxrx.ai/rxrx1),
[JUMP Hub](https://broadinstitute.github.io/jump_hub/),
[BBBC047](https://bbbc.broadinstitute.org/BBBC047),
[IDR](https://idr.openmicroscopy.org/about/),
[BioImage Model Zoo](https://bioimage.io/).

La recherche du 17 septembre 2026 n'a trouvé aucun second jeu public portant
le même label OoC `good`/`bad`. Les candidats organoïdes ne sont donc utilisables
que pour une validation externe de segmentation, de robustesse ou de
traçabilité. Ils ne doivent pas alimenter le classifieur actuel.

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
