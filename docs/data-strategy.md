# Stratégie de données

## Décision en trois jeux

| Rôle | Dataset | Licence | Pourquoi |
|---|---|---|---|
| Démonstration OoC | [OOC Image Dataset](https://doi.org/10.5281/zenodo.10203721) | CC-BY-4.0 | 3 072 bright-fields et métadonnées OoC |
| Validation microfluidique | [BBBC019 Microfluidics](https://bbbc.broadinstitute.org/BBBC019) | CC-BY 3.0 | images DIC et masques manuels |
| Validation d'instances | [BBBC038](https://bbbc.broadinstitute.org/BBBC038) | CC0 | diversité et masques de noyaux |

Cette combinaison couvre pertinence applicative, vérité terrain et
généralisation sans imposer un téléchargement de plusieurs centaines de Go.

## Fiche obligatoire avant téléchargement

Pour chaque version :

- URL et date d'accès ;
- identifiant/version ;
- licence exacte et obligations ;
- checksum des archives ;
- modalités, canaux et résolution ;
- structure des métadonnées ;
- unité biologique et unité de réplication ;
- cible, vérité terrain et métriques ;
- règles de redistribution.

## Split anti-fuite

Le split suit la plus grande unité disponible : expérience, plaque, puce, puits,
donneur ou acquisition. Des images voisines d'une même unité ne doivent pas être
réparties aléatoirement entre entraînement et test.

Ordre préféré :

1. validation externe sur un dataset distinct ;
2. test par expérience ou plaque entière ;
3. validation par groupe ;
4. entraînement sur les groupes restants.

Les normalisations et sélections de caractéristiques sont ajustées uniquement
sur l'entraînement.

## Étapes

1. télécharger BBBC019 Microfluidics et exécuter la baseline ;
2. télécharger BBBC038 stage 1 et figer un benchmark ;
3. télécharger les métadonnées OoC avant les images ;
4. vérifier les valeurs manquantes et unités ;
5. sélectionner un sous-ensemble reproductible ;
6. intégrer un manifeste versionné, jamais les données brutes dans Git.

Le manifeste actif est dans [`data/manifests/datasets.json`](../data/manifests/datasets.json).
L'archive OoC complète est désactivée par défaut : les 15 Gio libres observés le
16 septembre 2026 ne suffisent pas à garantir archive + extraction sans risque.

## Métriques

- premier plan : précision, rappel, F1, IoU ;
- instances : Dice/IoU, précision/rappel par objet, erreur de comptage ;
- robustesse : taux d'échec par modalité, condition et lot ;
- performance : secondes par mégapixel et mémoire maximale ;
- phénotype futur : effet standardisé et intervalle de confiance par unité.

## Données écartées pour le premier jalon

RxRx1 est riche mais pèse 296 Go et sa licence est CC-BY-NC-SA. JUMP est encore
plus volumineux. Ces ressources pourront servir via profils pré-calculés, pas
comme dépendance de la première démonstration.
