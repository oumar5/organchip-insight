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

L'environnement CPU sert aux tests, au smoke run et à la vérification ONNX. Il
ne doit pas être utilisé pour annoncer un benchmark GPU.

Le smoke de référence du commit `d39e5019632eec96d3f48c99c47c16558087d4cc`
a parcouru huit images train et quatre images de validation pendant une époque,
avec la graine `20260916` et la vérification des hashes d'images. Il n'a jamais
ouvert le manifeste test et son rapport porte `benchmark_eligible: false`.
Les métriques obtenues sur quatre images, macro-F1 `0,333333` et ROC-AUC `0,5`,
valident seulement l'exécution de bout en bout.

Artefacts locaux de ce contrôle :

- checkpoint :
  `data/experiments/ooc-cnn/smoke-local-d39e501/best-checkpoint.pt`, SHA-256
  `45b058b91f772e8baeafd06da5e5b6618b2b1831e89dab4484ab4717974d653f` ;
- rapport de sélection :
  `data/experiments/ooc-cnn/smoke-local-d39e501/validation-report.json`, SHA-256
  `9607e7a9a1cd87a183ad81357f9bf671bbef36e17e86af8f629540c7ec34e4fe` ;
- modèle ONNX opset 18 :
  `data/experiments/ooc-cnn/smoke-local-d39e501/onnx/model.onnx`, SHA-256
  `57badbeae247c241797ebe4094deeb6b25e71a79ca76429a832b9f92e6adc1c9`.

La parité ONNX/PyTorch passe pour les lots dynamiques 1, 2 et 3 : erreur
absolue maximale `1,862645149230957e-09`, pour une tolérance `1e-4`.

## Utilisation sur Kaggle

Activer un GPU puis joindre comme entrées locales le code source, les images,
les manifestes verrouillés et le fichier de poids initial. Le notebook doit
valider `kaggle-runtime-contract.json` avant tout calcul et enregistrer les
versions réellement présentes. Il ne doit exécuter ni `pip install`, ni
téléchargement réseau, ni `weights=DEFAULT`.

Le mode `validation` ne reçoit jamais le manifeste test. Le mode `final-eval`
reste soumis au manifeste gelé, aux hashes obligatoires, à la confirmation
explicite et au reçu d'accès unique du protocole CNN.

Kaggle monte les datasets joints sous `/kaggle/input` en lecture seule. Seul le
bundle source doit être copié sous, par exemple,
`/kaggle/working/organchip-insight`. Les 13 Go de données restent dans leur
dataset Kaggle séparé : passer sa racine au CLI avec `--image-root`. Cette
racine doit conserver le layout relatif déclaré, notamment
`data/raw/ooc/...`, afin que chaque chemin du manifeste se résolve sans copie.

Le chargeur refuse tout lien symbolique dont la cible sort de la racine
autorisée. Il ne faut donc pas relier `/kaggle/working` à `/kaggle/input` par
symlink ; `--image-root` fournit explicitement la racine read-only des images.

La prochaine étape est une exécution `validation` complète sur GPU, avec les
poids locaux et leur SHA-256 explicite. Elle ne débloque pas automatiquement le
test : `final-eval` reste une opération distincte et unique après gel de la
sélection.

Lors de cette opération finale seulement, le manifeste test peut rester dans
un bundle read-only distinct. Les options `--test-manifest` et
`--test-manifest-root` conservent son chemin logique sous cette racine ; le CLI
écrit le reçu unique avant de lire ou de hasher son contenu.
