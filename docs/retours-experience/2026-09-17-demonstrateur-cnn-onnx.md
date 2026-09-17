# Démonstrateur CNN ONNX abstentionniste

Date : **17 septembre 2026**

Statut : **intégré et testé localement ; poids non distribués ; test gelé non ouvert**

## Question

Le run B peut-il être présenté dans le produit sans transformer un résultat de
validation insuffisant en décision automatique de qualité ?

## Décision produit

Oui, uniquement comme démonstrateur expérimental :

- chaque image reste systématiquement `À vérifier` ;
- aucune classe `good` ou `bad` n'est attribuée ;
- la valeur affichée est le softmax brut de la classe positive `good`, explicitement
  marqué **non calibré** ;
- le mode d'acquisition source est affiché ;
- seules les images dont le mode PIL source est exactement `L` ou `RGB` sont
  évaluées ; les autres sont marquées hors domaine et ne reçoivent aucun score ;
- aucun overlay, comptage ou masque n'est rattaché à ce moteur ;
- la segmentation adaptative reste le moteur produit par défaut.

Cette intégration ne change pas la conclusion scientifique : sur la validation,
aucun signal de qualité robuste et indépendant des métadonnées d'acquisition et
de culture n'est démontré.

## Contrat technique

Le commit `a96284a` ajoute :

- un registre séparant `status` (maturité) et `runnable` (disponibilité réelle) ;
- un chargement ONNX CPU sans réseau et à fermeture sûre ;
- la vérification préalable des trois empreintes du bundle ;
- un résultat discriminé `quality-classification`, distinct de la segmentation ;
- la provenance complète dans l'API et l'interface ;
- une dépendance optionnelle `inference` et son installation dans l'image backend ;
- des tests du prétraitement, de l'abstention, du domaine, des hashes et du contrat API.

Le moteur n'est exécutable que si ONNX Runtime et le bundle complet sont présents.
Sinon, il reste visible dans le catalogue avec une cause d'indisponibilité ; le
bouton d'analyse ne le propose pas.

## Bundle autorisé

| Artefact | SHA-256 |
|---|---|
| `model.onnx` | `c2f7339255a5e525f659d94a47aa8eb02d1ef60ed832597b343b542a4ed694a2` |
| `preprocessing.json` | `fe8e18d8bc76a0ed06a884ec5ff9936fe6a0e59b1dbc44abaf7c027e61d0c3bc` |
| `labels.json` | `89e2fa4c560898d5c72c8efc80beb1b0d016b3e8d3dce7bdc7b30a23ce4b03cd` |

Les poids restent ignorés par Git. Leur publication et leur licence sont une
décision réservée ; l'intégration ne les ajoute ni au dépôt ni à l'image Docker.

## Smoke test réel

Environnement local : macOS Intel, Python 3.13, ONNX Runtime CPU `1.23.2`.
Le bundle a été chargé après vérification des hashes. Deux images du seul
manifeste train/validation campagne v2 ont été évaluées :

| Image | Mode source | Softmax brut `good` | Interprétation produit |
|---|---|---:|---|
| `230517_47.png` | L | 0,222390 | À vérifier |
| `220606_5.png` | RGB | 0,714799 | À vérifier |

Ces deux valeurs sont des témoins d'exécution, pas une mesure de performance et
pas une classification. Aucun artefact visuel n'a été créé. Le manifeste test
n'a pas été lu par ce smoke test.

## Validation logicielle

Après l'intégration :

- Ruff : réussi ;
- backend : **163 tests réussis, 1 ignoré** ;
- typecheck frontend : réussi ;
- build Vite : réussi ;
- notebooks : synchronisés ;
- rendu Docker Compose : valide.

Commande : `make check`.

Le parcours navigateur local a ensuite été exécuté de bout en bout : création
d'une expérience, sélection du moteur CNN expérimental, import de
`230517_47.png`, inférence puis lecture du résultat. L'interface affiche le mode
source `L`, le softmax brut arrondi `0,22`, le badge `À vérifier`, les trois
hashes et les avertissements. Elle n'affiche ni classe, ni overlay, ni comptage.
Toutes les requêtes utiles ont répondu en HTTP 2xx et la console navigateur ne
contenait aucune erreur ni alerte.

## Limites restantes

- l'historique SQLite conserve encore un seul résultat courant par expérience ;
- les poids ne sont pas encore distribués dans une release ou un modèle Kaggle ;
- le parcours Docker avec bundle monté doit être rejoué sur machine propre ;
- les sorties ne doivent pas être utilisées pour sélectionner un nouveau modèle,
  rouvrir le test ou définir un seuil post hoc.
