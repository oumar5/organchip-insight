# Bruit d'étiquettes dans les voisinages visuels OoC

Date : **17 septembre 2026**

Statut : **audit descriptif terminé ; aucune relabellisation**

## Question

Des images visuellement très proches reçoivent-elles parfois des étiquettes
`good` et `bad` différentes dans le dataset OoC ?

## Protocole

L'audit réutilise les 3 072 dHash 256 bits déjà versionnés dans
`reports/ooc-image-inventory-2026-09-16.csv` et compare exhaustivement les
4 717 056 paires. Une paire est signalée lorsque sa distance de Hamming est
inférieure ou égale à 8, seuil fixé dans l'audit initial. Les étiquettes, types
cellulaires, préfixes d'acquisition et splits sont lus dans le même inventaire.

SHA-256 de l'inventaire :

```text
26fbe2f67ed71389b61c815ce5a0813524da9f2d5ac52429b839fc873aeb17a0
```

## Résultats

| Mesure | Valeur |
|---|---:|
| Paires examinées | 4 717 056 |
| Paires candidates dHash ≤ 8 | 116 |
| Paires candidates à labels contradictoires | 26 |
| Paires candidates à types cellulaires différents | 97 |
| Paires candidates traversant le split publié | 57 |
| Paires contradictoires à types cellulaires différents | 23 |

Les 116 paires partagent toutes leur préfixe d'acquisition. Les 26 conflits
d'étiquette sont répartis aux distances 1 à 8 ; ils ne sont donc pas expliqués
par un seul doublon exact. Trois paires seulement ont un dHash identique, sans
conflit d'étiquette.

## Interprétation bornée

Le dHash est un écran de similarité, pas la preuve que deux images représentent
la même puce, le même puits ou le même champ. Inversement, la présence de 26
conflits parmi des voisinages visuels très proches montre que la frontière
`good`/`bad` n'est pas déductible de l'apparence globale seule avec une
certitude parfaite. Le fait que 23 conflits changent aussi de type cellulaire
indique un mélange entre apparence, lignée et politique d'étiquetage.

Cet audit ne produit pas une estimation statistique du taux d'erreur des 3 072
labels et ne remplace pas une relecture biologique. Il documente un risque de
bruit et de confusion qui justifie l'abstention du CNN et la présentation des
résultats par mode d'acquisition.

## Décision

- ne supprimer, corriger ou réétiqueter aucune image après observation des
  résultats ;
- conserver le test gelé fermé ;
- publier les 26 conflits comme limite du dataset, pas comme erreurs prouvées ;
- demander une relecture experte uniquement dans un futur protocole séparé.
