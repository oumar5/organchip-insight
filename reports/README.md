# Rapports reproductibles

Ce dossier contient les sorties petites et auditables qui sont suivies par Git.
Les données sources restent dans `data/raw/` et les images d'erreur générées dans
`reports/generated/`, tous deux ignorés.

## Reproduire

```bash
make data-fetch
make data-audit
make benchmark-bbbc019
```

## Contenu

- `data-audit-2026-09-16.json` : intégrité, structure et risques de fuite ;
- `benchmarks/bbbc019-microfluidic-adaptive-v1.json` : protocole, provenance,
  agrégats, intervalles bootstrap et mesures image par image ;
- `benchmarks/bbbc019-microfluidic-adaptive-v1.csv` : mêmes mesures par image,
  faciles à analyser dans un tableur.

Les overlays d'erreur utilisent vert pour les vrais positifs, orange pour les
faux positifs et magenta pour les faux négatifs. Ils ne sont pas versionnés afin
de garder le dépôt léger.
