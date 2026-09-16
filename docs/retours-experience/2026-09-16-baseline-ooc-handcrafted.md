# Baseline OoC handcrafted sur split groupé

Date : **16 septembre 2026**

Statut : **baseline reproductible terminée, résultat utile mais insuffisant**

## Question

Des caractéristiques visuelles déterministes, sans poids préentraînés ni
métadonnées expérimentales, permettent-elles de prédire le label expert
`good`/`bad` du dataset OoC sur des dates d'acquisition tenues à l'écart ?

La cible est exclusivement la qualité d'image annotée dans le dataset. Elle ne
mesure ni toxicité, ni efficacité d'un traitement, ni validité biologique, ni
diagnostic.

## Protocole reproductible

| Élément | Valeur |
|---|---|
| Code évalué | commit `5c5940409a1317f6adcf83fbbbee750bcf3c2f73` |
| Dataset | OOC Image Dataset, DOI `10.5281/zenodo.10203721`, CC-BY-4.0 |
| MD5 archive | `8f7e058996203d48eb03b2d86c0a2e4d` |
| Images | 3 072 : 1 727 `good`, 1 345 `bad` |
| Split | 2 137 train / 462 validation / 473 test |
| Groupes | 40 train / 10 validation / 9 test |
| Unité de groupe | préfixe `YYMMDD`, proxy conservateur de date d'acquisition |
| SHA-256 split | `5ffcf7ff0d69901f7362903d2532462c2758386dfbee2d6265b7a11d61b30d8c` |
| Entrées modèle | 50 caractéristiques d'image déterministes, vignette 256×256 |
| Poids externes | aucun |
| Graine | `20260916` |
| Bootstrap | 10 000 réplications par préfixe d'acquisition |

Commande :

```bash
make train-ooc-baseline
```

Le cache de caractéristiques vérifié a été réutilisé. Son SHA-256 est
`8ff227f79bc88ac0d3c680305e65fd3c8b66397afefb26d52883563e4583603b`.
Le rapport enregistre aussi les hashes du trainer, de l'extracteur, du modèle et
des prédictions.

## Sélection sans le test

Neuf candidats ont été ajustés sur le train et comparés sur la validation :
quatre régressions logistiques, trois Extra Trees et deux HistGradientBoosting.
Pour chaque candidat, le seuil a été choisi sur la validation par macro-F1, puis
balanced accuracy. Le meilleur candidat est :

```text
Extra Trees · 500 arbres · profondeur 8 · min_samples_leaf 2
seuil good = 0,505
```

Le test n'a participé ni au choix du modèle, ni au choix du seuil, ni au choix
des caractéristiques. Il avait déjà été évalué une première fois après la
sélection. La relance documentée ici régénère déterministiquement les artefacts
avec le code enfin versionné et corrige la sémantique des métriques mono-classe ;
elle ne crée aucune nouvelle décision à partir du test.

## Résultats principaux

| Mesure | Validation | Test groupé |
|---|---:|---:|
| Support | 462 | 473 |
| Accuracy | 0,777056 | 0,723044 |
| Balanced accuracy | 0,755174 | 0,693102 |
| Macro-F1 | 0,761214 | 0,692077 |
| ROC-AUC | 0,825165 | 0,802821 |
| Brier | 0,179678 | 0,194051 |

Intervalle bootstrap 95 % test par date :

| Mesure | Intervalle |
|---|---:|
| Accuracy | [0,644531 ; 0,825364] |
| Balanced accuracy | [0,565438 ; 0,748528] |
| Macro-F1 | [0,561284 ; 0,750882] |
| ROC-AUC | [0,589040 ; 0,875587] |

La matrice de confusion test, avec `bad=0` et `good=1`, est
`[[96, 109], [22, 246]]`. Le modèle prédit `good` pour 75,1 % des images alors
que le taux réel est 56,7 %. Il privilégie donc fortement le rappel des images
`good` et produit 109 faux positifs `good`.

## Tranches et erreurs

| Type cellulaire | Support bad/good | Macro-F1 | ROC-AUC |
|---|---:|---:|---:|
| A549 | 33 / 77 | 0,678730 | 0,912633 |
| CACO | 0 / 24 | non estimable | non estimable |
| HPMEC | 138 / 117 | 0,659472 | 0,766258 |
| HSAEC | 16 / 38 | 0,520993 | 0,358553 |
| HUVEC | 0 / 12 | non estimable | non estimable |
| NHBE | 18 / 0 | non estimable | non estimable |

| Jour | Support bad/good | Macro-F1 | ROC-AUC |
|---|---:|---:|---:|
| 0–1 | 18 / 105 | 0,505397 | 0,537566 |
| 2–3 | 83 / 25 | 0,614875 | 0,720482 |
| 4 | 34 / 19 | 0,543103 | 0,769350 |
| 4+ | 70 / 119 | 0,646355 | 0,732653 |

Les tranches mono-classe n'affichent plus de balanced accuracy, macro-F1 ou
ROC-AUC artificiellement parfaites. Les faibles résultats HSAEC et 0–1 jour,
ainsi que les 109 faux `good`, sont des signaux prioritaires pour la galerie
d'erreurs du futur CNN.

## Limites et risques de raccourci

1. Les neuf dates test donnent des intervalles très larges.
2. `YYMMDD` n'est pas un identifiant documenté de puce, puits, donneur ou
   expérience. Une même unité biologique suivie sur plusieurs dates peut encore
   traverser les splits.
3. Le dataset mélange modes `L`/`RGB` et plusieurs résolutions. Ces propriétés
   peuvent être corrélées au label et devenir des raccourcis pour un CNN.
4. L'écran de quasi-doublons a démontré le risque du split publié, mais un nouvel
   audit exhaustif de toutes les paires du split groupé reste à exécuter.
5. Les importances Extra Trees sont associatives et non causales.
6. Le résultat MobileNetV3 publié utilise un autre split, potentiellement
   contaminé par les préfixes d'acquisition ; aucune comparaison directe n'est
   valide.

## Décision

- conserver ce modèle comme baseline reproductible et explicable ;
- ne pas l'intégrer comme preuve de performance finale ;
- mesurer d'abord une baseline de raccourcis fondée uniquement sur
  mode/résolution ;
- construire ensuite un MobileNetV3 avec modes `smoke`, `validation` et
  `final-eval` séparés ;
- interdire tout accès au test en mode `smoke` ou `validation` ;
- n'autoriser `final-eval` qu'après gel du modèle, du seuil, du checkpoint et de
  leurs hashes ;
- rechercher une validation OoC externe avant toute revendication forte.

## Artefacts

- [rapport JSON](../../reports/benchmarks/ooc-handcrafted-image-quality-v1.json) ;
- [prédictions test](../../reports/predictions/ooc-handcrafted-image-quality-v1-test.csv) ;
- [split groupé](../../data/splits/ooc-grouped-v1.csv) ;
- modèle local ignoré par Git :
  `data/models/ooc-handcrafted-image-quality-v1.joblib`, SHA-256
  `766b1aad11da82902d0fda3ac06794b268950a42648591b62a7cd18777411757`.

Le modèle devra être joint à une release ou reconstruit depuis le code et les
données avant la soumission publique.
