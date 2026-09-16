# Protocole de décision — classification campagne v2

Pré-enregistrement du 16 septembre 2026. Le manifeste test reste absent de tout
run décrit ici. Une expérience n'est lancée que si son résultat change une
décision listée ci-dessous.

## État de référence

Le MobileNetV3-Small affiné sur image entière à 224 px atteint sur la validation
v2 une macro-F1 de `0,7627`, une balanced accuracy de `0,7619` et une ROC-AUC de
`0,7996` au seuil sélectionné `0,42`. Il n'est pas déclaré « meilleur modèle » :
aucun comparateur n'a encore été recalculé sur ce même split.

Les tranches déterminantes sont :

| Mode | Bad / good | Balanced accuracy | ROC-AUC |
| --- | ---: | ---: | ---: |
| L, 2056×1542 | 152 / 62 | 0,7729 | 0,8521 |
| RGB, 2048×1536 | 75 / 220 | 0,6315 | 0,6309 |

Le résultat L montre un signal au-delà de la seule catégorie globale
mode/résolution. Il ne prouve pas encore un signal biologique indépendant : des
campagnes, lignées ou conditions corrélées peuvent subsister à l'intérieur de
la tranche. La tranche RGB est trop faible pour une revendication produit.

## Étape 1 — comparateurs CPU sur v2

Recalculer, sur train/validation v2 uniquement :

1. prédiction majoritaire apprise sur train ;
2. raccourci catégoriel mode + résolution appris sur train ;
3. baseline handcrafted avec les mêmes candidats que v1.

Chaque rapport doit fournir les métriques globales aux seuils fixe et
sélectionné, puis les tranches L/RGB. Cette étape décide si le CNN apporte une
information au-delà des métadonnées d'acquisition. Les scores v1 restent du
contexte et ne sont jamais comparés numériquement au CNN v2.

Statut : **terminé** au commit `5667633`. Au seuil sélectionné sur validation,
le raccourci mode+résolution atteint une macro-F1 de `0,7260`, une balanced
accuracy de `0,7249` et une ROC-AUC de `0,7249`. Le handcrafted sélectionné
atteint respectivement `0,6876`, `0,6867` et `0,7074`. Le CNN les dépasse sur la
même validation (`0,7627`, `0,7619`, `0,7996`) et dépasse aussi leur balanced
accuracy dans chaque mode. Cette comparaison autorise les ablations, mais elle
ne remplace pas le test final et ne rend pas le CNN actuel éligible : sa tranche
RGB reste à `0,6315`, sous le plancher pré-enregistré de `0,65`.

## Étape 2 — ablations GPU bornées

Paramètres communs : split v2 inchangé, poids initiaux identiques, seed
`20260916`, backbone entièrement entraînable, maximum 20 époques, patience 6,
sélection du checkpoint sur macro-F1 à seuil 0,5, puis sélection du seuil sur
validation. Aucun balayage d'hyperparamètres.

| Run | Changement unique | Décision |
| --- | --- | --- |
| A | conversion déterministe en niveaux de gris, 224 px | mesure l'apport réel de la chroma |
| B | niveaux de gris, 448 px | teste si le signal de qualité est haute fréquence |
| C | recadrage centré commun 2048×1536, gris, 448 px | teste le marqueur de dimensions ; seulement si A ou B améliore la balanced accuracy RGB d'au moins 0,02 |

Une configuration est éligible au gel si sa balanced accuracy est au moins
`0,65` dans **chaque** mode. Parmi les configurations éligibles, la macro-F1
globale de validation décide ; en cas d'égalité à `0,005`, retenir le modèle le
plus petit et le moins coûteux. Si aucune n'est éligible, conserver le modèle
actuel comme résultat scientifique, mais ne pas présenter le CNN comme contrôle
qualité fiable pour RGB.

Statut au 17 septembre 2026 : **A et B terminés, C non autorisé**. A atteint une
balanced accuracy RGB de `0,5948` et B `0,6079`, toutes deux sous la référence
`0,6315` et sous le seuil conditionnel `0,651515`. Aucune configuration n'est
éligible au gel produit ; le test reste fermé. Les rapports et hashes sont
consignés dans le
[retour d'expérience A/B](retours-experience/2026-09-17-ablations-cnn-campagne-v2.md).

## Expériences conditionnelles, non lancées maintenant

- MobileNetV3 par tuiles à résolution native : à envisager si B améliore RGB,
  car cela confirmerait un signal local perdu par la réduction globale.
- DINOv2 ViT-S/14 gelé avec sonde linéaire : second avis seulement après
  préparation de poids hors ligne, licence et protocole identiques.
- LoRA, backbone plus gros ou autre architecture : uniquement si la sonde gelée
  justifie cette complexité.

## Étape 3 — gel et test

Une seule configuration est gelée avec ses hashes, son seuil, son commit et son
bundle source. Le test n'est attaché qu'ensuite, une seule fois. Le reçu d'accès
est copié dans le dossier du run final et inclus dans son archive avant arrêt du
workspace. Aucun résultat test ne peut rouvrir le choix du modèle.
