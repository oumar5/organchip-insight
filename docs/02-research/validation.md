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

- audit borné de 12 images sélectionnées sans utiliser les masques : une image
  par résolution puis trois extrêmes d'apparence ;
- précision, rappel et F1 par objet à IoU 0,50 et 0,75 ;
- erreur absolue et relative de comptage ;
- contexte pixel, temps CPU et mémoire.

Le protocole pré-enregistré et exécuté le 17 septembre 2026 donne un macro-F1
objet de `0,628327` à IoU 0,50 et `0,481698` à IoU 0,75. L'erreur absolue
relative médiane de comptage est `15,3409 %`, mais le moteur sous-compte
globalement 230 noyaux (`539` prédits contre `769` annotés). Deux des trois
critères de qualification échouent : µSAM n'est pas promu dans le produit et
ce benchmark nucléaire externe ne valide pas le comptage sur les images OoC.
Rapport :
[`bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json`](../../reports/benchmarks/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json).

### BBBC019 Microfluidics

- 13 images et masques de premier plan ;
- précision, rappel, F1 et IoU ;
- analyse d'erreur image par image ;
- comparaison avec les résultats historiques publiés uniquement à protocole égal.

La première mesure figée de `adaptive-segmentation-v1` donne un macro-F1 de
0,424892 et un macro-IoU de 0,273632. Le rapport complet, les intervalles et les
13 lignes image par image sont dans
[`reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json`](../../reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json).
Ce résultat valide le protocole, pas la qualité suffisante du moteur.

## Validation OoC

Sur le dataset Zenodo OoC :

- stratifier par type cellulaire, densité, temps et débit quand disponibles ;
- mesurer les taux d'échec et la stabilité des métriques ;
- faire relire un échantillon d'overlays ;
- ne pas créer de label de qualité qui n'existe pas dans les métadonnées.

### Classification de qualité d'image

Avant tout CNN, le split groupé a été réaudité sur les **2 216 621** paires
d'images appartenant à deux splits différents. L'écran dHash 256 bits à
distance de Hamming maximale 8 ne trouve aucun candidat inter-split. Cette
preuve est exhaustive pour ce critère précis, mais ne couvre pas toutes les
rotations, recadrages ou transformations possibles.

Les propriétés d'acquisition constituent en revanche un raccourci mesurable.
Une baseline catégorielle ajustée uniquement sur le train, avec lissage de
Laplace et seuil fixé à 0,5, obtient :

| Entrées mode + résolution | Macro-F1 | Balanced accuracy | ROC-AUC |
|---|---:|---:|---:|
| Validation | 0,690231 | 0,713283 | 0,719120 |
| Test groupé | 0,695068 | 0,713569 | 0,713569 |

Ce résultat n'est pas une baseline visuelle utile au produit : il quantifie le
risque qu'un modèle apprenne le dispositif ou le format d'acquisition. Tout CNN doit donc publier ses tranches `L`/`RGB` et par résolution, puis
démontrer un gain au-delà de ce raccourci et des autres métadonnées du
manifeste (bucket de jour, lignée), apprises sur le seul train.

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

Lecture honnête de ces deux tableaux : sur le test groupé, la macro-F1 du
baseline image-only (0,692) n'est pas distinguable de celle du raccourci
mode + résolution (0,695) ; seule la ROC-AUC sépare les deux (0,803 contre
0,714). Il n'existe donc pas de preuve qu'un modèle apprenne la qualité d'image
au-delà des propriétés d'acquisition. Ce constat est confirmé sur la campagne
v2 : après validation GPU, comparateurs et ablations A/B (17 septembre 2026),
aucun signal de qualité robuste et indépendant des métadonnées d'acquisition
et de culture n'est démontré, et le test n'a jamais été ouvert. Tout futur CNN doit
être jugé d'abord **à mode d'acquisition égal**.

Rapport :
[`reports/benchmarks/ooc-handcrafted-image-quality-v1.json`](../../reports/benchmarks/ooc-handcrafted-image-quality-v1.json).

Audit du split et des raccourcis :
[`reports/ooc-grouped-split-v1.json`](../../reports/ooc-grouped-split-v1.json).

### Contrôle technique du pipeline CNN

Le runtime MobileNetV3 du commit `92bf217fccb4784949411d2025a626bfbcea1015`
a passé un smoke test CPU déterministe : huit images train, quatre images de
validation, une époque et graine `20260916`. Les hashes des 12 images ont été
vérifiés. Le manifeste test n'a jamais été ouvert et le rapport marque
explicitement ce run `benchmark_eligible: false`.

La macro-F1 de validation `0,333333` et la ROC-AUC `0,5` ne sont que des
témoins d'exécution sur quatre images avec une initialisation aléatoire. Elles
ne doivent être comparées ni aux baselines ci-dessus, ni à un résultat publié.

L'export ONNX opset 18 accepte les lots dynamiques 1, 2 et 3. Son écart absolu
maximal avec PyTorch est `1,862645149230957e-09`, sous la tolérance `1e-4`.
La validation complète avec poids ImageNet locaux vérifiés a ensuite été
exécutée sur GPU Kaggle dans le run `kaggle-validation-campaign-v2`. Le meilleur
checkpoint est celui de l'époque 3. À seuil fixe 0,5, il atteint une macro-F1 de
`0,736102` et une balanced accuracy de `0,740072` sur 509 images de validation.
Après sélection du seuil sur cette même validation, le seuil gelé `0,42` donne
une macro-F1 de `0,762687` et une balanced accuracy de `0,761943`.

La baisse continue de la perte train et la dégradation de la perte validation
après l'époque 3 signalent un surapprentissage ; l'arrêt anticipé a été
déclenché à l'époque 9 après six époques sans amélioration. Le test n'a pas été
ouvert. La sélection gelée porte le SHA-256
`852692b5d4ccc51573b0c94cb98f5c5603d4ed0f09ace2d38afbe803be5d6a9d`.

L'export ONNX opset 18 passe la parité avec une erreur absolue maximale de
`2,0265579223632812e-06`, sous la tolérance `1e-4`. Son instantané runtime porte
toutefois le libellé ambigu `mode: smoke` alors qu'il réutilise le checkpoint
de validation vérifié ; le code a été corrigé depuis (`operation: onnx-export`, `execution_device`) ;
l'artefact historique conserve volontairement ce libellé pour préserver son hash.

Cette revue du bootstrap groupé et des tranches, puis les ablations
pré-enregistrées A/B, ont été réalisées le 17 septembre 2026 : aucune
configuration n'atteint le plancher de `0,65` de balanced accuracy par mode,
aucun accès au test n'a lieu et la modélisation CNN est close (voir le
[contre-audit](audits/audit-2026-09-17-classification-cnn.md)). Le protocole
scientifique réservait un seul accès final au test après cette revue. Le verrou logiciel refuse une
seconde tentative dans un workspace qui conserve son reçu ; ce reçu devra être
archivé hors de tout workspace Kaggle éphémère, car le verrou n'est pas global
entre deux environnements recréés.

Détails, artefacts et hashes :
[retour d'expérience du smoke CNN](../06-retrospectives/2026-09-16-pipeline-cnn-smoke.md).

Validation GPU complète :
[retour d'expérience de la campagne v2 Kaggle](../06-retrospectives/2026-09-16-validation-cnn-kaggle-campagne-v2.md).

### Démonstrateur CNN expérimental

Le run B est intégré localement comme démonstrateur ONNX CPU, sans promotion en
modèle de contrôle qualité. Le runtime vérifie les hashes du modèle, du
prétraitement et des labels avant chargement. Il produit seulement un softmax
brut non calibré, impose `À vérifier` à chaque image, refuse de scorer les modes
source hors `L`/`RGB` et ne génère ni overlay ni comptage. Le smoke réel sur une
image L et une image RGB du manifeste train/validation est documenté dans le
[REX du 17 septembre](../06-retrospectives/2026-09-17-demonstrateur-cnn-onnx.md).

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
