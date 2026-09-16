# Données reproductibles

Les données brutes sont téléchargées localement dans `data/raw/` et ne sont
jamais suivies par Git. Le manifeste versionné `manifests/datasets.json` fixe
les URL, versions, tailles, checksums et licences.

## Acquisition minimale

```bash
make data-fetch
make data-audit
```

Cette commande télécharge seulement :

- le tableur OoC v1 (119 712 octets, CC-BY-4.0) ;
- BBBC019v2 Microfluidics (10 746 718 octets, CC-BY-3.0).

L'archive d'images OoC de 6,7 Go est déclarée mais désactivée par défaut. Son
téléchargement exige une sélection et un consentement explicites :

```bash
uv run --project backend python backend/scripts/acquire_datasets.py \
  --resource ooc-images-v1 --allow-large
```

Prévoir plus de 14 Go libres pour l'archive et son extraction. Ne pas lancer
cette commande sur la machine actuelle sans libérer de l'espace.

## Vérification seule

```bash
uv run --project backend python backend/scripts/acquire_datasets.py --verify-only
```

L'extracteur refuse les chemins sortant du dossier cible et les liens
symboliques. Les dossiers `__MACOSX` et fichiers `desktop.ini` sont ignorés.
