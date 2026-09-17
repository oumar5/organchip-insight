# Protocole de regroupement par campagne — candidat v2

Statut au 16 septembre 2026 : règle écrite avant l'exécution de l'audit structurel ;
audit exécuté, aucun nouveau split ni score CNN calculé. Le split v1 et les résultats
historiques restent inchangés. Ce document ne rend pas le test historique vierge :
ses labels et les résultats du baseline ont déjà été examinés.

## Ce que représente un groupe

Une date d'acquisition est un nœud. Deux dates distinctes sont reliées si leur
écart est inférieur ou égal à **3 jours calendaires** et si elles ont au moins un
type cellulaire en commun. Une campagne est une composante connexe de ce graphe.
Toutes les images de toutes les dates d'une composante restent ensemble, même
celles dont le type cellulaire ne justifie pas directement une arête.

La fermeture transitive est intentionnelle : une campagne peut donc durer plus
de 3 jours. Les types cellulaires ne constituent pas des identifiants de puce,
de culture, de donneur ou de réplicat biologique. Cette règle est une précaution
contre une dépendance temporelle plausible, pas une preuve d'indépendance.

## Audit structurel avant toute affectation

Le script `backend/training/audit_ooc_campaigns.py` doit produire :

- les arêtes, leurs types cellulaires communs et les splits v1 concernés ;
- deux décomptes distincts pour le test v1 : images sur une date voisine d'un
  autre split, et images dont le type cellulaire participe à cette proximité ;
- les composantes, leur durée, leurs effectifs et les splits v1 traversés ;
- les hashes des entrées et de la règle, sans entraîner ni évaluer de modèle.

Le seuil primaire reste 3 jours. Les seuils 1 et 7 jours ne servent qu'à décrire
la sensibilité structurelle, jamais à choisir le meilleur score. L'audit ne crée
pas automatiquement un v2 : il faut d'abord vérifier qu'il reste assez de groupes
et que leur composition permet une évaluation interprétable.

Résultat de cette première exécution : 59 dates, 29 campagnes au seuil primaire,
21 arêtes traversant les splits v1, 345 images test sur les dates concernées dont
270 du type cellulaire partagé. La plus longue composante dure 9 jours, la plus
grande contient 533 images. Les seuils descriptifs 1 et 7 jours donnent
respectivement 41 et 17 composantes ; ils ne remplacent pas le seuil primaire.
Les 29 groupes ne garantissent pas, à eux seuls, la couverture des catégories.

Preuve : [rapport structurel](../../../reports/ooc-campaign-structure-v2-2026-09-16.json).
Reproduction vers un **nouveau** fichier, sans écraser le rapport historique :

```bash
uv run --project backend python backend/training/audit_ooc_campaigns.py \
  --output /tmp/ooc-campaign-structure-reproduction.json
```

## Étape suivante, distincte et encore à réaliser

Si le regroupement est retenu, publier un manifeste séparé, conservant la date
originale et ajoutant un identifiant de campagne explicite. Avant sa génération,
figer les paramètres d'affectation : fractions train/validation/test 70/15/15,
seed 20260916, 20 000 essais d'équilibrage des catégories, poids label/type/jour
4/2/1 comme en v1. L'équilibrage peut utiliser les catégories des données, mais
jamais les performances d'un modèle. Si les contraintes de couverture échouent,
documenter l'échec au lieu d'ajuster silencieusement la règle.

### Addendum avant génération — échec de couverture observé

La première tentative d'affectation, le 16 septembre 2026, a échoué avant toute
écriture : elle sélectionnait deux des trois campagnes contenant `NHBE` pour le
test, donc la validation ne pouvait plus contenir cette catégorie. Aucun score
de modèle n'a été calculé et aucun manifeste candidat n'a été conservé.

La contrainte de couverture est rendue explicite avant la nouvelle génération :
le holdout test doit contenir chaque catégorie et laisser au moins deux campagnes
contenant chacune d'elles ; le holdout validation doit en contenir chacune et
en laisser au moins une pour train. Les 20 000 essais, la seed, les fractions et
les poids restent inchangés. Cette règle formalise la couverture déjà exigée ;
elle n'utilise aucune performance de modèle.

Le manifeste a ensuite été généré sans entraîner ni évaluer de modèle : 2 056
images et 17 campagnes en train, 509 images et 6 campagnes en validation, 507
images et 6 campagnes dans le test final. Toutes les catégories exigées sont
présentes dans les trois partitions et aucune paire dHash ≤ 8 ne traverse les
partitions. Le rapport est
[ooc-campaign-split-v2.json](../../../reports/ooc-campaign-split-v2.json). Le test
reste physiquement séparé des entrées de sélection, même s'il est préparé comme
dataset privé pour l'évaluation finale.

Vérifier ensuite les quasi-doublons inter-splits avec le critère v1 (distance
dHash256 ≤ 8). Une violation bloque le gel du manifeste : elle ne justifie pas
de changer la règle après consultation des scores. Adapter le verrou de données
du CNN à ce manifeste explicite avant tout entraînement v2.

## Sélection du CNN

Les ablations couleur/niveaux de gris et résolution sont des hypothèses à tester
sur train/validation. Le nombre de runs est un budget, pas un critère scientifique.
Avant les runs, figer leur liste, les seeds, le budget, le critère de sélection
et les règles de seuil. Conserver la macro-F1 de validation comme référence du
pipeline actuel ; rapporter aussi la balanced accuracy par mode d'acquisition,
les effectifs et les classes présentes. Une tranche monoclasse ne permet pas
d'interpréter une balanced accuracy binaire comme une tranche à deux classes.

Ne pas choisir entre v1 et v2 sur les scores test. L'évaluation finale du CNN doit
suivre le gel des choix ; son verrou logiciel est limité au workspace et ne peut
pas effacer les consultations historiques du dataset.
