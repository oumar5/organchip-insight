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

La prochaine étape est une exécution `validation` complète sur GPU, avec les
poids locaux et leur SHA-256 explicite. Elle ne débloque pas automatiquement le
test : `final-eval` reste une opération distincte, destinée à n'être lancée
qu'une fois après gel de la sélection.

Lors de cette opération finale seulement, le manifeste test peut rester dans
un bundle read-only distinct. Les options `--test-manifest` et
`--test-manifest-root` conservent son chemin logique sous cette racine ; le CLI
écrit le reçu local avant de lire ou de hasher son contenu. Ce reçu doit être
exporté et conservé avec le rapport final pour rendre toute relance visible.
