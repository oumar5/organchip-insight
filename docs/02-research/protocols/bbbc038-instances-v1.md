# Protocole BBBC038 d'instances et de comptage — v1

Statut : **pré-enregistré avant toute prédiction µSAM sur BBBC038**.

Date de gel : 17 septembre 2026.

## Question

Le moteur pré-entraîné µSAM `vit_b_lm` en mode APG, sans adaptation ni réglage sur
BBBC038, fournit-il une segmentation d'instances et un comptage nucléaire crédibles
sur un petit audit externe et hétérogène ?

Ce protocole ne valide pas le comptage de cellules sur les images organ-on-chip du
concours. Il mesure uniquement un transfert zéro-shot vers les noyaux annotés de
BBBC038.

## Données et sélection figées

- source : BBBC038 v1, `stage1_train.zip`, licence CC0-1.0 ;
- archive : 670 images et leurs masques d'instances ;
- SHA-256 de l'archive :
  `dcb6edc2690f137406638b2309581a71522c4dff19157d118453b448dcddcb68` ;
- sous-ensemble : 12 images dans
  `data/manifests/bbbc038-stage1-subset-v1.json` ;
- SHA-256 du manifeste :
  `c6c768b7b4aba84259e9e170bee5a5deb5354a898cdc3abcdaa4afb96f8cec2f`.

La sélection n'utilise ni les masques ni le nombre d'instances : une image médiane
par résolution exacte, puis trois images distinctes correspondant au minimum de
moyenne, au maximum de moyenne et au maximum d'écart-type en niveaux de gris. Les
égalités sont départagées par l'identifiant de l'image.

Ce plan couvre les neuf résolutions présentes, mais ne constitue pas un échantillon
aléatoire ni une estimation de performance sur les 670 images.

## Moteur figé

- `micro_sam==1.8.14` ;
- modèle `vit_b_lm`, poids CC-BY-4.0 ;
- segmentation APG, CPU, sans tuilage ;
- paramètres APG identiques au benchmark BBBC019 déjà exécuté ;
- aucun ajustement à partir des images, masques, overlays ou scores BBBC038.

La configuration exécutable est
`backend/evaluation/configs/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json`.

## Mesures figées

- appariement un-à-un des instances, priorité au nombre d'appariements puis à l'IoU ;
- précision, rappel, F1 et IoU moyen des objets appariés aux seuils IoU 0,50 et 0,75 ;
- agrégations macro par image et groupées sur les objets ;
- erreur de comptage signée, absolue et absolue relative par image ;
- MAE, erreur absolue relative moyenne et médiane ;
- métriques binaires de premier plan uniquement comme contexte ;
- intervalles bootstrap à 95 %, unité image, 10 000 itérations, seed 20260917 ;
- temps d'inférence et mémoire maximale du processus.

## Règle d'interprétation décidée avant exécution

Le résultat sera qualifié de **signal externe encourageant pour le comptage
nucléaire** seulement si les trois conditions suivantes sont réunies :

1. macro-F1 objet à IoU 0,50 au moins égal à 0,70 ;
2. macro-F1 objet à IoU 0,75 au moins égal à 0,50 ;
3. médiane de l'erreur absolue relative de comptage au plus égale à 20 %.

Cette qualification n'autorise toujours pas à présenter les composantes connexes
du produit comme un nombre de cellules OoC validé. Si une condition échoue, le
benchmark est documenté comme négatif ou mitigé et aucun paramètre n'est modifié.
Une éventuelle nouvelle expérience exigerait un protocole v2 distinct, motivé avant
d'examiner ses résultats.

## Sorties attendues

- JSON et CSV sous `reports/benchmarks/` ;
- overlays d'erreurs sous `reports/generated/`, non versionnés ;
- retour d'expérience daté avec décision produit ;
- aucun accès au test gelé de classification OoC.
