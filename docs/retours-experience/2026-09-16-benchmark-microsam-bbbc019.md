# Benchmark zero-shot µSAM sur BBBC019

Date : **16 septembre 2026**

Statut : **benchmark isolé terminé ; résultat expérimental, pas validation OoC**

## Question

Le modèle de microscopie préentraîné µSAM, utilisé avec son générateur de
propositions automatique (APG), segmente-t-il mieux le sous-ensemble
microfluidique de BBBC019 que le moteur adaptatif instantané ? Quel est le coût
de ce gain sur CPU local ?

Ce benchmark mesure une segmentation binaire sur 13 images DIC externes. Il ne
mesure ni la qualité `good`/`bad` des images OoC, ni un effet biologique, ni une
performance clinique.

## Provenance et artefacts

| Élément | Valeur |
|---|---|
| Code évalué | commit `b440d2795bdeea7e89b424de2b112d1df9e29274` |
| Dataset | BBBC019 version 2, sous-ensemble Microfluidic, CC-BY-3.0 |
| Images évaluées | 13 images DIC et leurs 13 masques officiels `manual` |
| SHA-256 archive | `968b74f478b59d8a558ea2582fea9796e3c2845922077819a5f7b6db6c157b5f` |
| Moteur | µSAM `1.8.14`, modèle `vit_b_lm`, mode `apg`, CPU, sans tuilage |
| Configuration | [`bbbc019-microfluidic-microsam-vit-b-lm-apg.json`](../../backend/evaluation/configs/bbbc019-microfluidic-microsam-vit-b-lm-apg.json) |
| SHA-256 configuration | `df5b1017a1cb03bcf2e01751c7e48f256e1c8492338f05c551bda5f0809f5976` |
| Rapport | [`bbbc019-microfluidic-microsam-vit-b-lm-apg.json`](../../reports/benchmarks/bbbc019-microfluidic-microsam-vit-b-lm-apg.json) |
| SHA-256 rapport | `91b5169e5139e8536c2dbd5a9d002e73e3c1581f5b7407d2ec87cfc8b2dcc203` |
| Environnement minimal | [`environment.yml`](../../backend/experiments/micro-sam/environment.yml) |
| SHA-256 environnement | `f613f7fc60dc4844d7874b3604f98624e038a05a1bd06141415b4e92e34a14dc` |

Le rapport a été produit dans un environnement Conda isolé avec Python
`3.12.14` sur macOS x86_64. Le fichier d'environnement fixe Python `3.12` et
`micro_sam=1.8.14`, mais ne verrouille pas toutes les dépendances transitives :
il décrit une reconstruction minimale, pas une promesse de reproduction bit à
bit sur une autre machine.

## Reproduction actuelle

```bash
conda env create --file backend/experiments/micro-sam/environment.yml
make benchmark-bbbc019-microsam
```

La cible utilise par défaut `conda run --name organchip-microsam python`. Le
lanceur `MICROSAM_PYTHON` peut être surchargé explicitement si l'environnement
est installé sous un autre nom ou préfixe.

## Poids et licences

Le code µSAM est sous licence MIT. Les poids déclarés proviennent du modèle
BioImage.IO `diplomatic-bug` et sont sous CC-BY-4.0.

| Poids | Taille | SHA-256 |
|---|---:|---|
| `vit_b_lm` | 375 023 499 octets | `ffe862fa5b58d78375506041faf0eb3927ced5b5391e8be383e6d7ac07aed924` |
| `vit_b_lm_decoder` | 38 393 613 octets | `3a1566aada52e24299286527ec60c966d213db86ee656c67439c71c1b4182c26` |

## Protocole

- les paramètres APG de µSAM `1.8.14` sont laissés à leurs valeurs par défaut
  et figés avant lecture des métriques BBBC019 ;
- aucun ajustement n'est effectué à partir des 13 masques ;
- µSAM produit des instances, fusionnées en un masque de premier plan binaire
  avant comparaison au masque officiel `manual` ;
- les agrégats macro sont des moyennes non pondérées entre images ; les
  agrégats micro regroupent les pixels ;
- les intervalles à 95 % utilisent 10 000 rééchantillonnages des images avec la
  graine `20260916`.

Il s'agit donc d'un essai zero-shot strict de cette configuration, pas d'une
estimation de la meilleure performance atteignable après réglage.

## Résultats

| Agrégation µSAM | Précision | Rappel | F1 | IoU |
|---|---:|---:|---:|---:|
| Macro, moyenne des 13 images | 0,832314 | 0,819924 | 0,815542 | 0,698535 |
| Micro, pixels regroupés | 0,845972 | 0,742025 | 0,790596 | 0,653707 |

L'intervalle bootstrap à 95 % de la macro-F1 est
`[0,758206 ; 0,861862]`. Il quantifie la variabilité entre ces 13 images, pas
entre expériences biologiques indépendantes.

Sur le même sous-ensemble et les mêmes masques, la baseline adaptative obtenait
une macro-F1 de `0,424892` et une macro-IoU de `0,273632`. Le SHA-256 de son
[rapport](../../reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json) est
`d7a915d670561cbe66757ce25de9ab29aea91ee93c1f856f1051638f5012ccac`.

## Coût local observé

| Mesure | µSAM | Baseline adaptative |
|---|---:|---:|
| Inférence moyenne par image | 42,843791 s | 0,112333 s |
| Inférence moyenne par mégapixel | 40,859023 s | 0,107129 s |
| Total avec overlays | 560,935463 s | 8,514448 s |
| Pic RSS du processus | 8 702,957 Mo | 324,668 Mo |

µSAM demande aussi `18,610024` secondes de chargement du moteur dans cette
exécution. Ces mesures décrivent la machine et les environnements locaux des
rapports ; elles indiquent un ordre de grandeur, pas un benchmark matériel
universel.

## Limites

1. BBBC019 Microfluidic est un petit dataset DIC externe, pas le dataset OoC du
   challenge.
2. Les 13 images ne représentent pas 13 expériences biologiques indépendantes ;
   le bootstrap par image ne crée pas cette indépendance.
3. La fusion des instances µSAM en masque binaire évalue le premier plan, pas la
   qualité de la séparation entre cellules.
4. Les valeurs historiques TScratch, MultiCellSeg et Topman restent uniquement
   contextuelles tant que prétraitements et annotations ne sont pas prouvés
   identiques.
5. Le fichier Conda minimal et les hashes de poids renforcent l'auditabilité,
   sans verrouiller tout le graphe logiciel et le matériel.

## Décision

- conserver le moteur adaptatif comme aperçu local instantané et explicable ;
- conserver µSAM comme moteur expérimental, isolé et potentiellement
  asynchrone, compte tenu de son gain de segmentation mais aussi de son coût CPU
  et mémoire ;
- ne pas présenter ce résultat comme une validation sur les images OoC ou comme
  une preuve biologique ;
- exiger un benchmark sur des données OoC pertinentes et un protocole de
  déploiement/licence explicite avant toute promotion en moteur scientifique de
  production.
