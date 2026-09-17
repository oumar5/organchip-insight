# Benchmark d'instances µSAM sur BBBC038 — 17 septembre 2026

## Décision

Le résultat est **mitigé et ne franchit pas la règle de qualification
pré-enregistrée**. µSAM APG montre un transfert zéro-shot réel sur plusieurs
styles d'images nucléaires, mais sa segmentation d'instances n'est pas assez
robuste sur les 12 cas hétérogènes pour promouvoir le moteur dans le produit ni
pour revendiquer un comptage cellulaire validé.

L'interface conserve donc la formulation « composantes connexes » et la réserve
explicite indiquant qu'elles ne sont pas validées comme cellules ou noyaux. Aucun
paramètre µSAM n'est ajusté après ce résultat.

## Protocole gelé avant exécution

- protocole :
  [`protocole-bbbc038-instances-v1.md`](../02-research/protocols/bbbc038-instances-v1.md) ;
- commit de pré-enregistrement : `72a391d365230fd0323a5456b84d98cc9b2cb9c3` ;
- BBBC038 `stage1_train`, 670 images et masques d'instances, CC0-1.0 ;
- archive SHA-256 :
  `dcb6edc2690f137406638b2309581a71522c4dff19157d118453b448dcddcb68` ;
- sous-ensemble image-only de 12 images couvrant les neuf résolutions, puis
  trois extrêmes d'apparence distincts ;
- manifeste SHA-256 :
  `c6c768b7b4aba84259e9e170bee5a5deb5354a898cdc3abcdaa4afb96f8cec2f` ;
- µSAM `1.8.14`, `vit_b_lm`, APG, CPU, paramètres par défaut déjà employés sur
  BBBC019, sans tuilage ni réglage sur BBBC038 ;
- appariement d'instances un-à-un à IoU 0,50 et 0,75 ;
- bootstrap par image, 10 000 itérations, seed `20260917`.

La sélection du sous-ensemble n'a utilisé ni masque ni nombre d'instances. Les
hashes de chaque image et de chaque arbre de masques sont vérifiés avant
l'inférence.

Pendant le calcul, un commit indépendant sur les fins de ligne CSV a avancé
`HEAD` à `4b6fc15`. Le rapport enregistre correctement ce commit d'exécution ;
il ne modifie ni la configuration, ni le manifeste, ni le moteur du protocole
pré-enregistré. Les hashes de ces entrées restent ceux du gel.

## Commande

```bash
cd backend
../data/cache/microsam-env/bin/python3.12 \
  -m evaluation.evaluate_instances \
  --config backend/evaluation/configs/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json
```

## Résultats observés

### Instances

| Seuil | Macro précision | Macro rappel | Macro-F1 | F1 groupé | IC 95 % du macro-F1 |
|---|---:|---:|---:|---:|---:|
| IoU 0,50 | 0,663017 | 0,603540 | 0,628327 | 0,461774 | [0,401074 ; 0,835413] |
| IoU 0,75 | 0,502359 | 0,465755 | 0,481698 | 0,299694 | [0,261909 ; 0,695900] |

À IoU 0,50, l'agrégation groupée compte 302 vrais positifs, 237 faux positifs
et 467 faux négatifs. La largeur des intervalles confirme une forte dépendance
au style d'image.

### Comptage

| Mesure | Valeur |
|---|---:|
| Instances annotées | 769 |
| Instances prédites | 539 |
| Erreur signée moyenne | -19,166667 par image |
| MAE | 19,333333 par image |
| IC 95 % bootstrap de la MAE | [6,416667 ; 37,168750] |
| Erreur absolue relative moyenne | 21,1377 % |
| Erreur absolue relative médiane | 15,3409 % |

Le moteur sous-compte globalement de 230 instances. La médiane masque une queue
d'échecs : trois images ont un comptage exact, mais l'image au niveau de gris
moyen maximal perd 33 des 46 noyaux annotés.

### Premier plan et coût

- macro-F1 pixel de contexte : `0,714617` ;
- macro-IoU pixel : `0,628000` ;
- chargement du moteur : `27,987375 s` ;
- inférence moyenne : `36,690719 s/image` ;
- durée totale, overlays compris : `445,941248 s` ;
- mémoire maximale du processus : `8 896,457 Mo`.

Le coût CPU et mémoire confirme que µSAM doit rester un benchmark isolé dans
l'état actuel, pas un moteur synchrone du parcours Docker.

## Application de la règle pré-enregistrée

| Condition | Seuil | Observé | Verdict |
|---|---:|---:|---|
| Macro-F1 objet, IoU 0,50 | ≥ 0,70 | 0,628327 | échec |
| Macro-F1 objet, IoU 0,75 | ≥ 0,50 | 0,481698 | échec |
| Erreur absolue relative médiane de comptage | ≤ 20 % | 15,3409 % | réussite |

Une seule condition sur trois est satisfaite. La qualification « signal externe
encourageant pour le comptage nucléaire » n'est donc pas attribuée.

## Analyse d'erreurs

- les images simples à noyaux isolés peuvent atteindre un F1 objet de 1,0 aux
  deux seuils ;
- les champs denses restent raisonnables mais accumulent fusions, omissions et
  faux positifs ;
- sur certains styles clairs, APG segmente de larges structures cellulaires au
  lieu des noyaux annotés : le comptage et l'IoU s'effondrent ;
- les trois plus mauvais F1 à IoU 0,50 sont `0`, `0,013158` et `0,163934` ;
  les trois meilleurs valent `1,0`, `1,0` et `0,933333`.

Les 12 overlays d'erreur sont générés sous
`reports/generated/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg/overlays/`
et restent non versionnés.

## Artefacts

- rapport JSON : SHA-256
  `5a5c4bf7909c4b39c152e753c5c120db329bc0b87f1997acc16e81b4509f6550` ;
- lignes CSV : SHA-256
  `8c2b25a8aab4a481fa2bd415d2a64821439051c7875a8922814c441a66382f9d` ;
- configuration : SHA-256
  `f1f530bf636212c974a75985a10ebcb05c6de533591252f1dfe430962f1ae085` ;
- poids `vit_b_lm` et décodeur : SHA-256 consignés dans le rapport JSON.

## Limites

- 12 images choisies pour la diversité et non aléatoirement : les scores ne
  sont pas une estimation de population sur les 670 images ;
- bootstrap sur seulement 12 images, d'où des intervalles larges ;
- BBBC038 annote des noyaux issus de contextes hétérogènes, pas des cellules
  dans les images OoC du concours ;
- aucune validation biologique ou annotation d'instances n'existe sur les
  images OoC ;
- un protocole v2 serait une nouvelle expérience, pas une correction de ce
  résultat. Il n'est pas prioritaire avant la soumission.

## Suite décidée

1. versionner les rapports JSON/CSV et ce REX ;
2. ne pas intégrer µSAM au chemin produit synchrone ;
3. ne pas modifier les paramètres pour améliorer ce score ;
4. utiliser le résultat comme preuve de méthode et de transparence dans le
   rapport, en conservant la limite sur le comptage OoC ;
5. concentrer la suite sur l'expérience produit, le test machine propre, la
   documentation de soumission, la vidéo et la soutenance.
