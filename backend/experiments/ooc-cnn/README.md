# Environnement CNN OoC isolé

Ce dossier décrit l'environnement expérimental CNN sans modifier les dépendances
de l'API. Les versions CPU correspondent à la pile déjà validée localement sur
Python 3.12, PyTorch 2.10 et torchvision 0.25.

## Utilisation locale

La création de l'environnement télécharge des paquets et doit donc être lancée
explicitement, uniquement lorsqu'elle est souhaitée :

```bash
conda env create --file backend/experiments/ooc-cnn/environment.cpu.yml
PYTHONPATH=backend conda run --name organchip-ooc-cnn-cpu \
  python -m pytest backend/tests/test_ooc_cnn_protocol.py
```

Les cibles Make utilisent ce même environnement par défaut :

```bash
CNN_RUN_ID=smoke-local-manual-v1 make cnn-smoke
```

Pour employer un autre environnement isolé compatible, passer explicitement
`CNN_PYTHON=/chemin/vers/python`. L'export reproductible est exposé par
`make cnn-export` et refuse de démarrer sans les chemins et SHA-256 explicites
du checkpoint et du rapport de sélection.

L'environnement CPU sert aux tests, au smoke run et à la vérification ONNX. Il
ne doit pas être utilisé pour annoncer un benchmark GPU.

### Environnement réellement utilisé par le smoke de référence

Le smoke `smoke-local-92bf217` n'a pas été exécuté dans l'environnement Conda
nommé `organchip-ooc-cnn-cpu`. La commande a explicitement utilisé le préfixe
local préexistant `data/cache/microsam-env/bin/python`. Avant le calcul, le
contrat runtime a validé les versions pertinentes de la pile CNN ; le rapport
et son artefact d'environnement ont également capturé le `pip freeze` complet
de ce préfixe. Cette trace décrit donc l'exécution réellement effectuée, y
compris les paquets supplémentaires présents dans ce préfixe.

Le fichier `environment.cpu.yml`, SHA-256
`958c6e91a96b77cdcf7bb3912b27bab02224457287a985fa01cf94aa673f7aa1`,
est la recette minimale versionnée pour reconstruire la pile CPU. Il ne prétend
pas être l'export exact du préfixe utilisé par le smoke. Un rerun dans
`organchip-ooc-cnn-cpu` doit recevoir un nouvel identifiant et produire un
rapport, un checkpoint et un export ONNX distincts ; il constituerait une
nouvelle preuve, pas une réécriture des artefacts `smoke-local-92bf217`.

Le smoke de référence du commit `92bf217fccb4784949411d2025a626bfbcea1015`
a parcouru huit images train et quatre images de validation pendant une époque,
avec la graine `20260916` et la vérification des hashes d'images. Il n'a jamais
ouvert le manifeste test et son rapport porte `benchmark_eligible: false`.
Les métriques obtenues sur quatre images, macro-F1 `0,333333` et ROC-AUC `0,5`,
valident seulement l'exécution de bout en bout.

Artefacts locaux de ce contrôle :

- checkpoint :
  `data/experiments/ooc-cnn/smoke-local-92bf217/best-checkpoint.pt`, SHA-256
  `eaf8ebdae4a73e706c2266294d6436dca17d904dd4a8da781dff49d663f79ec6` ;
- rapport de sélection :
  `data/experiments/ooc-cnn/smoke-local-92bf217/validation-report.json`, SHA-256
  `0626128ce599ac6580861744071de729e143e7e78876229a5cbc1a4ee14cae8e` ;
- modèle ONNX opset 18 :
  `data/experiments/ooc-cnn/smoke-local-92bf217/onnx/model.onnx`, SHA-256
  `57badbeae247c241797ebe4094deeb6b25e71a79ca76429a832b9f92e6adc1c9`.

Le rapport d'export associé porte le SHA-256
`575431d9119eca85a83c1c1c2162b2091b2af1e1ae32182494d2303c4baeca0f`.

La configuration porte le SHA-256
`4c01910c1df49fc8b9a129b32b890015086b21ce09d1830eabd24fbd82cffe59`
et le contrat runtime le SHA-256
`3e8d1d34fdd7e853037ef2e8c3435ea2ef769a9f6bd5fffee03fec6c08d241ea`.

La parité ONNX/PyTorch passe pour les lots dynamiques 1, 2 et 3 : erreur
absolue maximale `1,862645149230957e-09`, pour une tolérance `1e-4`.

## Utilisation sur Kaggle

### Sonde préalable, sans données

Avant de transférer les données ou de lancer l'entraînement, utiliser le notebook
autonome [ooc-runtime-probe-kaggle.ipynb](../../../notebooks/ooc-runtime-probe-kaggle.ipynb).
Il embarque le contrat actuel et un diagnostic reproductible, sans dépendre du
bundle source. Aucun poids n'est téléchargé, aucun dataset n'est lu, aucun
entraînement n'est lancé. Le modèle aléatoire généré est un artefact de test,
jamais un modèle à intégrer au produit.

La création/importation sur Kaggle nécessite une confirmation explicite juste
avant l'action externe. Réglages : GPU activé, Internet désactivé, aucune entrée
dataset. Exécuter toutes les cellules puis récupérer `runtime-report.json` dans
le sous-dossier `organchip-runtime-probe-*` des sorties. Ne pas publier le
notebook ou créer un dataset pour cette simple vérification.

Le rapport contient les versions, les incompatibilités avec le contrat, un
forward MobileNetV3 sur CUDA et une vérification ONNX/PyTorch CPU pour les lots
1, 2 et 3. Un succès des opérations ne lève pas une incompatibilité de version.
Un succès global ne remplace pas le préflight complet de l'entraînement.

La sonde reste exécutée pour diagnostic si le contrat refuse une version. Toute
extension des bornes devra ensuite être vérifiée dans la pile réelle ; le contrat
et les hashes de configuration ne sont pas modifiés automatiquement.

Reproduction locale, dans un environnement CNN existant :

```bash
/chemin/vers/python backend/scripts/probe_cnn_runtime.py \
  --contract backend/experiments/ooc-cnn/kaggle-runtime-contract.json \
  --output-directory /tmp
```

Sans CUDA, le contrôle GPU échoue normalement et `runtime_checks_passed` reste
faux, même si la parité ONNX passe. Ce n'est pas une mesure des versions Kaggle.
Le notebook versionné est généré par
`backend/scripts/build_runtime_probe_notebook.py` ; sa synchronisation fait
partie de `make check`.

Vérification locale du 16 septembre 2026 : le script puis toutes les cellules
Python du notebook ont été exécutés dans `data/cache/microsam-env/bin/python`
(Python 3.12.14, torch 2.10.0, torchvision 0.25.0). Les versions respectent le
contrat ; la parité ONNX passe pour les trois tailles de lot (écart maximal
`9.43689570931383e-16`, tolérance `1e-4`). Le contrôle CUDA échoue comme attendu
sur ce Mac. Cette exécution des cellules n'est ni un run du kernel Jupyter, ni
une exécution Kaggle. Les versions Kaggle restent à mesurer.

### Entraînement après validation de l'environnement

Activer un GPU puis joindre comme entrées locales le code source, les images,
les manifestes verrouillés et le fichier de poids initial. Le notebook doit
valider `kaggle-runtime-contract.json` avant tout calcul et enregistrer les
versions réellement présentes. Il ne doit exécuter ni `pip install`, ni
téléchargement réseau, ni `weights=DEFAULT`.

Le mode `validation` ne reçoit jamais le manifeste test. Le mode `final-eval`
reste soumis au manifeste gelé, aux hashes obligatoires, à la confirmation
explicite et à un reçu d'accès local au workspace. Tant que ce workspace et son
reçu sont conservés, toute seconde tentative est refusée. Ce verrou local ne
peut pas empêcher une relance depuis un workspace neuf ou après suppression du
reçu : l'unicité globale reste une règle de protocole et exige d'archiver le
reçu hors du workspace éphémère.

Kaggle monte les datasets joints sous `/kaggle/input` en lecture seule. Seul le
bundle source doit être copié sous, par exemple,
`/kaggle/working/organchip-ooc-cnn/organchip-insight`. Les 13 Go de données restent dans leur
dataset Kaggle séparé : passer sa racine au CLI avec `--image-root`. Cette
racine doit conserver le layout relatif déclaré, notamment
`data/raw/ooc/...`, afin que chaque chemin du manifeste se résolve sans copie.

Le chargeur refuse tout lien symbolique dont la cible sort de la racine
autorisée. Il ne faut donc pas relier `/kaggle/working` à `/kaggle/input` par
symlink ; `--image-root` fournit explicitement la racine read-only des images.

Pendant une validation, le moteur écrit atomiquement `last-checkpoint.pt` après
chaque époque terminée, en plus de `best-checkpoint.pt`. Le checkpoint de reprise
contient le modèle, AdamW, le scheduler, le scaler AMP, l'historique, l'état de
l'early stopping et les générateurs aléatoires. Une reprise utilise le même
`run-id` et `--resume-from <run>/last-checkpoint.pt`; elle est refusée si le
rapport final existe déjà ou si le code, la configuration, le manifeste, les
poids initiaux ou le meilleur checkpoint ont changé. Une interruption au milieu
d'une époque repart au début de cette époque ; une interruption après l'époque
10 repart à l'époque 11. La persistance des fichiers Kaggle doit rester active.

Chaque époque écrit aussi sur stderr une ligne immédiatement visible avec les
pertes train/validation, macro-F1, balanced accuracy, learning rate, meilleure
époque et compteur de patience. Les courbes Matplotlib et `history.csv` restent
les artefacts de référence produits à la fin.

La prochaine étape est une exécution `validation` complète sur GPU, avec les
poids locaux et leur SHA-256 explicite. Elle ne débloque pas automatiquement le
test : `final-eval` reste une opération distincte, destinée à n'être lancée
qu'une fois après gel de la sélection.

Lors de cette opération finale seulement, le manifeste test peut rester dans
un bundle read-only distinct. Les options `--test-manifest` et
`--test-manifest-root` conservent son chemin logique sous cette racine ; le CLI
écrit le reçu local avant de lire ou de hasher son contenu. Ce reçu doit être
exporté et conservé avec le rapport final pour rendre toute relance visible.
