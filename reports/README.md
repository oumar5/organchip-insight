# Rapports reproductibles

Ce dossier contient les sorties petites et auditables qui sont suivies par Git.
Les données sources restent dans `data/raw/` et les images d'erreur générées dans
`reports/generated/`, tous deux ignorés.

## Reproduire

```bash
make data-fetch
make data-audit
make split-ooc
make train-ooc-baseline
make benchmark-bbbc019
```

## Contenu

- `data-audit-2026-09-16.json` : intégrité, structure et risques de fuite ;
- `benchmarks/bbbc019-microfluidic-adaptive-v1.json` : protocole, provenance,
  agrégats, intervalles bootstrap et mesures image par image ;
- `benchmarks/bbbc019-microfluidic-adaptive-v1.csv` : mêmes mesures par image,
  faciles à analyser dans un tableur.
- `benchmarks/bbbc019-microfluidic-microsam-vit-b-lm-apg.json` et `.csv` :
  benchmark zero-shot µSAM sur les mêmes 13 images et masques ;
- `ooc-grouped-split-v1.json` et `../data/splits/ooc-grouped-v1.csv` : split
  OoC groupé par préfixe d'acquisition, audit exhaustif des quasi-doublons et
  baseline de raccourcis mode/résolution ;
- `benchmarks/ooc-handcrafted-image-quality-v1.json` : sélection sur validation,
  évaluation test groupée, intervalles et tranches du baseline image-only ;
- `predictions/ooc-handcrafted-image-quality-v1-test.csv` : 473 prédictions test
  auditables ligne par ligne.

Les overlays d'erreur utilisent vert pour les vrais positifs, orange pour les
faux positifs et magenta pour les faux négatifs. Ils ne sont pas versionnés afin
de garder le dépôt léger.
