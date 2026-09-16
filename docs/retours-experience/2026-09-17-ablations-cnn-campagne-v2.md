# Ablations CNN A/B — campagne v2

État au 17 septembre 2026. Les runs utilisent uniquement le manifeste
train/validation v2. Le dataset de test gelé n'est pas attaché et le rapport A
confirme `test_manifest_opened: false`.

## Plomberie Kaggle

Les versions 1 et 2 des kernels A/B ont échoué avant l'entraînement. La version
1 supposait un ancien chemin absolu Kaggle. La version 2 détectait le point de
montage, mais pas le dossier supplémentaire portant le slug dans le bundle
source v6. Les commits `79d34c8` puis `cdce4a4` rendent la résolution compatible
avec les deux points de montage et les deux structures internes. Ces échecs
n'ont produit aucune métrique et ne participent pas à la sélection.

Entrées communes aux versions 3 :

- bundle source privé v6, SHA-256 logique
  `2b431a49757aa39cb40043c20a3733e861cdfaf40d8027a852016b4f6c1b3c88` ;
- commit source embarqué
  `b855c5fff7d3851ab0df1a0db365db09f7e3273b` ;
- split v2 verrouillé, seed `20260916` ;
- GPU Kaggle T4, Internet désactivé ;
- aucun dataset test attaché.

## Run A — niveaux de gris, 224 px

Kernel privé : `oumarbenlol/organchip-cnn-ablation-a-grayscale-224`, version 3.
Le run est terminé et son archive a été récupérée localement.

| Mesure | Résultat |
| --- | ---: |
| Meilleure époque | 2 |
| Époques exécutées | 8 / 20, arrêt anticipé patience 6 |
| Seuil choisi sur validation | 0,575 |
| Macro-F1 globale | 0,6576 |
| Balanced accuracy globale | 0,6704 |
| ROC-AUC globale | 0,7176 |
| Balanced accuracy L | 0,7389 |
| ROC-AUC L | 0,7529 |
| Balanced accuracy RGB | 0,5948 |
| ROC-AUC RGB | 0,5848 |

Le passage en niveaux de gris à 224 px dégrade le résultat de référence couleur
sur toutes les métriques déterminantes. La balanced accuracy RGB recule de
`0,6315` à `0,5948`. Le run A ne satisfait donc ni le plancher d'éligibilité de
`0,65` par mode, ni la condition d'amélioration RGB de `+0,02` autorisant à lui
seul le run C.

Le modèle surapprend rapidement : la meilleure époque est 2, puis la perte de
validation passe de `0,6624` à `1,2328` à l'époque 8 malgré la baisse continue de
la perte d'entraînement. Entraîner plus longtemps n'est pas justifié.

## Vérification des artefacts A

- ZIP : `kaggle-validation-campaign-v2-gray224-artifacts.zip` ;
- SHA-256 du ZIP :
  `a4142c8c8da0ba0d03827d83639f3f2a8fb7eaee6b6338e752ccf33df3003dda` ;
- 14 fichiers déclarés : tous les SHA-256 internes sont conformes ;
- rapport de validation SHA-256 :
  `80c2c182f2ec7acc13572023c06b580ae5a94c6e67e4bc0bc8ab4f493e567e49` ;
- checkpoint sélectionné SHA-256 :
  `4414e63d556f3f6ad89b4b106d00919e60aedc5cbdf98149d84f133a12af8b9a` ;
- modèle ONNX SHA-256 :
  `accb89d074ad87251d4a93ebcc195492bb44adcdb252467589c3a7bf2e398b27` ;
- parité ONNX réussie sur 6 échantillons, erreur absolue maximale
  `9,93e-7` pour une tolérance de `1e-4`.

L'archive et son contenu extrait sont conservés sous
`data/experiments/ooc-cnn/`, dossier ignoré par Git.

## État de la décision

Le run B gris 448 px reste en cours. La décision de lancer ou non C sera prise
uniquement après validation de B. C restera interdit si la balanced accuracy RGB
de B est inférieure à `0,651515`.

