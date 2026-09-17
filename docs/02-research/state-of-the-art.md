# État de l'art et paysage concurrentiel

Dernière revue : **17 septembre 2026**. Cette page rassemble ce qui existe
autour du dataset OoC, des moteurs de segmentation et des outils comparables,
afin de situer OrganChip Insight dans le rapport technique et la soutenance.
Chaque affirmation est reliée à une source ; les chiffres externes ne sont pas
des résultats du projet.

## Travaux publiés sur le dataset OoC (Zenodo 10203721)

Le dataset compte 11 citations recensées par Semantic Scholar le 16 septembre
2026. Trois utilisent réellement les images :

| Travail | Données | Méthode | Protocole d'évaluation | Résultat annoncé | Ce que nous en retenons |
|---|---|---|---|---|---|
| [Movčana et al., *Data* 2024](https://doi.org/10.3390/data9020028), auteurs du dataset | 3 072 images, split publié train/val/test par dossiers | MobileNetV3 transféré ImageNet | split publié, dont nous avons montré que 59 préfixes `YYMMDD` traversent les splits | accuracy 0,81, précision 0,79, rappel 0,78, contre 0,56 pour la majorité | baseline de référence à reproduire, mais sur un split potentiellement contaminé |
| [George & Kenry, *Chem & Bio Engineering* 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12745998/), Univ. of Arizona | sous-ensemble de 631 images A549 et HSAEC | embeddings Inception v3 (2 048 dims), PCA, régression logistique, forêts, AdaBoost, kNN, MLP | **un seul split aléatoire 70/30**, validation croisée stratifiée pour les hyperparamètres, aucune notion de groupe d'acquisition | AUC > 0,95 et accuracy > 0,83 sur la qualité A549 ; 0,957 AUC / ~0,83 accuracy en quatre classes | la performance élevée est obtenue sans contrôle de fuite ; notre split groupé et notre audit de raccourcis sont un argument différenciant |
| [Ivanova & Ivanovs, AICCONF 2026](https://doi.org/10.1109/AICCONF69182.2026.11600675), institut EDI (co-auteurs du dataset) | dataset complet | 52 configurations MobileNetV3 (profondeur de tête, dégel du backbone), 12 méthodes d'explicabilité évaluées par Insertion, Deletion et MuFidelity | non détaillé dans le résumé | le gain vient du dégel des blocs profonds, pas de la tête ; les métriques d'explicabilité se contredisent | dégeler le backbone dans notre run `validation` ; présenter Grad-CAM avec prudence et plusieurs métriques |

Aucun de ces travaux ne publie de plateforme utilisable, de comparaison de
moteurs ni de protocole d'accès unique au test. C'est l'espace que le projet
occupe.

## Modèles de segmentation en microscopie

Le benchmark [Archit & Pape, MIDL 2026](https://arxiv.org/abs/2603.17845)
évalue sur 36 jeux de données (mSA moyenne sur les seuils IoU 0,5 à 0,95) :

| Modèle | Label-free | Fluorescence cellules | Fluorescence noyaux | Licence des poids |
|---|---:|---:|---:|---|
| µSAM AIS | 0,480 | 0,347 | 0,513 | CC-BY-4.0 |
| **µSAM APG** | **0,541** | 0,344 | 0,518 | CC-BY-4.0 |
| CellPoseSAM | 0,544 | 0,363 | 0,483 | données d'entraînement CC-BY-NC |
| CellSAM | 0,380 | 0,272 | 0,386 | usage académique non commercial |
| SAM3 | 0,269 | 0,143 | 0,255 | — |

En label-free, µSAM APG est à 0,003 de CellPoseSAM avec une licence de poids
permissive. Ce tableau justifie à lui seul le choix de µSAM comme moteur
expérimental et le statut `license-review` de Cellpose ; il doit apparaître
dans le rapport.

État des dépendances vérifié sur PyPI le 16 septembre 2026 :

- `micro-sam` 1.8.14 (6 septembre 2026), version utilisée par le projet ;
  feuille de route annoncée : modèles compressés et support SAM2/SAM3 ;
- `cellpose` 4.2.1.1 ; le dépôt officiel indique que tous les modèles,
  y compris `cpsam` et les modèles `cpdino` fondés sur DINOv3, sont entraînés
  sur des données CC-BY-NC ;
- DINOv2 reste Apache-2.0 ; DINOv3 est sous licence Meta spécifique,
  commerciale mais non standard, donc non retenu.

## Outils et plateformes comparables

| Outil | Nature | Écart avec OrganChip Insight |
|---|---|---|
| [OrganoidAgent](https://github.com/yhyh2270/OrganoidAgent) | application locale organoïdes : segmentation Cellpose multi-échelle, morphométrie, viabilité, agent | dépend de Cellpose (CC-BY-NC), organoïdes plutôt que puces, pas de protocole de validation anti-fuite publié |
| [OrganoSeg2](https://www.nature.com/articles/s41598-026-37526-7) (2026) | seuillage adaptatif multi-fenêtres sans apprentissage, suivi | proche de notre moteur adaptatif ; pas de registre de moteurs ni de contrôle qualité |
| CellProfiler, ilastik, napari | pipelines et visualiseurs génériques | expertise requise, pas de workflow OoC ni de comparaison de moteurs |
| Orbits, Incucyte | produits commerciaux fermés | liés au matériel et aux essais du fournisseur |

Un projet tiers vise le même challenge sous le nom « ChipTrace » (hashes
immuables, fusion multimodale, tests d'altération, rapports HTML). Il n'est
pas public sous forme exécutable au 16 septembre 2026 ; il confirme que la
reproductibilité et la traçabilité sont des axes attendus, pas une
différenciation suffisante à elles seules.

## Jeux de données candidats pour une validation externe

Le niveau L4 du plan de validation exige des données OoC ou proches, hors
dataset d'entraînement :

| Dataset | Contenu | Licence | Usage envisagé |
|---|---|---|---|
| [Brain organoid dataset, Zenodo 10301912](https://www.nature.com/articles/s41597-024-03330-z) | 1 400 images bright-field de 64 organoïdes suivis, quatre clones, deux laboratoires, masques binaires manuels | CC-BY-4.0, archive de 973,6 Mo | robustesse inter-laboratoire de la segmentation sur un sous-ensemble pré-enregistré |
| [iOrganoAssay v1.1.0, *Data* 2026](https://doi.org/10.5281/zenodo.20351867) | 234 images bright-field, métadonnées d'essais, sorties morphométriques et 28 triplets officiels BF/GT/Seg de validation | CC0-1.0, archive de 1,82 Go | test externe exécuté une fois selon le protocole pré-enregistré : macro-F1 0,822746, IC 95 % [0,772415 ; 0,867911] ; preuve bornée de premier plan d'organoïde |
| [MultiOrg, NeurIPS 2024](https://arxiv.org/abs/2410.14612) | plus de 400 images de plaques, 60 000 annotations par boîtes et trois jeux de labels par deux experts | CC-BY-NC-SA-4.0, environ 35,4 Go | référence sur l'incertitude d'annotation ; non intégré avant soumission |
| [SWIFT, *Communications Biology* 2026](https://www.nature.com/articles/s42003-026-10768-x) | 417 images bright-field de côlon pour segmentation, classification et suivi YOLOv8s/SAM | code public ; bundle de données à auditer | concurrent récent et source méthodologique, pas une nouvelle dépendance de release |
| BBBC038 | noyaux, masques d'instances, CC0 | CC0 | audit zéro-shot exécuté sur 12 images diverses ; résultat mitigé, non généralisable aux images OoC |

Aucun second dataset public d'images OoC bright-field avec le même label de
qualité n'a été trouvé. La validation externe la plus honnête reste donc une
segmentation sur organoïdes bright-field et une robustesse inter-laboratoire,
avec le label `good`/`bad` strictement limité au dataset OoC. Le test
iOrganoAssay a été exécuté une seule fois après pré-enregistrement ; aucun
second dataset externe n'est lancé avant la publication.

## Contraintes d'exécution Kaggle

- L'image Kaggle est construite sur le runtime Colab
  `release-colab-external-images_20260716` ; le runtime Colab 2026.07 fournit
  Python 3.12.13, numpy 2.0.2 et **PyTorch 2.11.0**
  ([FAQ Colab](https://research.google.com/colaboratory/runtime-version-faq.html)).
  Le contrat runtime actuel n'accepte que `torch < 2.11` et
  `torchvision < 0.26` : à vérifier sur un notebook Kaggle avant tout run
  `validation`, sinon le préflight échouera à raison.
- Quota GPU gratuit d'environ 30 h par semaine, sessions de 12 h maximum,
  T4 ×2 ou P100.
- Les Spaces Docker gratuits de Hugging Face ne sont plus disponibles en
  2026 ; une démo hébergée passe par Render, Google Cloud Run ou un petit VPS,
  avec vidéo et exécution locale en secours, comme le règlement le demande.
