# OrganChip Insight

OrganChip Insight est une plateforme reproductible d'analyse d'images de
microscopie pour comparer des groupes temoins et traites, quantifier des
changements phenotypiques et produire des rapports scientifiques auditables.

Le projet est concu pour le challenge **AI4S Open Innovation: AI for Life
Science**. Il est developpe localement, puis publie sous forme de depot public,
de demonstration et de Writeup Kaggle.

## Architecture

- `backend/` : API FastAPI, stockage local, analyse d'image et futurs modeles ML.
- `frontend/` : interface React, Vite et TypeScript.
- `docs/` : architecture, exigences du challenge, strategie de donnees et roadmap.
- `docker-compose.yml` : demonstration reproductible en deux conteneurs.

## Demarrage rapide avec Docker

```bash
cp .env.example .env
docker compose up --build
```

Puis ouvrir :

- application : <http://localhost:8080>
- API : <http://localhost:8000>
- documentation OpenAPI : <http://localhost:8000/docs>

## Developpement local

Backend :

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Frontend :

```bash
cd frontend
npm install
npm run dev
```

## Etat actuel

Le socle permet deja de :

- creer et lister des experiences ;
- televerser des images PNG, JPEG ou TIFF ;
- calculer une analyse d'image de reference (intensite, contraste et qualite) ;
- afficher les resultats dans une interface scientifique ;
- executer l'ensemble avec Docker.

La segmentation cellulaire, l'analyse phenotypique et la toxicite seront
ajoutees apres selection et audit du dataset. Aucune metrique scientifique
simulee n'est presentee comme un resultat de modele.

## Documentation

Commencer par [docs/README.md](docs/README.md).

