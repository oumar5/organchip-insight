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

## Utilisation sur Kaggle

Activer un GPU puis joindre comme entrées locales le code source, les images,
les manifestes verrouillés et le fichier de poids initial. Le notebook doit
valider `kaggle-runtime-contract.json` avant tout calcul et enregistrer les
versions réellement présentes. Il ne doit exécuter ni `pip install`, ni
téléchargement réseau, ni `weights=DEFAULT`.

Le mode `validation` ne reçoit jamais le manifeste test. Le mode `final-eval`
reste soumis au manifeste gelé, aux hashes obligatoires, à la confirmation
explicite et au reçu d'accès chaîné du protocole CNN.
