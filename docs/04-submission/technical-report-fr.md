# OrganChip Insight : un espace de microscopie traçable pour les expériences sur puce

**Rapport technique candidat - 17 septembre 2026**

**Équipe :** Ben Lol OUMAR, unique membre et responsable de l'équipe. Aucune
affiliation institutionnelle n'est déclarée.

**Catégorie :** Outil & Plateforme

**Release :** candidat validé sur `dev` ; tag public en attente de l'autorisation du propriétaire

> Note de publication : les valeurs sont reliées aux rapports versionnés du projet.
> Le tag public et les URL publiques restent sous le contrôle du propriétaire
> et doivent être renseignés avant la soumission du Writeup Kaggle.

## Résumé

La microscopie d'organes sur puce produit des images longitudinales précieuses,
mais un résultat d'analyse est difficile à croire ou à réutiliser lorsque les
métadonnées d'acquisition, l'identité de l'algorithme, le coût de calcul et les
limites scientifiques sont séparés de la sortie. OrganChip Insight est un outil
et une plateforme locale et reproductible qui réunit la gestion d'expériences,
l'import robuste d'images, la segmentation CPU, l'inspection des overlays, les
mesures par image, l'export des résultats et un registre transparent des moteurs.
Le moteur adaptatif par défaut ne requiert aucun poids appris et fonctionne hors
ligne. Les benchmarks externes BBBC019, BBBC038 et iOrganoAssay sont produits
par des scripts versionnés et présentés dans le produit avec l'incertitude, le
temps d'exécution, la mémoire, les décisions de promotion et la provenance
SHA-256.

La crédibilité fait partie de l'implémentation, et non d'une annexe. L'étude de
classification de qualité des images d'organes sur puce emploie des splits
groupés, des contrats d'exécution verrouillés, des comparateurs fondés uniquement
sur les métadonnées, des métriques par mode et des ablations pré-enregistrées.
Aucune configuration n'a démontré un signal de qualité robuste et indépendant
des métadonnées d'acquisition et de culture ; le split de test gelé n'a donc
jamais été ouvert. Le CNN retenu est limité à un démonstrateur ONNX optionnel qui
s'abstient toujours et ne produit jamais de décision automatique bon/mauvais.
De même, l'interface indique des composantes connexes plutôt que des cellules,
car aucune annotation d'instances ne valide le comptage sur les images du concours.

Le système obtenu n'est pas un dispositif de diagnostic. C'est un workflow local
et auditable d'exploration microscopique attentive à la qualité, conçu pour
préserver la relation entre images, mesures, métadonnées, incertitude et résultats
négatifs.

## 1. Problème et utilisateur cible

Les expériences bright-field sur organes sur puce produisent souvent des images
répétées selon les dispositifs, lignées, jours de culture et modes d'acquisition.
Un laboratoire a besoin de plus qu'un modèle de segmentation isolé. L'unité utile
est une expérience qui conserve le contexte, valide les fichiers entrants,
préserve les images brutes, rattache chaque sortie à une version du moteur et
exporte des preuves révisables en dehors de l'application.

L'utilisateur cible est un laboratoire de recherche travaillant sur des images
non cliniques d'organes sur puce. Le workflow principal est le suivant :

1. créer une expérience nommée et enregistrer les métadonnées disponibles ;
2. importer un lot d'images et inspecter les fichiers acceptés et rejetés ;
3. exécuter un moteur d'analyse déclaré ;
4. examiner les overlays et les mesures par image ;
5. exporter des preuves structurées pour une analyse ou un audit ultérieur.

OrganChip Insight ne revendique ni diagnostic, ni recommandation thérapeutique,
ni prédiction de toxicité ou d'efficacité, ni comptage cellulaire validé.

## 2. Données, provenance et base juridique

### 2.1 Jeux de données

| Jeu de données | Version et licence | Usage dans le projet | Traçabilité |
|---|---|---|---|
| OOC Image Dataset, Zenodo 10203721 | version 2023, CC-BY-4.0 | étude groupée de classification de qualité | manifestes train/validation/test verrouillés et checksums |
| BBBC019 Microfluidics | v2, CC-BY-3.0 | benchmark externe de segmentation du premier plan | manifeste, CSV par image et rapport JSON |
| BBBC038 stage 1 train | v1, CC0-1.0 | benchmark borné d'instances et de comptage sur 12 images | hashes de l'archive, des images et des masques ; manifeste verrouillé |
| iOrganoAssay | v1.1.0, CC0-1.0 | validation externe pré-enregistrée du premier plan d'organoïde sur 28 triplets BF/GT/Seg | MD5 de l'archive, manifeste verrouillé de 84 fichiers, CSV par image et rapport JSON |

La déclaration complète des données est maintenue dans
[`docs/03-competition/ai-and-licenses.md`](../03-competition/ai-and-licenses.md).
Aucune donnée personnelle, clinique ou privée n'est utilisée.

### 2.2 Pourquoi quatre jeux de données ne forment pas une seule validation

Les jeux répondent à des questions différentes. BBBC019 fournit des masques
binaires de premier plan pour un petit ensemble microfluidique DIC. BBBC038
fournit des masques d'instances nucléaires qui permettent d'auditer la détection
d'instances et le comptage. Le jeu OOC du concours fournit des étiquettes de
qualité au niveau image, mais aucun masque d'instance. Les scores sont donc
présentés par jeu et par tâche. Ils ne sont jamais fusionnés en un chiffre unique.
iOrganoAssay fournit le masque d'un organoïde cible ; il ne valide ni la
segmentation OOC, ni la classification, ni le comptage cellulaire.

### 2.3 Dépendance longitudinale et conception du split

La structure des noms et acquisitions a révélé que des dates adjacentes et des
lignées communes pouvaient traverser un split naïf. L'audit des campagnes a
identifié 29 campagnes de trois jours et 270 images de test exposées à une date
voisine avec leur propre lignée dans l'ancien split. Il s'agit d'un risque de
dépendance longitudinale, et non d'une preuve que deux images viennent de la même
puce physique. Un manifeste v2 conscient des campagnes a donc été pré-enregistré
et généré, tandis que le split v1 a été conservé. Les détails figurent dans
[`docs/02-research/protocols/campaigns-v2.md`](../02-research/protocols/campaigns-v2.md) et
[`reports/ooc-campaign-split-v2.json`](../../reports/ooc-campaign-split-v2.json).

La formulation honnête reste la suivante : le split est groupé par date
d'acquisition et contrôlé pour les quasi-doublons détectés, mais l'indépendance
biologique n'est pas établie faute d'identifiants de puce et de puits.

## 3. Architecture du système

La plateforme adopte volontairement une architecture locale réduite :

```text
Interface React + TypeScript
        |
        v
Application FastAPI ---- OpenAPI et CLI
        |
        +---- SQLite : expériences, images, résultats
        +---- système de fichiers : uploads et overlays
        +---- registre de moteurs
                +---- segmentation adaptative v1
                +---- démonstrateur ONNX optionnel du run B
                +---- candidats de benchmark isolés
```

Docker Compose regroupe le frontend, Nginx, le backend et le volume persistant.
Nginx et l'API appliquent des contraintes cohérentes de taille et de sécurité.
Les conteneurs utilisent des comptes non root. Les dépendances Python et
JavaScript exactes sont verrouillées dans `backend/uv.lock` et
`frontend/package-lock.json`.

## 4. Méthode produit

### 4.1 Import robuste

Le backend décode les formats PNG, JPEG et TIFF au lieu de se fier aux extensions.
Il borne la taille et le nombre total de pixels, détecte les doublons binaires et
prend en charge les TIFF 16 bits en niveaux de gris. L'entrée de mesure est
normalisée par percentiles robustes, tandis que le fichier original est préservé.
L'import et l'analyse sont deux opérations séparées, ce qui empêche un échec
d'analyse de dupliquer les images lors d'une nouvelle tentative.

### 4.2 Segmentation adaptative

Le moteur par défaut utilise un seuillage classique et de la morphologie, suivis
d'une analyse des composantes connexes. Il n'a aucun poids externe et fonctionne
sur CPU. Les sorties comprennent l'overlay de segmentation, la fraction de premier
plan, le nombre de composantes, les résumés de surface, le diamètre estimé en
pixels, l'intensité, le contraste et un indice de contraste relatif.

Ces sorties sont des heuristiques exploratoires. Une composante connexe peut en
particulier regrouper plusieurs cellules ou représenter un débris, une texture de
fond ou une autre structure. L'interface et les exports conservent le terme
« composante connexe ».

### 4.3 Registre des moteurs et CNN expérimental

Chaque moteur déclare son statut, sa disponibilité, son rôle et ses limites. Le
modèle MobileNetV3 du run B ne peut être activé qu'avec un bundle ONNX local dont
les hashes du modèle, du prétraitement et du rapport de sélection correspondent
aux valeurs déclarées. Il redimensionne une entrée en niveaux de gris à 448 pixels
selon le contrat de prétraitement exporté.

Chaque sortie CNN porte le statut « À vérifier ». Le softmax est explicitement
étiqueté comme non calibré, le mode d'acquisition et les hashes de provenance sont
affichés, et aucune conclusion automatique bon/mauvais, aucun overlay de
segmentation et aucun comptage ne sont attachés. Sans ONNX Runtime ou sans le
bundle exact, le moteur reste visible mais indisponible, tandis que le workflow
adaptatif continue de fonctionner.

## 5. Conception de l'évaluation

### 5.1 Benchmarks externes de segmentation et d'instances

Les scripts BBBC019 calculent F1 et IoU du premier plan par image, bootstrapent
les macro-métriques, enregistrent le temps et la mémoire du processus et génèrent
des overlays d'erreur. Les rapports adaptatif et µSAM couvrent les mêmes 13 images.

Le protocole BBBC038 a été committé avant l'exécution. Il fixe un sous-ensemble
déterministe de 12 images, µSAM `vit_b_lm` avec génération automatique de prompts,
le F1 objet aux IoU 0,50 et 0,75, l'erreur absolue médiane en pourcentage du
comptage et trois critères de promotion. Aucun réglage postérieur au résultat n'a
été effectué. Voir
[`docs/02-research/protocols/bbbc038-instances-v1.md`](../02-research/protocols/bbbc038-instances-v1.md).

Le protocole iOrganoAssay a également été committé avant le score. Il évalue une
seule fois le moteur adaptatif gelé sur les 28 triplets officiels BF/GT/Seg de
la v1.1.0, avec seuils, adaptation d'entrée et trois critères de succès fixés.
Le GT officiel identifie un organoïde cible par champ et n'est pas une annotation
exhaustive d'instances. Voir
[`docs/02-research/protocols/iorganoassay-validation-v1.md`](../02-research/protocols/iorganoassay-validation-v1.md).

### 5.2 Classification de qualité

La cible de classification est binaire : `good`/`bad`. Le jour de culture et la
lignée sont des covariables et des comparateurs, pas des cibles. La validation a
été rapportée globalement et par mode d'acquisition, résolution, lignée et jour.

Le workflow sépare smoke tests, validation et évaluation finale. Le runtime, le
bundle source, les poids ImageNet, les manifestes de split, les checkpoints et
les archives de résultats sont identifiés par hashes. Un modèle couleur de
référence à 224 pixels et deux ablations pré-enregistrées ont été évalués : gris
à 224 pixels (A) et gris à 448 pixels (B). Une troisième ablation de recadrage
était conditionnelle et n'a pas été lancée, car le critère RGB pré-enregistré
n'était pas atteint. Le jeu de test gelé n'a jamais été ouvert.

Des règles fondées uniquement sur les métadonnées ont été ajustées sur le train
et évaluées sur la validation afin de mesurer la force des raccourcis. Un CNN
globalement fort peut en effet échouer au sein d'un mode d'acquisition.

## 6. Résultats

### 6.1 Segmentation du premier plan sur BBBC019

| Moteur | Macro-F1 | Intervalle bootstrap à 95 % | Macro-IoU | Temps CPU moyen/image | Mémoire maximale |
|---|---:|---:|---:|---:|---:|
| Segmentation adaptative v1 | 0.424892 | [0.369769, 0.467653] | 0.273632 | 0.112333 s | 324.668 MB |
| µSAM `vit_b_lm` APG | 0.815542 | [0.758206, 0.861862] | 0.698535 | 42.843791 s | 8702.957 MB |

Rapports sources :
[`JSON adaptatif`](../../reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json)
et
[`JSON µSAM`](../../reports/benchmarks/bbbc019-microfluidic-microsam-vit-b-lm-apg.json).

µSAM est plus précis sur cette petite tâche externe de premier plan, mais il est
environ 381 fois plus lent par image dans les environnements mesurés et utilise
nettement plus de mémoire. Les ratios de temps dépendent de l'environnement et
ne constituent pas une propriété générale indépendante du matériel.

### 6.2 Audit d'instances sur BBBC038

| Métrique | Résultat |
|---|---:|
| Macro-F1 objet à IoU 0,50 | 0.628327 |
| Macro-F1 objet à IoU 0,75 | 0.481698 |
| Erreur absolue médiane de comptage | 15.3409% |
| Temps CPU moyen/image | 36.690719 s |
| Mémoire maximale du processus | 8896.457 MB |

Le rapport source est
[`bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json`](../../reports/benchmarks/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json).
Deux des trois critères de promotion pré-enregistrés ont échoué. µSAM n'a pas été
promu dans le produit et aucun réglage n'a été effectué après observation du résultat.

### 6.3 Premier plan externe d'organoïde sur iOrganoAssay v1.1.0

| Métrique | Résultat adaptatif | Référence contextuelle Seg officielle |
|---|---:|---:|
| Macro-F1 | 0,822746 | 0,926390 |
| IC bootstrap 95 % du macro-F1 adaptatif | [0,772415 ; 0,867911] | - |
| Macro-IoU | 0,717835 | 0,868744 |
| Macro-F1 contrôle | 0,836929 | 0,878810 |
| Macro-F1 DSS | 0,808564 | 0,973971 |

Une seule image sur 28 (3,5714 %) est sous F1 0,50 ; les trois critères
pré-enregistrés sont atteints. Le temps moyen d'inférence adaptative est de
0,062657 seconde par image. Le cas le plus faible, `DSS_13`, illustre la limite
principale : le moteur inclut d'autres structures sombres ressemblant à des
organoïdes tandis que le GT officiel marque une cible centrale ; un premier
plan plausible supplémentaire est donc compté comme faux positif. Le résultat
est une preuve externe de segmentation d'un organoïde cible, pas une validation
d'instances plein champ ni d'essai biologique. Le rapport source est
[`iorganoassay-validation-v1.1.0-adaptive-v1.json`](../../reports/benchmarks/iorganoassay-validation-v1.1.0-adaptive-v1.json).

### 6.4 Classification de qualité et raccourcis de métadonnées

| Run | BA globale | BA L | BA RGB | AUC globale | AUC L | AUC RGB |
|---|---:|---:|---:|---:|---:|---:|
| Référence couleur 224 | 0.7619 | 0.7729 | 0.6315 | 0.7996 | 0.8521 | 0.6309 |
| A : gris 224 | 0.6704 | 0.7389 | 0.5948 | 0.7176 | 0.7529 | 0.5848 |
| B : gris 448 | 0.7750 | 0.8338 | 0.6079 | 0.8414 | 0.8551 | 0.6985 |
| Métadonnées : mode × classe de jour | 0.7920 | 0.8171 | 0.6533 | - | 0.8171 | 0.7068 |

Les valeurs du comparateur de métadonnées exigent une importante analyse de
sensibilité. En RGB, sa balanced accuracy de 0,6533 provient entièrement de la
distinction entre les étiquettes publiées `4_days` et `4+_days` ; leur fusion
réduit la balanced accuracy RGB à 0,5000 et la balanced accuracy globale à
0,7413. Ce comparateur met en évidence la structure du jeu et l'identification
des campagnes ; ce n'est pas un modèle de qualité déployable.

Pour le run B, la différence bootstrap avec la référence en RGB contient zéro,
et la sélection de seuil leave-one-date-out est instable. L'analyse post hoc au
sein des strates ne trouve qu'un résidu RGB modeste dans l'échantillon et ne peut
pas le séparer des effets de sélection de modèle. Les preuves et corrections
complètes figurent dans le
[`contre-audit de classification`](../02-research/audits/audit-2026-09-17-classification-cnn.md)
et le
[`rapport versionné des comparateurs`](../../reports/benchmarks/ooc-classification-comparators-campaign-v2.json).

**Conclusion scientifique figée :** « Sur cette validation, aucun signal de
qualité robuste et indépendant des métadonnées d'acquisition et de culture
n'est démontré ; le résidu observé en RGB pour le run B est modeste, mesuré en
échantillon et non distinguable d'un effet de sélection. »

L'étude de classification est donc close, aucune configuration n'est éligible
et le jeu de test gelé reste fermé.

## 7. Vérification du produit

La suite backend contient 185 tests collectés dans le candidat du 17 septembre
2026 : 184 réussissent et un test dépendant de l'environnement est ignoré. Ruff,
le type-check TypeScript, le build Vite de production, la synchronisation des
notebooks, celle du résumé de benchmarks, l'audit de l'arbre de release,
l'inventaire de checksums et la configuration Docker Compose passent via
`make check`.

Playwright démarre des projets Docker isolés avec des volumes neufs. Le parcours
rapide crée une expérience, importe une image synthétique, exécute l'inférence
adaptative, vérifie l'overlay et la réserve scientifique, puis télécharge JSON
et CSV. Un second parcours importe trois images publiques verrouillées par hash
(OoC RGB, OoC en niveaux de gris et TIFF BBBC019), vérifie les métadonnées du
format source, exécute le même workflow et confirme que tous les hashes des
sources restent inchangés. Des barrières supplémentaires rapportent zéro
violation Axe, vérifient le focus clavier visible, le reflow mobile à 390 px,
une largeur effective à 200 %, ainsi que la persistance des sources, résultats,
exports, galerie et visionneuse après redémarrage des deux conteneurs.

Le candidat a également été reconstruit avec
`docker compose build --pull --no-cache`. L'audit de release n'a trouvé aucun
secret suivi, chemin personnel, cache, jeu brut ni binaire de modèle non
distribuable. L'inventaire SHA-256 couvre 40 rapports, manifestes, notebooks,
sources de soumission et preuves frontend suivis.

## 8. Crédibilité et limites

1. **Groupement biologique.** La date d'acquisition est un proxy, pas un identifiant de puce ou de puits. L'indépendance biologique ne peut pas être établie.
2. **Étiquettes de qualité.** L'écran exhaustif de 4 717 056 paires trouve 116
   voisinages dHash ≤ 8, dont 26 à labels contradictoires. Cette similarité ne
   prouve pas une identité biologique ; le projet ne réinterprète ni ne corrige
   les labels après observation des sorties.
3. **Raccourcis d'acquisition.** La résolution identifie presque le mode et le mode interagit fortement avec la prévalence des classes. Les métriques globales sont insuffisantes.
4. **Petits benchmarks externes.** BBBC019 contient 13 images évaluées,
   BBBC038 un audit pré-enregistré de 12 images et iOrganoAssay 28 images de
   validation dans deux conditions. Aucun résultat n'est une estimation de
   population sur les images OOC. Le GT iOrganoAssay marque un organoïde cible,
   pas toutes les instances visibles.
5. **Aucune calibration physique.** Les surfaces et diamètres sont en pixels, pas en µm ou µm².
6. **Aucun comptage cellulaire validé.** Les composantes connexes sont des structures heuristiques, pas des cellules ou noyaux vérifiés sur OOC.
7. **Sortie CNN non calibrée.** Les valeurs softmax du démonstrateur optionnel ne sont pas des probabilités calibrées et ne pilotent aucune décision automatique.
8. **Périmètre de déploiement.** SQLite et les fichiers locaux conviennent à un prototype local ou une instance unique, pas à un système clinique multi-tenant.

## 9. Valeur pratique

La valeur immédiate de la plateforme est la discipline du workflow : images,
métadonnées, identité du moteur, overlays, mesures, exports et limites coexistent
dans une expérience. Un laboratoire peut comprendre pourquoi une image a été
rejetée, relancer une analyse sans réimporter, comparer les preuves des moteurs
et exporter un dossier révisable sans service externe.

Le résultat CNN négatif est également utile opérationnellement. Il empêche un
classifieur dominé par les raccourcis de devenir une barrière automatique et
identifie les métadonnées nécessaires aux futurs jeux : vocabulaire stable des
jours, identifiants de puce et de puits, types d'artefacts explicites,
calibration physique et au moins cinq dates indépendantes par mode.

Les recherches futures pourront étudier un score d'écart à la maturation
conditionné par mode, jour et lignée, des objectifs auxiliaires adversariaux pour
le jour de culture, des annotations expertes d'artefacts et l'interopérabilité
OME-Zarr. Ce sont des perspectives, pas des fonctionnalités de la soumission.

## 10. Reproduction

### 10.1 Produit

```bash
cp .env.example .env
docker compose up --build
```

Ouvrir `http://localhost:8080`. L'API se trouve sur `http://localhost:8000` et
le document OpenAPI sur `http://localhost:8000/docs`.

### 10.2 Vérification

```bash
make check
npm --prefix frontend exec playwright install chromium
make test-e2e
make test-real-images
make test-e2e-real
make test-release-persistence
```

### 10.3 Inférence en ligne de commande

```bash
cd backend
uv run python inference.py image-1.png image-2.tif --output-dir artifacts/demo
```

### 10.4 Vue versionnée des benchmarks

```bash
make benchmark-summary
```

`make check` vérifie que le résumé frontend généré correspond exactement aux
quatre rapports JSON verrouillés. Les jeux bruts restent hors de Git et sont
acquis ou vérifiés par les manifestes et scripts documentés dans
[`data/README.md`](../../data/README.md).

## 11. Outils d'IA, bibliothèques et licences

OpenAI Codex et Anthropic Claude Code ont contribué au code, aux tests, à la
documentation, aux contre-revues et à la revue de littérature sous contrôle
humain. Chaque métrique rapportée provient d'un script ou d'un rapport
versionné ; la prose générée n'est pas présentée comme preuve expérimentale. Le
produit ne dépend d'aucun LLM, modèle hébergé ou API commerciale.

La déclaration canonique, incluant µSAM, MobileNetV3, les jeux de données et
les bibliothèques principales, est disponible dans
[`docs/03-competition/ai-and-licenses.md`](../03-competition/ai-and-licenses.md).

**Licence du code :** Apache-2.0, consignée dans le fichier `LICENSE` à la
racine du dépôt.

**Bundle modèle :** non distribué dans cette soumission ; toute publication
future exige une décision de licence séparée et un bundle verrouillé par hash.

## 12. Conclusion

OrganChip Insight montre qu'une plateforme utile d'imagerie d'organes sur puce
ne se définit pas par un score unique. Elle se définit par un chemin complet
depuis une entrée validée jusqu'à des preuves inspectables et exportables, avec
provenance et limites préservées. Le workflow adaptatif est rapide, local et
disponible ; il atteint un macro-F1 de 0,822746 sur la validation externe
iOrganoAssay pré-enregistrée, tandis que le meilleur résultat µSAM sur BBBC019,
plus coûteux, reste un benchmark isolé et qu'un classifieur sensible aux
raccourcis ne peut pas prendre de décision automatique. La plateforme est donc
techniquement assez complète pour
être démontrée, tout en restant explicite sur les validations que les futures
données devront apporter.

## Références

1. Movčana et al. “Organ-On-A-Chip (OOC) Image Dataset for Machine Learning and Tissue Model Evaluation.” *Data* 9(2):28, 2024.
2. Ljosa, Sokolnicki et Carpenter. “Annotated high-throughput microscopy image sets for validation.” *Nature Methods* 9:637, 2012.
3. Archit et al. “Segment Anything for Microscopy.” *Nature Methods*, 2025.
4. Archit et Pape. “Revisiting foundation models for cell instance segmentation.” MIDL, 2026.
5. Howard et al. “Searching for MobileNetV3.” ICCV, 2019.
6. Nam et al. “iOrganoAssay: Microscopy Image Dataset for Organoid Assessment Assays.” *Data* 11(1):9, 2026.
