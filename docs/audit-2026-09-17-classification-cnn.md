# Contre-audit de la classification CNN — 17 septembre 2026

Contre-audit indépendant du bloc d'ablations A/B (commits `b855c5f` à
`eccac14`), relu par une seconde revue indépendante puis reproduit par des
implémentations séparées. Toutes les analyses de cette page sont **post hoc**
et **hors protocole** : elles n'ont produit aucun run, n'ont jamais ouvert le
test gelé, et ne modifient aucun verdict d'éligibilité. Seuls les chiffres
issus des rapports versionnés ou reproductibles par script sont retenus.

## Faits vérifiés

- Hashes des ZIP, rapports, checkpoints et modèles ONNX de A et B conformes
  aux REX ; 14 empreintes internes exactes par archive ; `test_manifest_opened:
  false` et `test_used_for_selection: false` dans chaque rapport.
- Protocole pré-enregistré à 23 h 18 (`acc92e9`), avant le code des ablations
  (23 h 44) et leurs résultats (00 h 34) ; `eccac14` n'ajoute qu'un statut.
- Configurations A et B : un seul champ modifié chacune par rapport à la
  référence (`color_mode`, puis `input_size`).
- Composition de la validation v2 : la tranche L compte **deux dates**
  (230419 : 124 images, 6,45 % `good` ; 230517 : 90 images, 60 % `good`) ; la
  tranche RGB compte dix dates, dont trois monoclasses.

| Run | Seuil | BA globale | AUC globale | BA L | AUC L | BA RGB | AUC RGB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Référence couleur 224 | 0,42 | 0,7619 | 0,7996 | 0,7729 | 0,8521 | 0,6315 | 0,6309 |
| A gris 224 | 0,575 | 0,6704 | 0,7176 | 0,7389 | 0,7529 | 0,5948 | 0,5848 |
| B gris 448 | 0,49 | 0,7750 | 0,8414 | 0,8338 | 0,8551 | 0,6079 | 0,6985 |

## Corrections acceptées après la revue croisée

1. **Intervalles bootstrap.** Les différences B − référence par bootstrap
   groupé (préfixe d'acquisition restreint à la tranche, graine `20260916`,
   2 000 tirages, mêmes indices pour les deux runs, percentiles 2,5/97,5)
   sont : BA RGB `[-0,1177 ; 0,0278]`, AUC RGB `[-0,0874 ; 0,1567]`, BA L
   `[-0,0539 ; 0,0609]`. Reproduites à la quatrième décimale par deux
   implémentations, dont une fondée sur `bootstrap_metrics_by_group`. Les
   intervalles d'AUC annoncés précédemment provenaient d'un rééchantillonnage
   par image. Précision nouvelle : avec deux dates, l'intervalle L n'a que
   trois points de support (chaque date seule, ou les deux) ; ses bornes sont
   un minimum et un maximum, pas un intervalle à 95 %, et ne doivent pas être
   citées comme tel.
2. **Seuil RGB « optimal ».** Sur la tranche RGB de B : 0,49 → BA 0,6079 ;
   0,53 (sélecteur officiel, macro-F1) → 0,6385 ; 0,635 (grille, BA
   maximale) → 0,6527 ; 0,65 → 0,6503 ; optimum exact 0,6550 sur un intervalle
   de seuil large de 0,00002, entre une image `bad` et une image `good`. La
   courbe est bimodale (plateaux 0,635–0,66 et 0,825–0,85), ce qui explique
   l'instabilité des seuils. Aucune de ces valeurs n'est un point de
   fonctionnement.
3. **Leave-one-date-out sur RGB.** Avec sélection du seuil par balanced
   accuracy sur les neuf autres dates : BA groupée 0,6312, intervalle
   `[0,5108 ; 0,7344]`, seuils 0,635–0,89. Avec le sélecteur officiel du dépôt
   (macro-F1) : 0,6089, `[0,5332 ; 0,6675]`, seuils 0,525–0,645. En
   resélectionnant le seuil à l'intérieur de chaque tirage, les intervalles
   s'élargissent à `[0,4587 ; 0,7222]` et `[0,4728 ; 0,6758]`. En split-half
   par date, 92 % des moitiés passent le plancher 0,65 en échantillon, 7,6 %
   seulement hors échantillon.

## Points méthodologiques

- La balanced accuracy est invariante à la prévalence : répliquer les images
  `bad` ×3 ou ×7 laisse la BA RGB à 0,6079. La formulation « pénalise
  mécaniquement RGB » était fausse. En revanche, seuls 0,045 des 0,226 points
  d'écart L − RGB sont récupérables par un seuil ; 0,186 sont un déficit de
  discrimination.
- La BA **globale** est gonflée par la composition mode × classe : 0,7750
  pour B contre 0,7029 en moyenne pondérée des modes ; la règle « RGB → good,
  L → bad » sans regarder l'image obtient 0,7249. La règle actuelle de seuil
  par macro-F1 groupée dépend de cette composition (0,49 devient 0,635 si les
  classes sont équilibrées à l'intérieur de chaque mode).
- Aucun changement de seuil ou de critère décidé après consultation de la
  validation ne peut restaurer une éligibilité, même consigné par amendement
  daté : l'amendement donne la transparence, pas le statut confirmatoire.

## Comparateurs de métadonnées, appris sur le seul train (post hoc)

Table de contingence mode × bucket de jour, lissage de Laplace, ajustée sur
les 2 056 images train, évaluée sur la validation au seuil 0,5 :

| Comparateur | BA L | AUC L | BA RGB | AUC RGB | BA globale |
|---|---:|---:|---:|---:|---:|
| mode × bucket de jour | 0,8171 | 0,8171 | 0,6533 | 0,7068 | 0,7920 |
| mode × lignée | 0,6358 | 0,6228 | 0,5080 | 0,4734 | 0,7251 |
| B (CNN) | 0,8338 | 0,8551 | 0,6079 | 0,6985 | 0,7750 |

Ce comparateur n'est pas dans le rapport versionné des comparateurs ; il
doit y être ajouté avant toute reprise de modélisation.

## Test adversarial de la conclusion

Après conditionnement sur les métadonnées les plus fines disponibles
(date × bucket de jour × lignée), le score de B conserve en RGB une
discrimination résiduelle modeste : AUC intra-strate pondérée 0,6430 sur
731 paires, permutation bilatérale p = 0,0215, intervalle par date
`[0,5892 ; 0,8189]`, plage leave-one-date-out 0,6244–0,7091. Ce résidu est
absent pour A (0,5116) et pour la référence (0,5458). Aucun proxy trivial
(netteté laplacienne, énergie de gradient, intensité, taille de fichier,
ordre d'acquisition) ne l'explique. En L, le résidu provient d'une seule
date (230517) et l'ordre d'acquisition révèle une structure en blocs non
enregistrée dans les métadonnées. Toutes ces mesures sont en échantillon,
sur le run sélectionné parmi trois, sans correction de tests multiples.

**Formulation retenue :** sur cette validation, aucun signal de qualité
robuste et indépendant des métadonnées d'acquisition et de culture n'est
démontré ; le résidu observé en RGB pour le run B est modeste, mesuré en
échantillon et non distinguable d'un effet de sélection du run. Il ne
justifie ni une revendication produit, ni un run supplémentaire.

## Décision

- modélisation CNN **close** ; aucune configuration éligible ; test gelé
  jamais ouvert et non ouvert pour cette modélisation ;
- B intégrable uniquement comme démonstrateur ONNX expérimental :
  abstention systématique « À vérifier », softmax présenté comme non
  calibré, mode d'acquisition et provenance affichés, aucune décision
  automatique `good`/`bad`, aucun overlay ni comptage rattaché ;
- pour tout protocole futur : règle de seuil invariante à la prévalence
  (seuil par mode ou maximin des BA par mode) pré-enregistrée avant toute
  prédiction de validation ; au moins cinq dates par mode en validation ;
  comparateurs de métadonnées versionnés **avant** le premier run ;
  identifiants de puce et de puits enregistrés à l'acquisition ;
- candidature Tool & Platform : crédible et différenciante par la
  plateforme traçable et l'audit scientifique ; aucune probabilité de
  finale ne peut être avancée sérieusement.

## Reproduction

Scripts et sorties de ce contre-audit conservés hors dépôt dans l'espace de
travail de session ; les entrées sont les fichiers `validation-predictions.csv`
des trois runs (archives ZIP dont les SHA-256 figurent dans les REX), le
manifeste `data/splits/ooc-campaign-v2-train-validation.csv` et l'inventaire
`reports/ooc-image-inventory-2026-09-16.csv`. Les comparateurs de métadonnées
et le bootstrap apparié doivent être versionnés dans
`backend/training/` pour devenir des résultats du projet.
