# API

Base locale : `http://localhost:8000/api/v1`.

La documentation OpenAPI interactive est disponible sur `/docs`.

## Santé

```http
GET /health
```

## Registre d'inférence

```http
GET /inference/engines
```

Retourne les moteurs disponibles, expérimentaux ou bloqués par une revue de
licence. Une présence dans le registre ne signifie pas qu'un moteur est
exécutable dans le chemin produit.

## Expériences

```http
POST /experiments
GET  /experiments
GET  /experiments/{experiment_id}
```

Exemple de création :

```json
{
  "name": "Réponse au composé A",
  "description": "Comparer la morphologie à 24 h",
  "control_label": "DMSO",
  "treatment_label": "Composé A"
}
```

## Images

```http
POST /experiments/{experiment_id}/images
Content-Type: multipart/form-data
```

Formats acceptés : PNG, JPEG, TIFF. Taille maximale par défaut : 25 Mo. Le
suffixe seul ne suffit pas : Pillow vérifie également que le contenu est une
image lisible.

## Inférence

```http
POST /experiments/{experiment_id}/analyze?engine_id=adaptive-segmentation-v1
GET  /experiments/{experiment_id}/results
GET  /experiments/{experiment_id}/artifacts/{filename}
```

Le résultat contient :

- version et fiche du moteur ;
- métriques agrégées ;
- métriques par image ;
- URLs des overlays ;
- avertissements ;
- horodatage.

## Erreurs principales

| Code | Signification |
|---:|---|
| 404 | expérience, résultat ou artefact absent |
| 409 | aucune image disponible pour l'analyse |
| 422 | moteur indisponible ou aucune image exploitable |
