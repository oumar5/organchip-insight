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
- comptage, surfaces, diamètre, intensité, contraste et score qualité ;
- overlays de segmentation inspectables ;
- registre transparent des moteurs disponibles et candidats ;
- même pipeline depuis l'interface, l'API ou `inference.py` ;
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
uv run --project backend ruff check backend/app backend/tests backend/inference.py
uv run --project backend pytest backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose config --quiet
```

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

La priorité scientifique suivante est un benchmark reproductible sur BBBC019
Microfluidics et BBBC038, puis une démonstration sur le dataset OoC public.
