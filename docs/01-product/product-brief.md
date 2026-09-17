# Vision produit

## Problème

Les équipes travaillant sur les organes-sur-puce accumulent des images de
microscopie, mais l'analyse reste souvent fragmentée entre fichiers, scripts,
logiciels spécialisés et interprétation manuelle. Cette fragmentation ralentit
la comparaison entre contrôle et traitement et rend la provenance difficile à
auditer.

## Proposition

**OrganChip Insight** transforme un lot d'images en une chaîne de preuves :

1. description de l'expérience et des groupes ;
2. contrôle de la qualité des images ;
3. segmentation et quantification ;
4. contrôle visuel des contours ;
5. comparaison descriptive de deux expériences, sans inférence biologique ;
6. export d'un rapport reproductible.

Le produit est positionné dans la catégorie **Tool & Platform** du challenge
AI4S. La valeur ne repose pas uniquement sur un modèle : elle vient de
l'expérience de bout en bout, de la traçabilité et de la possibilité de changer
de moteur d'inférence sans changer le workflow scientifique.

## Utilisateur principal

Un chercheur ou ingénieur en bio-imagerie qui possède des images et des
métadonnées expérimentales, mais ne veut pas maintenir une pile ML complexe.

## Promesse vérifiable du MVP

> En moins de trois minutes, un utilisateur peut créer une expérience, importer
> des images, lancer une inférence sans entraînement, inspecter les contours et
> retrouver le résultat après redémarrage.

Le contexte persistant comprend les identifiants de puce et de puits, la
lignée, le jour de culture et, lorsqu'elle est connue, une échelle physique
sourcée. Les mesures en pixels restent la référence ; les conversions en µm et
µm² ne sont ajoutées que si l'utilisateur renseigne explicitement l'échelle.

## Non-objectifs actuels

- diagnostic clinique ;
- interprétation causale automatique ;
- remplacement de la validation biologique ;
- entraînement sur des données privées sans audit préalable ;
- score de toxicité présenté sans cible et protocole validés.

## Critères de succès produit

| Dimension | Critère de sortie |
|---|---|
| Utilisabilité | parcours principal réalisable sans documentation externe |
| Fiabilité | données et résultats persistants, erreurs explicites |
| Transparence | moteur, version, limites et date visibles |
| Reproductibilité | API, CLI, Docker et tests fournissent le même pipeline |
| Valeur scientifique | overlays inspectables et métriques reliées aux images |
