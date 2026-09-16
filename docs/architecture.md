# Architecture technique

## Principes

1. **Local-first** : le projet doit fonctionner sans service commercial obligatoire.
2. **Reproductible** : une commande lance l'application et les versions sont fixees.
3. **Scientifiquement honnete** : aucune valeur de demonstration n'est presentee
   comme une performance de modele.
4. **Modulaire sans microservices prematurement** : API, interface et package ML
   sont separes, mais restent simples a executer.

## Flux principal

```text
React/TypeScript
    -> FastAPI
        -> stockage des experiences et images
        -> controle qualite des images
        -> segmentation cellulaire (phase suivante)
        -> embeddings et analyse phenotypique (phase suivante)
        -> resultats JSON et rapport
```

## Backend

L'API expose actuellement :

- `GET /api/v1/health`
- `POST /api/v1/experiments`
- `GET /api/v1/experiments`
- `GET /api/v1/experiments/{id}`
- `POST /api/v1/experiments/{id}/images`
- `POST /api/v1/experiments/{id}/analyze`
- `GET /api/v1/experiments/{id}/results`

Le stockage en memoire est un adaptateur initial. Il sera remplace par SQLite
quand les metadonnees definitives du dataset seront connues. Les images sont
stockees sous `data/experiments/{id}/images`.

## Pipeline ML cible

Le pipeline final devra comporter :

1. controle qualite et normalisation ;
2. segmentation des cellules ou noyaux ;
3. extraction de descripteurs morphologiques et d'embeddings ;
4. comparaison temoin/traitement ;
5. classification, regression ou detection d'anomalies selon les labels ;
6. estimation de l'incertitude ;
7. production de figures et d'un rapport tracable.

L'entrainement et l'evaluation restent des commandes hors API. L'API ne charge
que des artefacts valides et versionnes.

## Frontend

L'interface suit trois actions : definir l'experience, importer les images,
examiner les preuves. Elle doit rester comprehensible sans connaissance du code
et rendre visibles la version du pipeline, les avertissements et la provenance.

## Deploiement

`docker compose up --build` construit :

- `backend` sur le port 8000 ;
- `frontend` sur le port 8080 ;
- un volume persistant pour les images.

Pour la remise du challenge, une image unique ou une demonstration publique
pourra etre produite apres stabilisation du frontend et du modele.

