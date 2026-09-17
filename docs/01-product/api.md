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
licence. `status` décrit la maturité scientifique ; `runnable` décrit la
disponibilité technique et `unavailable_reason` explique une indisponibilité.

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

Formats acceptés : PNG, JPEG, TIFF monopage. Couleur 8 bits et niveaux de gris
entiers 8/16 bits. Les images flottantes et multipages sont rejetées explicitement.
Le contenu est décodé avant acceptation. Limites par défaut : 25 Mio par fichier
et 16 777 216 pixels ; configurables à la baisse. `GET /inference/upload-limits`
retourne les limites effectives utilisées par l'interface.

L'interface envoie un fichier par requête puis affiche `accepted_files`,
`rejected_files`, `rejection_reasons` et `duplicate_files`. Les doublons binaires
au sein d'une expérience sont ignorés, même sous un autre nom. Leur détection
ne constitue pas une détection des quasi-doublons scientifiques.

L'ajout effectif d'une image invalide le résultat précédent. Un rejet ou un
doublon seul conserve un résultat encore applicable. Import et analyse sont
deux actions séparées : une relance d'analyse ne téléverse rien.

## Images importées et aperçus

```http
GET /experiments/{experiment_id}/images
GET /experiments/{experiment_id}/previews/{filename}
```

La liste renvoie, pour chaque image stockée, le nom de stockage, le nom
d'affichage, la taille et l'URL d'un aperçu PNG 8 bits généré à la demande et
mis en cache. Les images monocanal, TIFF 16 bits compris, sont étirées entre
leurs percentiles 1 et 99 pour l'affichage uniquement ; aucune mesure n'utilise
ces aperçus.

## Inférence

```http
POST /experiments/{experiment_id}/analyze?engine_id=adaptive-segmentation-v1
POST /experiments/{experiment_id}/analyze?engine_id=ooc-quality-cnn-campaign-v2-gray448
GET  /experiments/{experiment_id}/results
GET  /experiments/{experiment_id}/exports/results.json
GET  /experiments/{experiment_id}/exports/results.csv
GET  /experiments/{experiment_id}/artifacts/{filename}
```

Le résultat contient :

- version et fiche du moteur ;
- métriques agrégées ;
- résultats par image discriminés par `analysis_type` ;
- URLs des overlays pour une segmentation, ou softmax brut abstentionniste et
  mode source pour le démonstrateur CNN ;
- avertissements ;
- provenance des artefacts consommés ;
- horodatage.

L'export JSON conserve le résultat complet et sa provenance. Le CSV contient
une ligne par image et des colonnes adaptées au type de résultat ; les deux
réponses sont servies comme pièces jointes.

## Erreurs principales

| Code | Signification |
|---:|---|
| 404 | expérience, résultat ou artefact absent |
| 409 | aucune image disponible, ou analyse déjà en cours |
| 422 | moteur indisponible ou aucune image exploitable |
| 500 | échec inattendu : statut `failed`, images conservées pour réessayer |

Le déploiement actuel utilise **un seul processus API**. Les imports et débuts
d'analyse sont sérialisés ; une analyse en cours bloque les mutations de son
expérience. Au redémarrage, les analyses interrompues passent à `failed`.
Le passage à plusieurs workers exige une file de tâches et une coordination
interprocessus ; ce changement n'est pas couvert par ces garanties.
