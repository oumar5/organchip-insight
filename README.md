# OrganChip Insight

[English version](README.en.md)

Plateforme locale et reproductible d'analyse d'images de microscopie pour les
expériences organ-on-a-chip.

OrganChip Insight permet déjà de créer une expérience, importer des images,
exécuter une segmentation sans entraînement, inspecter les overlays et retrouver
les résultats après redémarrage. Les sorties actuelles sont **exploratoires** :
elles ne constituent ni un diagnostic ni une conclusion biologique.

## Capacités actuelles

- interface React/TypeScript en français et responsive ;
- API FastAPI documentée par OpenAPI ;
- expériences et résultats persistés dans SQLite ;
- décodage des uploads, limites de taille/pixels et détection des doublons binaires ;
- imports séparés de l'analyse, rejets détaillés et TIFF gris 16 bits pris en charge ;
- inférence CPU sans poids : Otsu, morphologie, composantes connexes ;
- composantes connexes, surfaces, diamètre, intensité, contraste et indice de
  contraste relatif explicitement heuristiques ; le comptage n'est pas validé
  comme nombre de cellules ;
- overlays de segmentation inspectables ;
- registre transparent des moteurs disponibles et candidats ;
- démonstrateur CNN ONNX optionnel à abstention systématique ;
- exports JSON complet et CSV par image ;
- même pipeline depuis l'interface, l'API ou `inference.py` ;
- pipeline expérimental MobileNetV3 reproductible, avec modes `smoke`,
  `validation` et `final-eval` isolés ;
- Docker Compose, suites unitaires et parcours Playwright bout en bout.
- validation externe iOrganoAssay v1.1.0 pré-enregistrée et versionnée.

## Démarrage recommandé

Prérequis : Docker Desktop avec Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

Ouvrir ensuite :

- application : <http://localhost:8080>
- API : <http://localhost:8000>
- OpenAPI : <http://localhost:8000/docs>

Les données sont conservées dans le volume Docker `organchip_data`.

Le Docker standard conserve le moteur adaptatif et affiche le CNN comme
indisponible tant que ses poids ne sont pas montés. Pour la démonstration ONNX :

```bash
export ORGANCHIP_QUALITY_MODEL_DIR_HOST="$(pwd)/data/experiments/ooc-cnn/kaggle-validation-campaign-v2-gray448/onnx"
docker compose -f docker-compose.yml -f docker-compose.quality.yml up --build
```

L'overlay Compose monte ce dossier en lecture seule et le runtime vérifie les
trois SHA-256 avant de rendre le moteur exécutable.

Si un port est déjà occupé, modifier `.env` sans toucher au code :

```dotenv
ORGANCHIP_BACKEND_PORT=18000
ORGANCHIP_FRONTEND_PORT=18080
```

## Développement local

Backend, depuis la racine :

```bash
uv sync --project backend --extra dev
uv run --project backend uvicorn app.main:app --reload
```

Frontend, dans un second terminal :

```bash
cd frontend
npm install
npm run dev
```

Ouvrir <http://localhost:5173>. Vite relaie les appels `/api` vers le backend.

## Inférence en ligne de commande

```bash
cd backend
uv run python inference.py image-1.png image-2.tif --output-dir artifacts/demo
```

La commande écrit les overlays et un `result.json` traçable.

## Vérification

```bash
make check
```

Ou séparément :

```bash
uv run --project backend --extra dev ruff check backend/app backend/tests backend/inference.py backend/training backend/evaluation backend/scripts
uv run --project backend --extra dev --extra ml pytest backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose config --quiet
```

Le scénario navigateur démarre une pile Docker isolée, crée une expérience,
importe une image synthétique, lance l'analyse et vérifie les exports JSON/CSV,
puis supprime ses conteneurs et son volume :

```bash
npm --prefix frontend exec playwright install chromium
make test-e2e
```

## Données publiques et benchmark

Le téléchargement minimal est borné, vérifié par checksum et n'inclut pas
l'archive OoC de 6,7 Go :

```bash
make data-fetch
make data-audit
make benchmark-bbbc019
```

Les données brutes restent dans `data/raw/`, hors Git. Le manifeste, l'audit et
les résultats versionnés sont décrits dans [data/README.md](data/README.md).

Sur les 28 triplets officiels de validation iOrganoAssay v1.1.0, le moteur
adaptatif gelé atteint un macro-F1 de `0,822746` (IC bootstrap 95 %
`[0,772415 ; 0,867911]`) et les trois critères pré-enregistrés sont atteints.
Cette preuve concerne le premier plan d'un organoïde cible ; elle ne valide ni
le comptage cellulaire, ni la classification `good`/`bad`, ni la segmentation
sur les images OoC du concours. Voir le
[REX iOrganoAssay](docs/retours-experience/2026-09-17-validation-externe-iorganoassay.md).

La modélisation CNN OoC est close après validation GPU et ablations A/B : aucune
configuration n'a atteint le plancher pré-enregistré par mode et le test gelé
n'a jamais été ouvert. Le run B est disponible uniquement comme démonstrateur
ONNX expérimental à abstention systématique. Voir le
[contre-audit](docs/audit-2026-09-17-classification-cnn.md) et le
[REX produit](docs/retours-experience/2026-09-17-demonstrateur-cnn-onnx.md).

Pour activer localement le démonstrateur avec le bundle autorisé déjà présent :

```bash
cd backend
uv sync --extra dev --extra ml --extra inference
ORGANCHIP_QUALITY_MODEL_DIR=../data/experiments/ooc-cnn/kaggle-validation-campaign-v2-gray448/onnx \
  uv run uvicorn app.main:app --reload
```

Les poids restent hors Git. Sans ONNX Runtime ou sans bundle conforme, le
moteur reste visible mais non exécutable et l'analyse adaptative continue de
fonctionner.

Contrôles locaux du pipeline et du notebook :

```bash
make cnn-protocol-test
make cnn-notebook-check
CNN_RUN_ID=smoke-local-manual-v1 make cnn-smoke
```

`cnn-smoke` utilise par défaut l'environnement Conda
`organchip-ooc-cnn-cpu` décrit dans
[`backend/experiments/ooc-cnn/README.md`](backend/experiments/ooc-cnn/README.md).
Un interpréteur isolé équivalent peut être fourni explicitement, par exemple
`make cnn-smoke CNN_PYTHON=/chemin/vers/python`.

Le smoke de référence `smoke-local-92bf217` a précisément utilisé le préfixe
local existant `data/cache/microsam-env/bin/python`, et non l'environnement
nommé ci-dessus. Son rapport conserve le `pip freeze` complet et le contrat
runtime a validé les versions pertinentes. `environment.cpu.yml` reste la
recette minimale de reconstruction ; un nouveau run dans l'environnement nommé
produirait des artefacts distincts. Les détails et le SHA-256 de cette recette
sont consignés dans le retour d'expérience lié plus haut.

L'export ONNX exige les identités exactes du checkpoint et du rapport de
sélection ; aucune valeur n'est inférée :

```bash
make cnn-export \
  CNN_CHECKPOINT=data/experiments/ooc-cnn/smoke-local-manual-v1/best-checkpoint.pt \
  CNN_CHECKPOINT_SHA256=REPLACE_WITH_64_HEX_SHA256 \
  CNN_SELECTION_REPORT=data/experiments/ooc-cnn/smoke-local-manual-v1/validation-report.json \
  CNN_SELECTION_REPORT_SHA256=REPLACE_WITH_64_HEX_SHA256 \
  CNN_EXPORT_DIR=data/experiments/ooc-cnn/smoke-local-manual-v1/onnx
```

Le [notebook Kaggle](notebooks/ooc-cnn-kaggle.ipynb) reste hors ligne par
construction : aucune installation, aucun téléchargement implicite de poids et
aucune action de publication Kaggle.

## Architecture

```text
frontend React
    -> API FastAPI
        -> SQLite : expériences et résultats
        -> fichiers : images et overlays
        -> registre de moteurs
            -> segmentation adaptative v1 (disponible)
            -> QC CNN run B (expérimental, bundle optionnel, abstention)
            -> µSAM (expérimental, benchmark isolé)
            -> Cellpose (revue de licence)
```

## Documentation

Commencer par l'[index documentaire](docs/README.md), puis lire :

- [vision produit](docs/product-brief.md) ;
- [inférence avant entraînement](docs/inference.md) ;
- [recherche et décisions](docs/research.md) ;
- [stratégie de données](docs/data-strategy.md) ;
- [plan de validation](docs/validation.md) ;
- [roadmap](docs/roadmap.md).

## Positionnement challenge

Catégorie prévue : **Tool & Platform** pour le challenge
[AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien),
volet international du 5ᵉ Pazhou Algorithm Competition. Le règlement officiel,
la grille Kaggle (impact 30 %, approche et innovation 30 %, résultats 20 %,
reproductibilité 10 %, présentation 10 %) et le calendrier (soumission le 10 octobre 2026, finale
avec soutenance du 20 au 30 octobre) sont résumés dans
[docs/competition-requirements.md](docs/competition-requirements.md). Le plan
de travail jusqu'à la finale est dans
[docs/plan-soumission.md](docs/plan-soumission.md).

Les benchmarks reproductibles adaptatif et µSAM ciblent BBBC019 Microfluidics ;
un audit d'instances µSAM pré-enregistré a aussi été exécuté sur BBBC038. Le
split OoC groupé, les comparateurs, la validation CNN et les ablations A/B sont
terminés. Aucun CNN n'a satisfait le critère par mode, le test gelé n'a jamais
été ouvert et la modélisation est close. La suite porte sur la finition produit
et les livrables de soumission.

## Licence

Projet conçu et porté par **Ben Lol OUMAR**.

Le code original d'OrganChip Insight est distribué sous licence
[Apache-2.0](LICENSE). Les jeux de données, poids, bibliothèques et médias tiers
conservent leurs licences propres, répertoriées dans
[la déclaration des outils et licences](docs/declaration-ia-et-licences.md).
