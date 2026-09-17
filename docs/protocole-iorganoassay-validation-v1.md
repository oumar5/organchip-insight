# Protocole pré-enregistré — validation externe iOrganoAssay v1.1.0

Date de gel : **17 septembre 2026**
Statut : **protocole gelé avant calcul des scores adaptatifs**

## Question

Le moteur produit `adaptive-segmentation-1.1.0`, gelé sans entraînement,
segmente-t-il le premier plan d'organoïdes sur un dataset externe récent avec
une performance suffisamment homogène entre contrôle et traitement DSS ?

## Données

- iOrganoAssay **v1.1.0**, Zenodo `20351867`, CC0-1.0 ;
- archive de 1 817 410 571 octets, MD5
  `3cd6380e9413b977fdc531f32338ccd2` ;
- les **28 triplets officiels** du dossier `6.Validation` sont tous utilisés :
  14 `Ctrl` et 14 `DSS` ;
- chaque triplet contient l'image bright-field, le masque `GT` et la
  segmentation de référence `Seg` ;
- le manifeste verrouillé contient taille, dimensions et SHA-256 des 84
  fichiers.

L'archive haute résolution n'est pas extraite. Le téléchargement complet est
néanmoins vérifié avant l'extraction sélective du dossier de validation.

## Adaptation d'entrée fixée

Les images BF et les masques officiels n'ont pas la même résolution. L'image BF
est convertie en RGB puis redimensionnée **une seule fois** aux dimensions du
GT avec Pillow LANCZOS. Elle est ensuite convertie en niveaux de gris 0–1 et
transmise sans autre réglage au moteur gelé.

Le GT et la segmentation de référence sont convertis en niveaux de gris et
binarisés par `valeur > 0,5`, conformément au code R public iOrganoAssay. Aucun
seuil n'est choisi sur les résultats.

## Métriques

- précision, rappel, F1/Dice et IoU du premier plan par image ;
- erreur de centroïde normalisée par la diagonale ;
- macro-moyennes globales et séparées pour `Ctrl` et `DSS` ;
- intervalle bootstrap à 95 % du macro-F1, 10 000 tirages, seed `20260917` ;
- fraction des images dont F1 est inférieur à 0,50 ;
- mêmes agrégats pour la segmentation `Seg` fournie, à titre contextuel.

## Critères figés

Le résultat peut être cité comme preuve positive de généralisation externe
seulement si les trois critères sont satisfaits :

1. macro-F1 global ≥ 0,70 ;
2. macro-F1 de chaque condition ≥ 0,65 ;
3. au plus 20 % des images avec F1 < 0,50.

Un échec est publié tel quel. Aucun résultat ne peut modifier le moteur,
sélectionner un autre modèle, entraîner sur iOrganoAssay ou ouvrir le test OoC.

## Commandes reproductibles

```bash
uv run --project backend python backend/scripts/acquire_datasets.py \
  --resource iorganoassay-v1.1.0 --allow-large
make build-iorganoassay-manifest
make benchmark-iorganoassay
```
