# Comparateurs de classification — campagne v2

Date : **16 septembre 2026**

Statut : **comparaison train/validation terminée ; test final non ouvert**
(addendum du 17 septembre 2026 en fin de document)

## Question

Le CNN MobileNetV3-Small apporte-t-il, sur le même split campagne v2, un signal
supérieur à une majorité, au raccourci d'acquisition mode + résolution et à la
baseline visuelle handcrafted ?

## Protocole

- entraînement sur les 2 056 lignes `train` du manifeste v2 ;
- évaluation et sélection des seuils sur ses 509 lignes `validation` ;
- aucun chargement du manifeste test (`test_manifest_opened: false`) ;
- extraction fraîche des 50 caractéristiques sur le seul manifeste autorisé,
  sans réutiliser le cache v1 qui contenait d'autres partitions ;
- mêmes neuf candidats handcrafted que pour la campagne v1 ;
- raccourci mode + résolution ajusté uniquement sur train, avec lissage de
  Laplace ;
- seuil fixe `0,5` conservé dans le rapport et seuil sélectionné sur validation
  ajouté pour comparer honnêtement des sorties probabilistes.

Le seuil et le candidat handcrafted sont choisis sur la validation : ces scores
sont des métriques de décision, pas une estimation indépendante de
généralisation.

## Résultats globaux

| Comparateur | Seuil | Macro-F1 | Balanced accuracy | ROC-AUC |
| --- | ---: | ---: | ---: | ---: |
| Majorité `good` | 0,500 | 0,3565 | 0,5000 | 0,5000 |
| Mode + résolution | 0,505 | 0,7260 | 0,7249 | 0,7249 |
| Handcrafted, régression logistique C=0,01 | 0,460 | 0,6876 | 0,6867 | 0,7074 |
| CNN MobileNetV3-Small actuel | 0,420 | **0,7627** | **0,7619** | **0,7996** |

Le raccourci au seuil fixe `0,5` prédit toutes les images `good`, car la
probabilité train lissée de la catégorie L est `0,504447`. Sa ROC-AUC reste
`0,724873`, ce qui révèle le signal de mode malgré ce seuil dégénéré. Le seuil
sélectionné `0,505` sépare alors L et RGB et donne la comparaison pertinente
ci-dessus.

## Tranches par mode

| Modèle | Balanced accuracy L | Balanced accuracy RGB |
| --- | ---: | ---: |
| Majorité | 0,5000 | 0,5000 |
| Mode + résolution | 0,5000 | 0,5000 |
| Handcrafted | 0,6584 | 0,5609 |
| CNN actuel | **0,7729** | **0,6315** |

Le raccourci n'a aucune discrimination à mode constant : il prédit toute la
tranche L `bad` et toute la tranche RGB `good`. Le CNN dépasse donc réellement
le raccourci au sein de chaque mode sur cette validation. Il dépasse également
le handcrafted de `0,1145` point de balanced accuracy sur L et de `0,0706` sur
RGB.

## Décision

Le CNN actuel est le meilleur **candidat de validation** parmi les méthodes
évaluées sur v2. Il ne doit pas encore être appelé modèle final ou modèle
produit :

- le gain global sur le raccourci est de `+0,0367` en macro-F1, `+0,0371` en
  balanced accuracy et `+0,0748` en ROC-AUC ;
- la tranche L fournit un signal convaincant sur cette validation ;
- la tranche RGB reste sous le plancher pré-enregistré de `0,65` en balanced
  accuracy, à `0,6315` ;
- les seuils et candidats ont été sélectionnés sur cette même validation ;
- l'indépendance biologique complète n'est pas établie par le manifeste.

La prochaine décision est donc inchangée : exécuter l'ablation A (gris, 224 px)
et l'ablation B (gris, 448 px). Le run C n'est autorisé que si A ou B améliore la
balanced accuracy RGB d'au moins `0,02`. Aucun accès test avant ce gel.

## Artefacts et provenance

| Élément | Valeur |
| --- | --- |
| Commit d'exécution | `56676332c8481d6d8f26de81e77a40ec6c58993f` |
| Manifeste train/validation | `b191947b892bfa7e9442aca0051c3b2246343a289715073fd17eefabcf8ea4a3` |
| Rapport JSON | `reports/benchmarks/ooc-classification-comparators-campaign-v2.json` |
| SHA-256 du rapport | `39f8ba31a61d52d2d54972153d1b390e0da76b0fca7b5084c5942c2c82f0becd` |
| Prédictions validation | `reports/predictions/ooc-classification-comparators-campaign-v2-validation.csv` |
| SHA-256 des prédictions | `01d267ccaaa0da86c8edc5cf8a157bc955a42a9a5b1258790dccb3717f4fbf2d` |
| Cache de caractéristiques local | `6be6567b976560f349fff95c753bb837379ce21b6ab3150c413111d00a72daee` |
| Modèle handcrafted local | `a9c23560aefaeb278cd4c81980c279c578abb516538cb9b461a2d2a800b8613c` |

Le cache et le modèle restent dans des chemins ignorés par Git. Le rapport et
les 509 prédictions sont versionnés afin de rendre chaque chiffre auditable.

## Addendum du 17 septembre 2026 — comparateur de métadonnées manquant

- « Le CNN dépasse réellement le raccourci au sein de chaque mode » : le
  raccourci mode + résolution vaut `0,5000` de balanced accuracy par mode par
  construction ; le dépasser n'établit rien à mode constant.
- « La tranche L fournit un signal convaincant » : la tranche L ne compte que
  deux dates d'acquisition ; en analyse post hoc, un comparateur mode ×
  bucket de jour appris sur le seul train (lissage de Laplace, seuil 0,5)
  atteint `0,8171` sur L, `0,6533` sur RGB et `0,7920` globalement, au-dessus
  du CNN de référence (`0,7729`, `0,6315`, `0,7619`). Ce comparateur n'est
  pas versionné dans le rapport ; il doit y être ajouté avant toute reprise.
- Les écarts avec le handcrafted (`0,1145` sur L, `0,0706` sur RGB) sont des
  points sans intervalle : L ne permet aucun bootstrap groupé informatif.
- A et B ont été exécutés ; aucun n'améliore la balanced accuracy RGB
  (`0,5948`, `0,6079` contre `0,6315`), C n'a pas été lancé, aucune
  configuration n'est éligible, le test n'a jamais été ouvert. Voir le
  [contre-audit](../02-research/audits/audit-2026-09-17-classification-cnn.md).

### Mise en œuvre de l'addendum — 17 septembre 2026

Le commit `438a555932fa9dd89fc7cd221794a468779392ef` ajoute au comparateur
reproductible les tables catégorielles mode × bucket de jour et mode × type
cellulaire. Elles sont ajustées sur `train` uniquement, avec lissage de Laplace
`alpha=1`, puis évaluées au seuil fixe `0,5`. Aucune catégorie de validation
n'est absente du train et aucun seuil n'est choisi sur ces résultats.

| Comparateur | Macro-F1 | Balanced accuracy | ROC-AUC | BA L | BA RGB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mode × bucket de jour | 0,7971 | 0,7920 | 0,8442 | 0,8171 | 0,6533 |
| Mode × type cellulaire | 0,7272 | 0,7251 | 0,6975 | 0,6358 | 0,5000 |

Le premier comparateur dépasse numériquement les CNN de référence et B sur la
balanced accuracy globale de cette validation. Cette observation confirme que
le bucket de jour et le mode portent un raccourci majeur ; elle ne constitue pas
une estimation indépendante de généralisation. Le type cellulaire seul, même
conditionné par le mode, n'explique pas le résultat RGB.

Les 509 prédictions contiennent désormais les probabilités des deux
comparateurs. Le rapport régénéré référence le commit d'exécution ci-dessus :

| Élément régénéré | SHA-256 |
| --- | --- |
| Rapport JSON | `4f1bdc729256bddf4824725397aba8b7b790f78c88d83d451f31f2f50346c42c` |
| Prédictions validation | `2442f271ab4a9a5d157d80124dc78047186d1c41b823409d9b549e1c67388968` |

Les empreintes antérieures restent dans la section historique ci-dessus afin de
ne pas réécrire silencieusement le premier résultat.
