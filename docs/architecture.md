# Architecture technique

## Vue d'ensemble

```text
React + TypeScript
       |
       | JSON / multipart
       v
FastAPI ---------------------------------------------------+
       |                                                   |
       +--> SQLite : expériences et résultats              |
       +--> volume local : images et overlays              |
       +--> registre de moteurs                            |
               |                                           |
               +--> segmentation adaptative (disponible)  |
               +--> CNN QC run B (expérimental, optionnel) |
               +--> µSAM (expérimental, benchmark isolé)  |
               +--> Cellpose (revue de licence)            |
                                                           |
CLI inference.py ------------------------------------------+
```

## Principes

1. **Local-first** : aucun service commercial obligatoire.
2. **Inférence immédiate** : la baseline fonctionne avant tout entraînement.
3. **Moteurs explicites** : tâche, maturité, exécutabilité et type de sortie sont discriminés.
4. **Persistance simple** : SQLite et fichiers suffisent au MVP.
5. **Preuve visible** : chaque segmentation génère un overlay ; une classification
   expérimentale expose son mode source, ses hashes et son abstention.
6. **Reproductibilité** : API, CLI et interface utilisent le même pipeline.

## Backend

```text
backend/
├── app/
│   ├── api/routes/        endpoints HTTP
│   ├── ml/pipeline.py     inférence et artefacts
│   ├── ml/quality_classifier.py  runtime ONNX expérimental à fermeture sûre
│   ├── ml/registry.py     disponibilité et limites des moteurs
│   ├── repository.py      persistance SQLite
│   ├── schemas.py         contrat Pydantic
│   └── main.py            application FastAPI
├── inference.py           entrée CLI recommandée par Kaggle
├── tests/                 tests API et persistance
├── training/              entraînement contrôlé et protocoles CNN
└── evaluation/            benchmarks reproductibles et configurations figées
```

Le pipeline est synchrone et FastAPI l'exécute dans son pool de threads. C'est
adapté au MVP local. Avant exposition multi-utilisateur, les inférences devront
être placées dans une file de tâches avec timeouts, annulation et quotas.

## Stockage

```text
data/
├── organchip.sqlite3
└── experiments/{uuid}/
    ├── images/
    └── artifacts/
```

SQLite conserve expériences, statuts et résultats JSON après redémarrage. Les
images et overlays restent sur le volume. Cette séparation facilite une future
migration vers PostgreSQL + stockage objet sans modifier le contrat API.

## Frontend

Le frontend suit trois actions : définir, analyser, vérifier. Il affiche la
version du pipeline, le niveau de preuve, les avertissements et la provenance.
Il ne contient aucun résultat de démonstration simulé.

## Contrat de moteur

Un moteur fournit :

- une fiche `AnalysisEngine` ;
- des métriques agrégées ;
- des résultats par image ;
- des artefacts visuels ;
- des avertissements ;
- une provenance d'artefacts ;
- une version immuable.

La fiche sépare `available`, `experimental`, `planned` et `license-review`, puis
indique indépendamment `runnable`. Un moteur non exécutable ne peut pas être
invoqué par l'API.

## Déploiement

Docker Compose lance :

- backend FastAPI sur `8000` ;
- frontend Nginx sur `8080` ;
- volume persistant `organchip_data`.

L'image frontend relaie `/api/` vers le backend. Les dépendances sont verrouillées
par `uv.lock` et `package-lock.json`.

## Décisions à venir

- OME-TIFF/OME-Zarr et métadonnées multidimensionnelles ;
- tâches asynchrones ;
- comparaison contrôle/traitement par unité expérimentale ;
- export PDF/CSV ;
- stockage d'artefacts adressé par hash ;
- observabilité et authentification pour une démo publique.
