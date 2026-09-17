# Stratégie de données

Dernière revue externe : **17 septembre 2026**.

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

## Recherche externe du 17 septembre 2026

La recherche n'a trouvé aucun second dataset public reproduisant exactement la
classification OoC `good`/`bad`. Les jeux ci-dessous répondent donc à d'autres
questions et ne doivent jamais être fusionnés avec l'entraînement actuel.

| Dataset | Contenu vérifié | Licence et taille | Décision avant soumission |
|---|---|---|---|
| [iOrganoAssay v1.1.0](https://doi.org/10.5281/zenodo.20351867) | 234 images bright-field, sorties de segmentation/morphométrie et dossier officiel de validation contenant 28 triplets BF/GT/Seg, répartis entre contrôle et DSS | CC0-1.0 ; ZIP 1 817 410 571 octets, MD5 `3cd6380e9413b977fdc531f32338ccd2` | **exécuté une fois** sur les 28 triplets : macro-F1 0,822746, IC 95 % [0,772415 ; 0,867911], trois critères sur trois atteints ; seuls les 84 fichiers du dossier de validation sont extraits |
| [Brain Organoid Dataset v2](https://doi.org/10.5281/zenodo.10301912) | 1 400 images de 64 organoïdes suivis, quatre clones, deux laboratoires, JPEG/TIFF et masques binaires manuels | CC-BY-4.0 ; ZIP 973 563 674 octets, MD5 `53e6b41af957ac33c03b927e0fbe69aa` | alternative robuste pour un protocole inter-laboratoire sur un sous-ensemble pré-enregistré |
| [MultiOrg](https://doi.org/10.34740/kaggle/ds/5097172) | plus de 400 images de plaques, plus de 60 000 boîtes d'organoïdes, 26 expériences et trois jeux d'annotations par deux experts | CC-BY-NC-SA-4.0 ; environ 35,4 Go | ne pas intégrer avant la soumission : coût, licence non commerciale et tâche de détection distincte ; conserver comme référence sur l'incertitude inter-annotateurs |
| [SWIFT](https://www.nature.com/articles/s42003-026-10768-x) | workflow 2026 de segmentation, classification et suivi ; entraînement YOLOv8s sur 417 images bright-field de côlon | données hébergées sur OMERO et code public ; bundle de reproduction encore à auditer | état de l'art uniquement ; ne pas introduire une nouvelle chaîne YOLO/SAM avant la release |

### Règle go/no-go

Un seul test externe supplémentaire est autorisé avant publication, uniquement
s'il tient dans un protocole borné, n'exige aucun réglage sur les résultats et
ne décale pas les tâches P0. iOrganoAssay v1.1.0 a été retenu parce qu'il fournit
un sous-ensemble officiel BF/GT/Seg explicitement destiné à la validation ; le
dataset cérébral reste une alternative non exécutée. L'archive complète de
1,82 Go est vérifiée, mais seuls les 84 fichiers de validation sont extraits.
Le résultat observé est publié tel quel : les trois critères pré-enregistrés
sont atteints, sans réglage postérieur. Il constitue une preuve de segmentation
du premier plan d'un organoïde, pas une validation de la classification OoC ni
du comptage cellulaire.
