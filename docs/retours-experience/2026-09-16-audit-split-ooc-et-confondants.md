# Audit exhaustif du split OoC et des raccourcis

Date : **16 septembre 2026**

Statut : **audit reproductible terminé, risque de raccourci confirmé**

## Question

Le split OoC groupé par préfixe d'acquisition empêche-t-il les quasi-doublons
détectables de traverser train, validation et test ? Quelle performance peut-on
obtenir sans regarder les pixels, uniquement avec le mode et la résolution ?

## Correction de la preuve initiale

La première version du rapport réaffectait les 57 paires proches qui
traversaient le split publié, puis concluait qu'aucune ne traversait le nouveau
split. Cette vérification ne couvrait pas les paires qui se trouvaient dans le
même split publié mais auraient pu être séparées par le nouveau découpage.

Le générateur recalcule désormais toutes les paires entre splits groupés à
partir des dHash déjà versionnés dans l'inventaire. Il ne relit pas les 6,7 Go
d'images et conserve le CSV du split bit pour bit.

Commande :

```bash
make split-ooc
```

## Résultat anti-fuite

| Comparaison | Paires examinées | Candidats dHash ≤ 8 |
|---|---:|---:|
| Train ↔ validation | 987 294 | 0 |
| Train ↔ test | 1 010 801 | 0 |
| Validation ↔ test | 218 526 | 0 |
| **Total** | **2 216 621** | **0** |

Le contrôle est exhaustif pour le dHash 256 bits et le seuil 8. Il ne prouve
pas l'absence de correspondances après rotation, recadrage ou transformation
plus complexe. Le groupe `YYMMDD` reste par ailleurs un proxy de date, pas un
identifiant documenté de puce, puits, donneur ou expérience.

Le SHA-256 du split reste :

```text
5ffcf7ff0d69901f7362903d2532462c2758386dfbee2d6265b7a11d61b30d8c
```

## Baseline de raccourcis

Trois classifieurs catégoriels utilisent respectivement le mode, la résolution,
ou leur combinaison. Ils sont ajustés uniquement sur le train avec lissage de
Laplace α=1, probabilité globale train en repli et seuil fixé a priori à 0,5.
Aucun choix n'est effectué sur la validation ou le test.

La combinaison mode + résolution donne :

| Split | Macro-F1 | Balanced accuracy | ROC-AUC |
|---|---:|---:|---:|
| Train | 0,567498 | 0,599113 | 0,601835 |
| Validation | 0,690231 | 0,713283 | 0,719120 |
| Test | 0,695068 | 0,713569 | 0,713569 |

Les images RGB sont majoritairement `good`, tandis que les images en niveaux de
gris sont plus souvent `bad` dans la validation et le test. La résolution suit
presque la même séparation. Ces variables décrivent l'acquisition ; elles ne
constituent pas une preuve de qualité biologique.

## Décision

- conserver le split actuel : aucun candidat dHash ne le traverse au seuil
  choisi ;
- ne pas présenter cette absence comme une garantie contre toutes les fuites ;
- convertir toutes les entrées CNN en RGB avec un prétraitement identique, sans
  masquer le risque résiduel lié au contenu ;
- publier les métriques CNN par mode et par résolution ;
- comparer explicitement tout CNN à la macro-F1 test de raccourci `0,695068` ;
- garder le test inaccessible aux modes CNN `smoke` et `validation`.

## Artefact

Le rapport complet, ses distributions, ses métriques et les hashes de
provenance sont dans
[`reports/ooc-grouped-split-v1.json`](../../reports/ooc-grouped-split-v1.json).
