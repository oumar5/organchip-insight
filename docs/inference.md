# Inférence avant entraînement

## Décision

Le projet fournit immédiatement un moteur `adaptive-segmentation-v1`. Il ne
nécessite ni poids préentraînés, ni GPU, ni entraînement local. Il constitue une
baseline exécutable et non une preuve de performance biologique.

## Pipeline actuel

Depuis `adaptive-segmentation-1.1.0`, les niveaux de gris 16 bits sont lus sans
conversion écrêtante en 8 bits : division par 65535 pour les mesures et mise à
l'échelle pour l'overlay. Le seuillage conserve sa normalisation P1/P99.
L'échelle d'intensité est celle du conteneur entier, pas une calibration physique
du capteur (notamment pour du 12 bits stocké dans un TIFF 16 bits).
Le chemin 8 bits est inchangé. Les anciens rapports restent ceux du moteur 1.0.0.

Pour chaque image :

1. conversion en intensité et normalisation robuste entre les percentiles 1 et 99 ;
2. calcul automatique du seuil d'Otsu ;
3. sélection du premier plan clair ou sombre selon sa plausibilité spatiale ;
4. fermeture morphologique et retrait des petits artéfacts ;
5. étiquetage des composantes connexes ;
6. mesure du nombre d'objets, de la surface et du diamètre équivalent ;
7. production d'un overlay PNG avec masque et contours.

Le seuillage, l'étiquetage et les mesures reposent sur les primitives documentées
de [scikit-image](https://scikit-image.org/docs/stable/). Les sorties sont
calculées à partir des pixels réellement fournis.

## Contrat scientifique

Le moteur peut servir à :

- vérifier le chemin de données de bout en bout ;
- détecter des images vides, sombres ou faiblement contrastées ;
- établir une baseline mesurable ;
- préparer un protocole de comparaison de moteurs ;
- produire une première démonstration réelle.

Il ne peut pas encore servir à :

- affirmer que chaque composante est une cellule ;
- séparer correctement tous les objets en contact ;
- conclure à une toxicité ou une efficacité ;
- remplacer une annotation et une validation expertes.

## Registre des moteurs

| Moteur | État | Usage | Décision |
|---|---|---|---|
| Segmentation adaptative v1 | disponible | baseline CPU locale | moteur par défaut |
| µSAM | expérimental | benchmark isolé préentraîné | meilleur sur BBBC019, non activé dans le chemin produit |
| Cellpose | revue de licence | segmentation généraliste | non activé par défaut |

Le code Cellpose est sous licence BSD, mais le dépôt officiel indique que les
modèles ont été entraînés sur des données CC-BY-NC. L'usage dans un challenge à
prix doit donc être clarifié avant intégration. µSAM est publié sous licence MIT,
et le checkpoint BBBC019 évalué est enregistré avec sa licence CC-BY-4.0 et ses
SHA-256. Tout autre checkpoint devra refaire cette vérification de provenance.

Sources :

- [Cellpose, documentation officielle](https://cellpose.readthedocs.io/en/latest/)
- [Cellpose, dépôt et note de licence des données](https://github.com/MouseLand/cellpose)
- [µSAM, dépôt officiel](https://github.com/computational-cell-analytics/micro-sam)
- [µSAM, article Nature Methods](https://doi.org/10.1038/s41592-024-02580-4)

## Interface Python

```python
from pathlib import Path
from app.ml.pipeline import AdaptiveSegmentationAnalyzer

output = AdaptiveSegmentationAnalyzer().analyze(
    [Path("image.tif")],
    artifact_dir=Path("artifacts"),
    artifact_url_prefix=".",
)
print(output.metrics)
```

## Interface en ligne de commande

Depuis `backend/` :

```bash
uv run python inference.py image-1.png image-2.tif --output-dir artifacts/demo
```

La commande écrit les overlays et `result.json`. Ce fichier contient la version
du pipeline, le registre du moteur, les métriques par image et les avertissements.

## Prochaine condition de promotion

Un moteur préentraîné ne remplace la baseline que s'il :

1. possède une licence compatible et documentée ;
2. fonctionne sur CPU ou dispose d'un repli CPU ;
3. est évalué sur un split figé de BBBC038 et BBBC019 ;
4. améliore les métriques principales avec intervalles de confiance ;
5. conserve overlays, provenance et limites dans l'interface.
