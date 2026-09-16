# OrganChip Insight

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
- vérification de contenu et limite de taille des uploads ;
- inférence CPU sans poids : Otsu, morphologie, composantes connexes ;
- comptage, surfaces, diamètre, intensité, contraste et indice de contraste
  relatif explicitement heuristique ;
- overlays de segmentation inspectables ;
- registre transparent des moteurs disponibles et candidats ;
- même pipeline depuis l'interface, l'API ou `inference.py` ;
- pipeline expérimental MobileNetV3 reproductible, avec modes `smoke`,
  `validation` et `final-eval` isolés ;
- Docker Compose et suites de tests.

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
uv run --project backend --extra dev ruff check backend/app backend/tests backend/inference.py
uv run --project backend --extra dev --extra ml pytest backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose config --quiet
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

Le pipeline CNN OoC a passé un smoke test CPU et une vérification d'export
ONNX. Ce contrôle de 12 images vérifie le chemin technique, pas la performance
du modèle : la validation complète sur GPU Kaggle et l'évaluation finale du
test gelé restent à réaliser. Voir le
[retour d'expérience CNN](docs/retours-experience/2026-09-16-pipeline-cnn-smoke.md).

Contrôles locaux du pipeline et du notebook :

```bash
make cnn-protocol-test
make cnn-notebook-check
CNN_RUN_ID=smoke-local-manual-v1 make cnn-smoke
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
            -> µSAM (planifié)
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
[AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien).

Le premier benchmark reproductible cible BBBC019 Microfluidics. La suite est la
comparaison µSAM, puis la classification de qualité sur le dataset OoC après un
split anti-fuite vérifié.
