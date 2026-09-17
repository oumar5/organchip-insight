# Comparaison des moteurs alimentée par les rapports — 17 septembre 2026

## Objectif

Rendre les preuves de segmentation et de comptage visibles dans le produit sans
recopier de métrique à la main et sans suggérer qu'un résultat externe valide le
comptage sur les images organ-on-chip (OoC).

## Réalisation

Le script `backend/evaluation/build_benchmark_summary.py` lit quatre rapports
versionnés :

- `reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json` ;
- `reports/benchmarks/bbbc019-microfluidic-microsam-vit-b-lm-apg.json` ;
- `reports/benchmarks/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json`.
- `reports/benchmarks/iorganoassay-validation-v1.1.0-adaptive-v1.json`.

Il valide leurs identifiants, vérifie que les deux évaluations BBBC019 couvrent
le même nombre d'images, calcule le SHA-256 de chaque source et génère
`frontend/public/benchmark-summary.json`. La cible `make benchmark-summary`
régénère le fichier ; `make check` échoue s'il n'est plus synchronisé.

La vue affiche les F1 et IoU, les intervalles bootstrap disponibles, le temps
CPU par image, le pic mémoire et la décision de promotion. Elle sépare
explicitement BBBC019 (premier plan sur 13 images DIC externes) de BBBC038
(instances nucléaires sur un sous-ensemble pré-enregistré de 12 images) et
d'iOrganoAssay (premier plan d'un organoïde cible sur 28 triplets officiels).
Les scores ne sont jamais comparés entre ces jeux.

## Vérifications

- tests unitaires du générateur, y compris le refus de rapports BBBC019 portant
  sur des effectifs différents ;
- type-check et build du frontend ;
- contrôle de synchronisation du JSON généré ;
- scénario Playwright étendu pour vérifier les métriques et la décision de
  non-promotion dans le navigateur ;
- contrôle Axe et plancher typographique conservés par le même scénario.

## Résultat observé

Sur BBBC019, µSAM améliore le score de premier plan mais coûte environ 43 s par
image et 8,7 Go de mémoire dans l'environnement mesuré. Sur BBBC038, il échoue
à deux critères d'instances pré-enregistrés sur trois. Il reste donc un
benchmark isolé ; le moteur adaptatif demeure le moteur produit.

Le résultat BBBC038 ne valide pas le comptage de cellules sur les images OoC.
L'interface conserve le terme « composantes connexes » et la réserve associée.

La validation iOrganoAssay a été ajoutée après pré-enregistrement et exécution
unique : macro-F1 `0,822746`, IC 95 % `[0,772415 ; 0,867911]`, contrôle
`0,836929`, DSS `0,808564`, trois critères sur trois atteints. La carte précise
que le GT cible un organoïde et que le résultat ne valide ni les instances plein
champ, ni le comptage cellulaire, ni la classification OoC. Le protocole et
l'analyse d'erreur sont consignés dans le
[REX iOrganoAssay](2026-09-17-validation-externe-iorganoassay.md).

## Limites et décision

Les overlays d'erreur sont bien générés par les scripts de benchmark et gardés
comme artefacts locaux, mais ils ne sont pas copiés dans le frontend. Ce choix
évite d'alourdir le produit avec des images de datasets externes et maintient
la provenance dans les rapports et les REX. Une galerie destinée au rapport ou
à la vidéo pourra être produite à partir de ces mêmes commandes, avec
attribution, sans modifier les décisions produit.
