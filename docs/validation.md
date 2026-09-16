# Plan de validation

## Niveaux de preuve

| Niveau | Définition | État |
|---|---|---|
| L0 | chemin technique testé sur images synthétiques | atteint |
| L1 | contrôle qualitatif sur données publiques réelles | à réaliser |
| L2 | métriques figées sur vérité terrain externe | à réaliser |
| L3 | comparaison témoin/traitement avec réplications | à réaliser |
| L4 | validation sur données OoC externes | cible de soumission |

L'interface ne doit jamais présenter un résultat L0 ou L1 comme une conclusion
biologique.

## Validation de segmentation

### BBBC038

- split par source/contexte d'imagerie, pas image aléatoire uniquement ;
- Dice et IoU pixel ;
- précision, rappel et F1 par objet ;
- erreur absolue de comptage ;
- temps CPU par mégapixel.

### BBBC019 Microfluidics

- 13 images et masques de premier plan ;
- précision, rappel, F1 et IoU ;
- analyse d'erreur image par image ;
- comparaison avec les résultats historiques publiés uniquement à protocole égal.

## Validation OoC

Sur le dataset Zenodo OoC :

- stratifier par type cellulaire, densité, temps et débit quand disponibles ;
- mesurer les taux d'échec et la stabilité des métriques ;
- faire relire un échantillon d'overlays ;
- ne pas créer de label de qualité qui n'existe pas dans les métadonnées.

## Intervalles et répétabilité

- bootstrap par unité expérimentale, jamais seulement par image ;
- graine enregistrée ;
- versions des données et modèles figées ;
- mêmes entrées : mêmes sorties pour la baseline déterministe ;
- résultat brut JSON conservé avec les figures.

## Tests logiciels

- unitaires : normalisation, segmentation, repository ;
- API : création, upload, rejet, inférence, artefact ;
- frontend : type-check et build ;
- intégration : Docker Compose ;
- smoke test : parcours complet sur une image de référence.

## Critère de stabilité du MVP

- zéro erreur connue de sévérité bloquante ;
- tous les tests automatisés passent ;
- redémarrage sans perte des expériences ;
- upload corrompu rejeté ;
- résultat reproductible sur CPU ;
- documentation alignée sur l'API effective.

