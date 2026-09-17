# Validation externe iOrganoAssay v1.1.0

Date : 17 septembre 2026

Statut : exécutée une seule fois après pré-enregistrement

Moteur : `adaptive-segmentation-1.1.0`, sans entraînement

## Question

Le moteur adaptatif gelé peut-il extraire le premier plan d'un organoïde sur
un jeu bright-field externe, sans régler ses paramètres après observation des
résultats ? Cette expérience ne cherche ni à valider le classifieur `good`/`bad`,
ni à compter des cellules.

## Protocole gelé avant le score

- source : iOrganoAssay v1.1.0, Zenodo `20351867`, licence CC0-1.0 ;
- archive : 1 817 410 571 octets, MD5
  `3cd6380e9413b977fdc531f32338ccd2` ;
- échantillon : les 28 triplets officiels BF/GT/Seg, soit 14 contrôle et
  14 DSS ;
- adaptation unique : redimensionnement de l'image BF vers la taille du masque
  GT avec LANCZOS ; algorithme adaptatif autrement inchangé ;
- masques JPEG GT/Seg binarisés par `valeur > 0,5`, comme dans le code R
  publié ;
- bootstrap : 10 000 itérations, unité image, seed `20260917` ;
- commit pré-enregistré : `fcec46b48ee9b30fa259dfb578930e78de4f25e6`.

Les trois critères fixés à l'avance étaient : macro-F1 globale au moins 0,70,
macro-F1 de chaque condition au moins 0,65 et au plus 20 % des images sous
F1 0,50.

## Résultats

| Mesure | Résultat |
|---|---:|
| Macro-F1 adaptatif | 0,822746 |
| IC bootstrap 95 % du macro-F1 | [0,772415 ; 0,867911] |
| Macro-IoU adaptatif | 0,717835 |
| Macro-F1 contrôle | 0,836929 |
| Macro-F1 DSS | 0,808564 |
| Images sous F1 0,50 | 1/28, soit 3,5714 % |
| Temps moyen d'inférence | 0,062657 s/image |
| Mémoire maximale du processus | 314,359 Mo |
| Référence Seg officielle, macro-F1 | 0,926390 |
| Référence Seg officielle, macro-IoU | 0,868744 |

Les trois critères sont atteints. Le résultat est donc admissible comme
**preuve externe de segmentation de premier plan d'organoïde**, sans promotion
d'un nouveau moteur ni modification du moteur gelé.

## Analyse d'erreur

Le cas le plus faible est `DSS_13` (F1 0,485618 ; précision 0,329094 ; rappel
0,926079). L'inspection de l'image, du GT et de l'overlay montre que le GT
officiel isole un organoïde central alors que l'algorithme sélectionne aussi
d'autres structures sombres plausibles dans le champ. Elles sont comptées
comme faux positifs par ce protocole. Cela limite l'interprétation du score :
le masque est une cible annotée, pas une annotation exhaustive de toutes les
instances visibles.

## Limites et décision

- Les images représentent des organoïdes intestinaux murins, pas les champs
  organ-on-chip du concours.
- Les 28 images appartiennent à deux conditions ; elles ne sont pas présentées
  comme 28 réplications biologiques indépendantes.
- Le benchmark évalue un premier plan binaire et non des instances, des cellules,
  une qualité `good`/`bad` ou un effet biologique.
- La sortie Seg officielle est une référence contextuelle fournie par le jeu,
  pas un modèle concurrent réexécuté dans notre environnement.
- Aucun seuil, aucune morphologie et aucun échantillon n'ont été modifiés après
  le score. Le test OoC gelé reste fermé.

Décision : intégrer le résultat dans l'interface et les livrables comme preuve
externe bornée. Ne pas changer la portée produit et ne pas revendiquer de
comptage cellulaire.

## Reproduction

```bash
make build-iorganoassay-manifest
make benchmark-iorganoassay
make benchmark-summary
```

Artefacts versionnés :

- `docs/02-research/protocols/iorganoassay-validation-v1.md` ;
- `data/manifests/iorganoassay-validation-v1.1.0.json` ;
- `reports/benchmarks/iorganoassay-validation-v1.1.0-adaptive-v1.json` ;
- `reports/benchmarks/iorganoassay-validation-v1.1.0-adaptive-v1.csv`.

Le rapport JSON conserve les hashes du manifeste et de la configuration, les
versions d'environnement, les 28 mesures par image et les avertissements de
portée.
