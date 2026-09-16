# Plan de validation

## Niveaux de preuve

| Niveau | Définition | État |
|---|---|---|
| L0 | chemin technique testé sur images synthétiques | atteint |
| L1 | contrôle qualitatif sur données publiques réelles | atteint le 16 septembre 2026 |
| L2 | métriques figées sur vérité terrain externe | atteint pour BBBC019 le 16 septembre 2026 |
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

La première mesure figée de `adaptive-segmentation-v1` donne un macro-F1 de
0,424892 et un macro-IoU de 0,273632. Le rapport complet, les intervalles et les
13 lignes image par image sont dans
[`reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json`](../reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json).
Ce résultat valide le protocole, pas la qualité suffisante du moteur.

## Validation OoC

Sur le dataset Zenodo OoC :

- stratifier par type cellulaire, densité, temps et débit quand disponibles ;
- mesurer les taux d'échec et la stabilité des métriques ;
- faire relire un échantillon d'overlays ;
- ne pas créer de label de qualité qui n'existe pas dans les métadonnées.

### Classification de qualité d'image

Le premier baseline image-only utilise 50 caractéristiques déterministes, sans
poids externe. Le modèle et le seuil sont sélectionnés uniquement sur la
validation groupée par préfixe `YYMMDD` ; le test contient neuf préfixes tenus à
l'écart.

| Split | Macro-F1 | Balanced accuracy | ROC-AUC |
|---|---:|---:|---:|
| Validation | 0,761214 | 0,755174 | 0,825165 |
| Test groupé | 0,692077 | 0,693102 | 0,802821 |

L'intervalle bootstrap par préfixe du macro-F1 test est
`[0,561284 ; 0,750882]`. Cette largeur et la baisse face à la validation doivent
rester visibles. Le préfixe est seulement une heuristique de date ; ce résultat
mesure une généralisation à des dates tenues à l'écart, pas à des puces ou
expériences indépendantes documentées.

Rapport :
[`reports/benchmarks/ooc-handcrafted-image-quality-v1.json`](../reports/benchmarks/ooc-handcrafted-image-quality-v1.json).

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
