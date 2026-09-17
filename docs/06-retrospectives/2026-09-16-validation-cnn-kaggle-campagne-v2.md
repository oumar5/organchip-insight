# Validation CNN GPU Kaggle — campagne v2

Date : **16 septembre 2026**

Statut : **validation GPU terminée ; sélection candidate consignée, non gelée
pour le produit ; test final jamais ouvert** (voir addendum du 17 septembre 2026)

## Question

Le pipeline MobileNetV3 Small peut-il exécuter une validation complète sur GPU
Kaggle avec des entrées entièrement locales et vérifiées, sélectionner son
checkpoint et son seuil sans consulter le test, puis produire un export ONNX
numériquement cohérent ?

Cette expérience ne tranche pas encore la généralisation finale. Elle porte
uniquement sur le train et la validation de la campagne v2 pré-enregistrée.

## Protocole reproductible

| Élément | Valeur |
|---|---|
| Notebook | `notebooks/ooc-cnn-kaggle.ipynb` |
| Identifiant du run | `kaggle-validation-campaign-v2` |
| Bundle source Kaggle | `organchip-insight-source-campaign-v2`, version 4 |
| SHA-256 du bundle source | `54a1e26a28c5967417d135e6f3d17698f15ec50c9e0d7fe273ecc3d4ef9de545` |
| Configuration | `backend/training/configs/ooc-cnn-mobilenet-v3-small-campaign-v2.json` |
| SHA-256 de la configuration | `134ee19c9983cc838be459fc0e4cdc37de08008bd70596bf82b9e51aa9dae2dd` |
| Split | `ooc-grouped-by-temporal-campaign-v2` |
| SHA-256 du verrou de split | `6d8474483a3f43acbf46cd9bffe5d20205d906da2ea8330fb8993d68dcd8769a` |
| SHA-256 du manifeste train/validation | `b191947b892bfa7e9442aca0051c3b2246343a289715073fd17eefabcf8ea4a3` |
| Modèle | MobileNetV3 Small, poids ImageNet locaux |
| SHA-256 des poids initiaux | `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f` |
| Graine | `20260916` |
| Matériel | deux Tesla T4 visibles ; entraînement sur un périphérique CUDA |
| Runtime | Python 3.12.13, PyTorch 2.10.0+cu128, torchvision 0.25.0+cu128 |
| Entraînement | 20 époques maximum, lot 32, AdamW, LR `3e-4`, weight decay `1e-4` |
| Arrêt anticipé | patience 6, métrique macro-F1 à seuil 0,5 |
| Durée de la cellule d'entraînement | environ 23 min 55 s |
| Accès réseau requis | non |
| Accès au test | aucun, `test_manifest_opened: false` |

Les images sont restées sous `/kaggle/input` en lecture seule. Le notebook a
copié uniquement le petit bundle source vers `/kaggle/working`. Le préflight a
validé le contrat logiciel, le split, l'inventaire, les poids et leurs hashes
avant le lancement.

## Courbe d'entraînement et arrêt anticipé

Le meilleur checkpoint a été obtenu à l'époque 3 :

| Époque | Train loss | Validation loss | Macro-F1 à 0,5 | Balanced accuracy |
|---:|---:|---:|---:|---:|
| 1 | 0,548799 | 0,579929 | 0,6886 | 0,6895 |
| 2 | 0,410388 | 0,596277 | 0,6943 | 0,6968 |
| 3 | 0,353206 | 0,562712 | 0,7361 | 0,7401 |
| 9 | 0,161179 | 0,892134 | 0,7332 | 0,7308 |

Après l'époque 3, la perte d'entraînement continue de diminuer tandis que la
perte de validation se dégrade. C'est un signal de surapprentissage. La
patience atteint 6 à l'époque 9 et l'arrêt anticipé restaure le checkpoint de
l'époque 3. Le mécanisme d'early stopping a donc joué son rôle.

## Résultats de validation

La validation contient 509 images : 227 `bad` et 282 `good`.

| Mesure | Seuil fixe 0,50 | Seuil sélectionné 0,42 |
|---|---:|---:|
| Accuracy | 0,736739 | 0,766208 |
| Balanced accuracy | 0,740072 | 0,761943 |
| Macro-F1 | 0,736102 | 0,762687 |
| ROC-AUC | 0,799638 | 0,799638 |
| PR-AUC | 0,779539 | 0,779539 |
| Brier score | 0,189335 | 0,189335 |
| ECE, 10 intervalles | 0,123790 | 0,123790 |

Au seuil sélectionné sur validation, la matrice de confusion est : 164 vrais
`bad`, 63 `bad` prédits `good`, 56 `good` prédits `bad` et 226 vrais `good`.
Le seuil `0,42` n'est pas un résultat indépendant : il a été optimisé sur cette
même validation et doit rester gelé avant tout accès au test.

Le macro-F1 de validation `0,762687` est numériquement proche du macro-F1 de
validation de la baseline handcrafted `0,761214`. Cette proximité ne démontre
pas une supériorité du CNN : les protocoles et la sélection du seuil doivent
être comparés à conditions strictement identiques, et le test final est encore
fermé.

Le rapport JSON produit également le bootstrap groupé et les tranches par type
cellulaire, bucket de jour, mode d'image et résolution. Leur revue détaillée est
obligatoire avant de décider d'ouvrir le test, car le raccourci mode +
résolution est déjà documenté. Tant que cette revue et les ablations prévues ne
sont pas terminées, le résultat ne prouve pas que le CNN apprend la qualité
d'image au-delà des propriétés d'acquisition.

## Artefacts gelés

```text
data/experiments/ooc-cnn/kaggle-validation-campaign-v2/best-checkpoint.pt
SHA-256 f55c53390101cba03cdf340e06c1d6b543e31284e5e2eacc38815581bf32e74d

data/experiments/ooc-cnn/kaggle-validation-campaign-v2/validation-report.json
SHA-256 7e3407b7088990d15039bea68e633bd13ba9abc060dbe43eb6395cdb11be76d2

data/experiments/ooc-cnn/kaggle-validation-campaign-v2/frozen-selection.json
SHA-256 852692b5d4ccc51573b0c94cb98f5c5603d4ed0f09ace2d38afbe803be5d6a9d
```

Le dossier du run contient aussi `last-checkpoint.pt`, `environment.json`,
`history.csv`, `learning-curves.png`, `validation-confusion.png`,
`validation-predictions.csv`, `source-hashes.json` et le dossier `onnx/`.
L'ensemble occupe environ 87,3 MiB dans le workspace Kaggle. Ces fichiers ne
sont pérennes qu'après création d'une version Kaggle ou archivage externe.

## Export ONNX

L'export utilise ONNX opset 18, une taille spatiale fixe de 224 et un axe de lot
dynamique. La parité a été vérifiée sur des lots de 1, 2 et 3, soit six
échantillons.

| Contrôle | Valeur |
|---|---:|
| Tolérance absolue | `1e-4` |
| Erreur absolue maximale | `2,0265579223632812e-06` |
| Parité | réussie |

```text
data/experiments/ooc-cnn/kaggle-validation-campaign-v2/onnx/model.onnx
SHA-256 3c9bf61ef20baebe82a383176deb0e390ee02bc653745b106904226157e03586

data/experiments/ooc-cnn/kaggle-validation-campaign-v2/onnx/export-report.json
SHA-256 72357dc8391978630bc3db7c7ebe58440341e17daaa916a74c43a7e062ec5b5a
```

Le rapport historique archivé porte `mode: smoke` et `requested_device: cpu` :
l'export réutilise bien le checkpoint de validation vérifié et sa parité est
correcte, mais ce libellé est ambigu. Le code a été corrigé pour les prochains
exports avec `operation: onnx-export`, `execution_device: cpu` et un champ
séparé `contract_validation_mode`. L'artefact historique reste volontairement
inchangé afin de conserver son hash et sa traçabilité.

## Décision

- considérer l'entraînement GPU, l'arrêt anticipé, le gel et l'export ONNX
  comme techniquement réussis ;
- conserver l'époque 3 et le seuil `0,42` comme sélection candidate, sans les
  modifier après consultation du test ;
- archiver immédiatement les artefacts du workspace dans une version Kaggle
  ou dans un bundle externe vérifié ;
- auditer le bootstrap groupé et toutes les tranches, puis exécuter les
  ablations pré-enregistrées ;
- corriger l'étiquette runtime du rapport d'export ;
- ne pas ouvrir le test final tant que ces contrôles et la décision de gel ne
  sont pas formellement revus.

## Sources et artefacts

- notebook : `notebooks/ooc-cnn-kaggle.ipynb` ;
- configuration :
  `backend/training/configs/ooc-cnn-mobilenet-v3-small-campaign-v2.json` ;
- dossier Kaggle :
  `/kaggle/working/organchip-ooc-cnn/organchip-insight/data/experiments/ooc-cnn/kaggle-validation-campaign-v2/` ;
- rapport brut : `validation-report.json`, SHA-256 documenté ci-dessus ;
- figures : `learning-curves.png` et `validation-confusion.png` ;
- prédictions : `validation-predictions.csv`.

## Addendum — conservation et versionnement

Le push GitHub réalisé depuis Kaggle a sauvegardé une copie exécutée du notebook
mais n'a pas publié les fichiers de `/kaggle/working` : `kaggle kernels output`
n'a récupéré que la log. Le notebook canonique a donc été restauré dans un
commit séparé et doit rester non exécuté dans GitHub.

Une commande `archive` partagée et testée produit désormais le bundle
déterministe suivant directement dans Kaggle :

```text
/kaggle/working/organchip-cnn-validation-campaign-v2-artifacts-v1.zip
```

Le noyau du notebook principal ne répondant plus après l'entraînement, l'archive
de sauvetage a été générée dans une console Python distincte attachée à la même
session, sans modifier les artefacts scientifiques. Elle a ensuite été
téléchargée et contrôlée localement :

- 14 artefacts utiles, plus le manifeste interne ;
- taille : `28 478 598` octets ;
- SHA-256 du ZIP :
  `36ad8c046695ea943e52de79f48a2d437a0f5cfac5c761701f389c3307ea4446` ;
- SHA-256 du manifeste interne :
  `5d563f18766b321f7b6b33b956f90a65a718afaa2ddcfa439e3e3633137e7fd9` ;
- vérification locale : `unzip -t` sans erreur ;
- copie locale ignorée par Git :
  `data/experiments/ooc-cnn/organchip-cnn-validation-campaign-v2-artifacts-v1.zip`.

Le Dataset privé Kaggle `oumarbenlol/organchip-cnn-validation-artifacts`
(`datasetId=12053935`, version 1) est à l'état `ready`. Kaggle a décompressé le
ZIP côté serveur et expose les 15 fichiers sous le dossier racine unique
`organchip-cnn-validation-campaign-v2/`. Sa licence est temporairement
`unknown`, car aucune licence de redistribution des artefacts n'a encore été
arrêtée.

Le conteneur Kaggle Model privé
`oumarbenlol/organchip-image-quality-cnn` (`modelId=758515`) est créé. Il reste
volontairement sans variation ni poids : Kaggle impose une licence au niveau de
la variation, et cette décision ne doit pas être inventée. Après choix de la
licence, les variantes `onnx` et `pytorch` recevront chacune une version issue
de ce bundle vérifié. Aucun poids, checkpoint ou ZIP n'est commité dans GitHub.

## Lecture par mode d'acquisition

Le rapport archivé contient une différence structurante qui doit gouverner les
expériences suivantes :

| Mode | Bad / good | Balanced accuracy | ROC-AUC |
| --- | ---: | ---: | ---: |
| L, 2056×1542 | 152 / 62 | 0,7729 | 0,8521 |
| RGB, 2048×1536 | 75 / 220 | 0,6315 | 0,6309 |

Le modèle apprend donc un signal utile dans la tranche L, alors que sa
discrimination RGB reste faible. Contrôler le mode empêche le raccourci global
mode/résolution d'expliquer à lui seul le score L, sans démontrer pour autant
l'indépendance biologique : d'autres facteurs de campagne peuvent rester
corrélés au label. La prochaine décision se prend sur les comparateurs v2 puis
sur les ablations pré-enregistrées dans
`docs/02-research/protocols/classification-campaign-v2.md`, jamais sur le test.

Les corrections appliquées avant le prochain run sont : nom d'archive dérivé du
`RUN_ID`, identifiant lu dans le rapport, provenance commit/bundle/config dans le
manifeste, étiquette explicite `onnx-export`, archivage du reçu final et retrait
de l'inventaire complet contenant les lignes test du bundle source.

## Addendum du 17 septembre 2026 — lecture après comparateurs et ablations

- La tranche L (balanced accuracy `0,7729`) ne compte que deux dates
  d'acquisition (230419 : 124 images, 6,45 % `good` ; 230517 : 90 images,
  60 % `good`). En analyse post hoc, un comparateur mode × bucket de jour
  appris sur le seul train y atteint `0,8171`. La phrase « le modèle apprend
  donc un signal utile dans la tranche L » n'est pas soutenue : ce score ne
  démontre pas un signal de qualité indépendant des métadonnées.
- Le macro-F1 de validation `0,762687` ne se compare pas au `0,761214` de la
  baseline handcrafted v1, obtenu sur un autre split ; le handcrafted
  recalculé sur v2 atteint `0,6876`
  (`reports/benchmarks/ooc-classification-comparators-campaign-v2.json`).
- La revue des tranches et les ablations A/B ont été réalisées le
  17 septembre 2026 ; ni A ni B n'est éligible, C n'a pas été lancé, aucun
  gel produit n'a lieu, le test n'a jamais été ouvert et ne le sera pas pour
  cette modélisation, qui est close. Aucune consultation du test n'a eu lieu.
- Voir le [contre-audit](../02-research/audits/audit-2026-09-17-classification-cnn.md) et le
  [retour d'expérience A/B](2026-09-17-ablations-cnn-campagne-v2.md).
