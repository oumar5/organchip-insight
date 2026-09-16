# Audit des données et première baseline BBBC019

Date : **16 septembre 2026**

Statut : **benchmark réel terminé, décision µSAM confirmée**

## Addendum du 16 septembre 2026

L'archive OoC complète a ensuite pu être téléchargée et auditée. Le blocage
décrit plus bas est donc historique : les chemins ont révélé que les 59
préfixes `YYMMDD` traversaient les splits publiés. Un split groupé par préfixe a
été figé et un premier classifieur image-only a été mesuré. Voir le
[retour d'expérience du baseline OoC](2026-09-16-baseline-ooc-handcrafted.md).

Le préfixe reste un proxy de date, pas un identifiant documenté de puce, puits,
donneur ou expérience. Le nouveau test réduit un risque de fuite sans devenir
pour autant une validation biologique indépendante.

## Résumé de la décision

Le chemin complet fonctionne : téléchargement borné, checksum, extraction sûre,
audit, inférence, comparaison à la vérité terrain, CSV, JSON et overlays
d'erreur. La baseline classique reste le moteur instantané et explicable, mais
ses erreurs sur BBBC019 sont trop importantes pour en faire le moteur
scientifique principal.

La prochaine expérience est donc `µSAM + APG`, évaluée avec exactement les mêmes
13 images, masques et métriques. Il ne faut pas encore entraîner MobileNetV3 sur
le dataset OoC : le tableur seul ne permet pas d'exclure une fuite entre vues de
la même puce ou acquisition.

## Provenance

| Élément | Valeur |
|---|---|
| Code évalué | commit `0bdee0ccc02d5a430331f7e698a189360a1be2f2` |
| OoC metadata | Zenodo 10203721, v1, CC-BY-4.0 |
| SHA-256 tableur | `863fc133f8be825c010c41ea26168fedb75af8d2722646f61402779583073eba` |
| BBBC019 | version 2, sous-ensemble Microfluidic, CC-BY-3.0 |
| SHA-256 archive | `968b74f478b59d8a558ea2582fea9796e3c2845922077819a5f7b6db6c157b5f` |
| Moteur | `adaptive-segmentation-1.0.0`, aucun poids, aucun entraînement |
| Graine bootstrap | `20260916`, 10 000 rééchantillonnages par image |

Commandes :

```bash
make data-fetch
make data-audit
make benchmark-bbbc019
```

Les sorties sources sont
[`reports/data-audit-2026-09-16.json`](../../reports/data-audit-2026-09-16.json)
et
[`reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json`](../../reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json).

## Ce que révèle le tableur OoC

Le classeur annonce 3 118 lignes après l'en-tête, mais 46 sont entièrement
vides. Il reste bien **3 072 images identifiées**, sans doublon d'`imageID`.

| Variable | Résultat |
|---|---:|
| Label `1` | 1 727 |
| Label `2` | 1 345 |
| Lignées cellulaires | 6 |
| Densité manquante | 344 / 3 072 |
| Temps après ensemencement manquant | 2 244 / 3 072 |
| Débit manquant | 859 / 3 072 |
| Identifiant explicite puce/puits/expérience | absent |
| Colonne train/validation/test | absente |

Les densités utilisent 20 écritures textuelles pour seulement 10 valeurs
numériques ; les débits utilisent plusieurs écritures de l'unité pour 6 valeurs.
Le pipeline d'entraînement devra normaliser ces champs sans transformer les
valeurs absentes en information artificielle.

Le codage `1` / `2` est conservé tel quel dans l'audit. L'association exacte à
`good` / `bad` devra être vérifiée contre les chemins de l'archive avant tout
entraînement, même si le titre de colonne suggère l'ordre.

### Blocage anti-fuite

Le split publié est matérialisé dans les dossiers de l'archive d'images, pas
dans le tableur. Les préfixes d'`imageID` ressemblent à des dates d'acquisition,
mais la documentation ne garantit pas qu'ils représentent des expériences,
puces, puits ou donneurs indépendants. En conséquence :

- l'analyse descriptive des métadonnées est autorisée ;
- l'entraînement de classification reste bloqué ;
- une accuracy obtenue aujourd'hui pourrait récompenser une fuite de contexte.

L'archive pèse 6,7 Go et la machine n'avait qu'environ 15 Gio libres. Archive et
extraction ne peuvent pas être lancées avec une marge de sécurité suffisante. Il
faut libérer de l'espace, utiliser un disque externe ou monter les données dans
un notebook Kaggle.

## Intégrité BBBC019

- 13 images DIC ;
- 13 masques manuels officiels ;
- 13 correspondances exactes par nom ;
- dimensions identiques pour chaque paire ;
- masques binaires contenant uniquement `0` et `1` ;
- aucun doublon exact d'image ;
- 13 masques de réannotation alternatifs présents mais non utilisés.

Le masque officiel `manual` est le seul utilisé dans cette mesure. Changer vers
`reannotation` constituerait un autre protocole et exigerait un autre identifiant
de benchmark.

## Résultats de la baseline

| Agrégation | Précision | Rappel | F1 | IoU |
|---|---:|---:|---:|---:|
| Macro, moyenne des 13 images | 0,521310 | 0,426830 | 0,424892 | 0,273632 |
| Micro, pixels regroupés | 0,511504 | 0,392183 | 0,443966 | 0,285319 |
| IC bootstrap 95 % macro | [0,419029 ; 0,610348] | [0,367141 ; 0,501803] | [0,369769 ; 0,467653] | [0,233589 ; 0,306250] |

La médiane F1 est 0,445442. L'inférence seule prend en moyenne environ
0,107 seconde par mégapixel sur la machine locale ; le pic RSS du processus est
d'environ 325 Mo. Le temps total incluant les 13 overlays est 8,5 secondes.

### Contexte historique, pas classement direct

La page BBBC rapporte pour ce sous-ensemble les moyennes historiques suivantes :

| Algorithme | Précision | Rappel | F1 |
|---|---:|---:|---:|
| TScratch | 0,35 | 0,79 | 0,42 |
| MultiCellSeg | 0,23 | 0,98 | 0,35 |
| Topman | 0,47 | 0,99 | 0,63 |
| Notre baseline | 0,521 | 0,427 | 0,425 |

Notre F1 est proche de TScratch, mais par un compromis très différent : meilleure
précision, rappel nettement plus faible. Cette comparaison reste indicative tant
que les détails de prétraitement et la version exacte des annotations historiques
ne sont pas prouvés identiques.

## Analyse des erreurs

Le pire cas, `SN90_C_3_000_dic.tif`, obtient F1 = 0,153604. Le seuillage confond
une grande texture de fond avec des cellules : rappel élevé mais énormément de
faux positifs. Le meilleur F1 n'est que 0,518228 sur
`SN90_C_7_075_dic.tif` ; l'algorithme détecte surtout des bords sombres et laisse
de larges surfaces cellulaires en faux négatifs.

Ces deux erreurs ne se corrigent pas proprement avec un unique seuil global. Les
overlays confirment donc la nécessité d'un modèle adapté à la microscopie, tout
en montrant pourquoi l'interface doit toujours afficher le masque au lieu de
présenter un nombre sans preuve visuelle.

## Suite ordonnée

1. figer la licence et le checkpoint exacts de µSAM/APG ;
2. intégrer le moteur comme dépendance optionnelle, jamais obligatoire pour le
   démarrage de l'application ;
3. exécuter le même benchmark sans ajuster sur les 13 masques ;
4. comparer F1, IoU, temps, mémoire et erreurs image par image ;
5. seulement après la stratégie de stockage OoC, auditer le split de chemins ;
6. entraîner ensuite MobileNetV3 et une baseline métadonnées avec validation
   groupée.

## Leçon produit

« L'inférence fonctionne » ne signifie pas « la mesure est bonne ». Un prototype
gagne en crédibilité lorsqu'il montre précisément où son premier moteur se trompe
et transforme cette faiblesse en protocole de sélection du moteur suivant.
