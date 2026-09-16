# Pipeline CNN et smoke CPU

Date : **16 septembre 2026**

Statut : **chemin technique validé, aucun benchmark CNN exécuté**

## Question

Le pipeline MobileNetV3 OoC peut-il charger des manifestes verrouillés,
vérifier les images, entraîner et sélectionner un checkpoint sans accéder au
test, puis produire un modèle ONNX numériquement cohérent ?

Ce contrôle ne cherche pas à estimer la performance scientifique. Il porte sur
un échantillon minuscule et utilise une initialisation aléatoire sans poids
ImageNet.

## Runtime et garde-fous

| Élément | Valeur |
|---|---|
| Code évalué | commit `92bf217fccb4784949411d2025a626bfbcea1015` |
| Architecture | MobileNetV3 Small, deux classes `bad` / `good` |
| Matériel | CPU |
| Échantillon | 8 images train / 4 images validation |
| Entraînement | 1 époque, lot 4, aucun poids externe |
| Graine | `20260916` |
| Intégrité | hashes des 12 images vérifiés |
| Accès test | aucun, `test_manifest_opened: false` |
| Éligibilité benchmark | non, `benchmark_eligible: false` |

Les modes `smoke` et `validation` ne reçoivent pas le manifeste test. Le mode
`final-eval` exige un manifeste gelé, les hashes attendus, la confirmation
exacte du protocole et un reçu d'accès local. Le test est destiné à être ouvert
une seule fois, après le gel du modèle, du seuil et du checkpoint. Le verrou
refuse une seconde tentative seulement dans un workspace qui conserve ce reçu ;
il ne peut pas empêcher une relance depuis un nouvel environnement Kaggle ou
après suppression du reçu. L'unicité globale reste donc une règle de protocole,
avec archivage externe obligatoire du reçu et du rapport final.

## Résultat du smoke

| Mesure technique | Valeur |
|---|---:|
| Macro-F1 validation | 0,333333 |
| ROC-AUC validation | 0,5 |
| Images de validation | 4 |

Ces chiffres confirment que les calculs, la sélection et la sérialisation se
terminent. Ils ne mesurent pas la qualité attendue du CNN : quatre images ne
constituent pas un échantillon de validation, l'initialisation est aléatoire et
le run est explicitement inéligible au benchmark. Ils ne doivent donc pas être
comparés à la baseline de raccourcis ni à la baseline handcrafted.

Le checkpoint retenu est :

```text
data/experiments/ooc-cnn/smoke-local-92bf217/best-checkpoint.pt
SHA-256 eaf8ebdae4a73e706c2266294d6436dca17d904dd4a8da781dff49d663f79ec6
```

Le rapport qui fixe la sélection est :

```text
data/experiments/ooc-cnn/smoke-local-92bf217/validation-report.json
SHA-256 0626128ce599ac6580861744071de729e143e7e78876229a5cbc1a4ee14cae8e
```

Ces fichiers sont des artefacts locaux ignorés par Git. Les hashes permettent
de vérifier leur identité, mais ils ne rendent pas ce smoke publiable comme
résultat scientifique.

Commandes exactes de cette preuve locale :

```bash
PYTHONPATH=backend data/cache/microsam-env/bin/python \
  -m training.ooc_cnn.cli train --mode smoke --device cpu \
  --image-root . --run-id smoke-local-92bf217

make cnn-export \
  CNN_PYTHON=data/cache/microsam-env/bin/python \
  CNN_CHECKPOINT=data/experiments/ooc-cnn/smoke-local-92bf217/best-checkpoint.pt \
  CNN_CHECKPOINT_SHA256=eaf8ebdae4a73e706c2266294d6436dca17d904dd4a8da781dff49d663f79ec6 \
  CNN_SELECTION_REPORT=data/experiments/ooc-cnn/smoke-local-92bf217/validation-report.json \
  CNN_SELECTION_REPORT_SHA256=0626128ce599ac6580861744071de729e143e7e78876229a5cbc1a4ee14cae8e \
  CNN_EXPORT_DIR=data/experiments/ooc-cnn/smoke-local-92bf217/onnx
```

## Export ONNX

L'export utilise ONNX opset 18, une taille spatiale fixe de 224 et un axe de lot
dynamique. La parité a été vérifiée sur des lots de 1, 2 et 3, soit six
échantillons au total.

| Contrôle | Valeur |
|---|---:|
| Tolérance absolue | `1e-4` |
| Erreur absolue maximale | `1,862645149230957e-09` |
| Parité | réussie |

Modèle exporté :

```text
data/experiments/ooc-cnn/smoke-local-92bf217/onnx/model.onnx
SHA-256 57badbeae247c241797ebe4094deeb6b25e71a79ca76429a832b9f92e6adc1c9
```

Rapport d'export :

```text
data/experiments/ooc-cnn/smoke-local-92bf217/onnx/export-report.json
SHA-256 575431d9119eca85a83c1c1c2162b2091b2af1e1ae32182494d2303c4baeca0f
```

Configuration et contrat runtime évalués :

```text
backend/training/configs/ooc-cnn-mobilenet-v3-small-v1.json
SHA-256 4c01910c1df49fc8b9a129b32b890015086b21ce09d1830eabd24fbd82cffe59
backend/experiments/ooc-cnn/kaggle-runtime-contract.json
SHA-256 3e8d1d34fdd7e853037ef2e8c3435ea2ef769a9f6bd5fffee03fec6c08d241ea
```

Ce résultat valide le chemin d'export et la cohérence numérique pour cet
artefact précis. Il ne valide ni la précision du modèle, ni son comportement
sur une autre pile d'exécution ou un autre matériel.

## Préparation Kaggle

Le prochain run utile est le mode `validation` complet sur GPU Kaggle, avec des
poids ImageNet fournis localement et vérifiés par SHA-256. Aucun téléchargement
implicite de poids, aucune installation réseau et aucun accès test ne sont
autorisés pendant cette étape.

Le bundle source Kaggle doit être matériellement autonome sous
`/kaggle/working/organchip-ooc-cnn/organchip-insight` : code, configuration, contrat runtime,
inventaire et manifestes. Les 13 Go d'images ne sont pas dupliqués. Ils restent
dans le dataset read-only sous `/kaggle/input`, avec le même layout relatif
`data/raw/ooc/...`, et sa racine est transmise au CLI par `--image-root`.

Relier le projet à `/kaggle/input` par symlink ne fonctionne pas : le chargeur
rejette intentionnellement les liens qui sortent de la racine autorisée. La
racine explicite permet au contraire de lire le dataset séparé sans le copier.
Le préflight de validation doit vérifier le contrat runtime, la présence et le
format de chaque hash requis, puis les contenus locaux correspondants avant
l'entraînement. En `final-eval`, les hashes attendus du manifeste gelé, du
checkpoint et du manifeste test sont validés avant l'autorisation ; le contenu
du manifeste test n'est vérifié qu'après persistance du reçu, juste avant son
évaluation.

Le manifeste test reste lui aussi dans le bundle final read-only. Il est passé
avec sa racine logique au CLI et n'est ni copié ni hashé par le notebook : le
protocole persiste d'abord le reçu local, puis seulement le CLI ouvre le
manifeste et vérifie son SHA-256. Le reçu doit ensuite être exporté hors du
workspace éphémère afin que toute nouvelle exécution soit détectable lors de la
revue scientifique, même si elle ne peut pas être bloquée globalement par le
processus local.

## Décision

- considérer le runtime et l'export ONNX comme techniquement opérationnels ;
- ne publier aucune métrique CNN à partir de ce smoke ;
- exécuter ensuite la validation GPU complète et examiner les tranches par mode,
  résolution, type cellulaire et jour ;
- comparer seulement ce futur run éligible aux baselines existantes ;
- ne déclencher l'accès test destiné à être unique qu'après revue et gel formel
  de la validation, du seuil, du checkpoint et des hashes, puis archiver le
  reçu hors du workspace.

## Artefacts locaux

- rapport miroir : `reports/generated/ooc-cnn/smoke-local-92bf217.json` ;
- dossier du run : `data/experiments/ooc-cnn/smoke-local-92bf217/` ;
- rapport d'export :
  `data/experiments/ooc-cnn/smoke-local-92bf217/onnx/export-report.json`.

Les artefacts locaux ne sont pas versionnés. Le présent retour d'expérience
conserve les conditions, les limites et les hashes nécessaires à leur audit.
