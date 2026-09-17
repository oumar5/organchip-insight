# Stratégie Kaggle et choix des modèles

Date de revue : **16 septembre 2026**

Statut : **décision d'orientation avant benchmark**

## Décision exécutive

OrganChip Insight doit rester dans la catégorie **Tool & Platform** et devenir
une plateforme de contrôle qualité et d'analyse quantitative des images
bright-field d'organ-on-chip. Le cœur scientifique recommandé comporte quatre
briques indépendantes :

1. une baseline classique, déjà opérationnelle, pour garantir une inférence
   immédiate et explicable ;
2. `µSAM + APG` comme premier candidat zero-shot pour la segmentation ;
3. un CNN transféré, avec MobileNetV3 comme baseline publiée, pour la
   classification `good` / `bad` du dataset OoC ;
4. une fusion **image + métadonnées expérimentales** pour tester si le type
   cellulaire, le temps, la densité et le débit améliorent réellement le contrôle
   qualité.

Un grand modèle vision-langage comme Gemma ou Kimi ne doit pas produire les
mesures scientifiques principales. Il peut devenir plus tard un assistant de
navigation ou de rédaction, strictement ancré sur les mesures calculées.

## État réel du challenge Kaggle

Observation effectuée sur la page connectée le 16 septembre 2026 :

- les règles sont acceptées et le compte a rejoint le challenge ;
- le formulaire externe a été envoyé par l'utilisateur ;
- l'échéance affichée est le **10 octobre 2026 à 17 h 59, heure de Paris** ;
- à la date de cette sonde, l'équipe portait encore le nom par défaut
  `Oumar Ben Lol` ; l'identité publique a depuis été corrigée en
  **Ben Lol OUMAR** dans les livrables du 17 septembre 2026 ;
- aucun Writeup n'a encore été créé pour notre équipe ;
- la page affichait 120 entrants, 2 participants, 2 équipes et 2 soumissions ;
- les deux soumissions officielles sont anonymisées comme `Team 1` et `Team 2`
  et marquées « Viewable at Hackathon close » ;
- il n'existe pas d'onglet Leaderboard : l'évaluation est une revue d'experts,
  pas un score automatique sur un fichier de prédictions.

Conclusion : les résultats et dossiers complets des autres participants ne sont
pas visibles actuellement. Une personne a publié volontairement un concept
détaillé dans Discussion, mais ce n'est pas un résultat officiel ; le notebook
annoncé dans ce message renvoyait « page introuvable » lors de la vérification.
Ses chiffres ne peuvent donc pas servir de benchmark reproductible.

Le concours souffre d'une incertitude de classement plus forte qu'une
compétition avec leaderboard. Notre défense doit donc rendre chaque affirmation
facile à vérifier : script, jeu de données, split, métriques, erreurs et vidéo
réelle.

## Préconfiguration Kaggle recommandée

Kaggle doit servir à la remise et à une reproduction de secours, pas à héberger
le développement principal.

À faire maintenant ou au début du prochain bloc :

1. renommer l'équipe `OrganChip Insight` ;
2. créer un **brouillon privé** de Writeup avec la catégorie `Tool & Platform`,
   sans le soumettre ;
3. préparer son plan : problème, démonstration, dépôt, résultats, limites ;
4. conserver le développement local et les données hors Git ;
5. ne créer un jeton Kaggle CLI que si un notebook ou un dataset Kaggle doit être
   synchronisé ; le jeton reste hors du dépôt et n'est jamais journalisé ;
6. préparer plus tard un notebook Kaggle minimal qui reproduit un benchmark sur
   CPU ou GPU gratuit, sans service payant ;
7. vérifier avant remise que le dépôt, la vidéo et la démo sont accessibles sans
   demande de permission.

Le challenge ne fournit pas son propre dataset à télécharger. Préconfigurer la
CLI Kaggle n'est donc pas le premier bloc scientifique. Les téléchargements
Zenodo et BBBC doivent être gérés par nos scripts avec manifestes et checksums.

## Ce qui existe déjà

| Solution | Ce qu'elle fait bien | Limite par rapport à OrganChip Insight |
|---|---|---|
| CellProfiler | Pipelines reproductibles, segmentation, mesures morphologiques, lots importants | Paramétrage expert, pas centré OoC ni comparaison moderne de moteurs |
| ilastik | Segmentation interactive par apprentissage classique | Workflow de bureau, déploiement web et provenance expérimentale limités |
| napari | Excellent visualiseur multidimensionnel et écosystème de plugins | Ce n'est pas une plateforme d'expérience ou de reporting en soi |
| Cellpose / Cellpose-SAM | Très forte segmentation cellulaire généraliste | Poids entraînés sur des données CC-BY-NC ; risque pour un projet avec prix et avenir commercial |
| CellSAM | Bon zero/few-shot sur plusieurs modalités cellulaires | Poids officiels annoncés pour usage académique non commercial uniquement |
| µSAM | Segmentation/annotation 2D, 3D et tracking, modèles adaptés à la microscopie | Plus lourd que la baseline et doit être validé sur nos images OoC |
| Orbits Oncology / Incucyte | Produits intégrés pour organoïdes, live-cell et high-content imaging | Solutions commerciales, fermées et généralement liées à un contexte matériel ou assay |

Il existe donc beaucoup de briques de segmentation et quelques plateformes
commerciales. Notre originalité défendable n'est pas « l'IA sait segmenter ».
Elle est la combinaison suivante : OoC public, comparaison reproductible de
moteurs, contrôle qualité image, métadonnées expérimentales, analyse d'erreurs,
provenance et interface utilisable sans équipement propriétaire.

## Le dataset OoC change la question scientifique

Le dataset public principal contient **3 072 images bright-field** et une
étiquette experte `good` / `bad`. Une image `bad` peut notamment contenir des
parois déformées, bulles, flou ou défaut de mise au point. Certaines lignes
incluent aussi type cellulaire, temps après ensemencement, densité et débit.
L'archive d'images pèse environ 6,7 Go et le tableur de métadonnées environ
120 Ko.

Les auteurs ont publié une baseline **MobileNetV3** par transfert ImageNet. Ils
annoncent sur leur test une accuracy de 0,81, une précision de 0,79 et un rappel
de 0,78. Ces valeurs sont des résultats externes à reproduire, pas encore des
résultats d'OrganChip Insight.

Cette vérité terrain rend le contrôle qualité plus défendable que la seule
segmentation : nous pouvons reproduire une baseline publiée, mesurer une
amélioration et expliquer les erreurs. La segmentation reste utile pour montrer
les structures et produire des descripteurs, mais elle ne doit pas être confondue
avec l'étiquette de qualité.

## CNN ou Transformer ?

La réponse recommandée est **les deux, dans un benchmark court et contrôlé**.

### CNN

Un CNN transféré est le meilleur point de départ pour la classification OoC :

- le dataset n'a que 3 072 images ;
- MobileNetV3 fournit un résultat publié directement comparable ;
- les CNN sont moins coûteux et plus simples à expliquer avec Grad-CAM ;
- U-Net reste une baseline de segmentation biomédicale forte et efficace avec
  peu d'annotations et de l'augmentation.

### Transformer de vision

Un Transformer devient intéressant s'il est **préentraîné** :

- `µSAM` est spécialisé en segmentation microscopique ;
- `DINOv2 ViT-S/14` peut fournir des embeddings sans entraînement pour explorer
  les images, visualiser les groupes et entraîner un classifieur linéaire ;
- un ViT entraîné depuis zéro sur 3 072 images serait un risque inutile ;
- `DINOv3` est un candidat ultérieur, mais sa licence et son coût ajoutent une
  décision que DINOv2, Apache-2.0, permet d'éviter au premier jalon.

Le benchmark MIDL 2026 sur 36 jeux de microscopie rapporte que CellPoseSAM et
`µSAM + APG` figurent régulièrement parmi les meilleures approches, tandis que
les SAM généralistes restent moins fiables en microscopie. Il rapporte aussi que
SAM3 est sensible au texte de prompt et ne reconnaît pas toujours les termes
biologiques. Un grand modèle généraliste ne remplace donc pas un modèle adapté au
domaine.

## Modèle recommandé par fonction

| Fonction | Premier choix | Comparateur | Décision actuelle |
|---|---|---|---|
| Aperçu visuel brut | viewer React + tuiles + histogrammes | napari en développement | aucun modèle requis |
| Carte exploratoire des images | DINOv2 ViT-S/14 gelé + UMAP | descripteurs classiques | expérimentation sans entraînement |
| Segmentation zero-shot | µSAM ViT-B LM + APG | baseline adaptative actuelle | candidat prioritaire |
| Segmentation supervisée | petit U-Net | µSAM fine-tuné plus tard | seulement après benchmark zero-shot |
| Qualité `good` / `bad` | MobileNetV3 transféré | EfficientNet/ConvNeXt léger, DINOv2 + tête linéaire | reproduire d'abord la publication |
| Fusion image + contexte | embedding image + petit MLP/tabulaire en late fusion | image seule et métadonnées seules | multimodal pertinent |
| Explication utilisateur | règles + mesures + templates | Gemma 4 optionnel | hors chemin critique |
| Mesure scientifique | modèles ci-dessus + statistiques | jamais un VLM génératif | règle ferme |

## Le multimodal pertinent

Le mot « multimodal » recouvre deux idées très différentes.

### 1. Image + métadonnées expérimentales : oui

C'est le multimodal utile au projet. Nous devons comparer trois modèles :

1. image seule ;
2. métadonnées seules ;
3. image + métadonnées par fusion tardive.

Le troisième modèle concatène un embedding d'image à des variables encodées
(cell type, temps, densité, débit), puis utilise une petite tête de classification.
Il ne sera conservé que s'il améliore une validation groupée sans exploiter de
fuite. Cette ablation montrera aux juges la valeur réelle des métadonnées.

### 2. Image + texte dans un grand VLM : pas pour mesurer

Un VLM peut décrire une image de manière convaincante sans fournir un masque
pixel-par-pixel fiable, une calibration ou une reproductibilité biologique. Il
ne doit donc ni compter les cellules, ni décider qu'un tissu est viable, ni
produire un score de toxicité sans vérité terrain.

Il pourra plus tard :

- expliquer à l'utilisateur des métriques déjà calculées ;
- aider à retrouver une expérience par langage naturel ;
- rédiger un résumé explicitement marqué comme généré ;
- guider vers les overlays et limites du moteur.

## Gemma, MedGemma ou Kimi ?

### Gemma 4

Gemma 4 accepte texte et images, prend en charge le français et sa fiche officielle
annonce une licence Apache-2.0. Les variantes E2B/E4B sont les seules raisonnables
pour une démonstration locale légère. Ce serait notre choix si nous ajoutons un
assistant, car il est plus facile à reproduire et à redistribuer que les modèles
beaucoup plus lourds.

Mais Gemma 4 reste un VLM généraliste : il n'est pas entraîné pour tracer des
frontières cellulaires ou valider un phénotype OoC.

### MedGemma

MedGemma comprend du texte et certaines images médicales, mais Google demande une
validation et une adaptation pour chaque usage. Sa spécialisation clinique ne
correspond pas automatiquement à la microscopie bright-field OoC, et ses
conditions HAI-DEF sont plus complexes qu'Apache-2.0. Il n'apporte pas d'avantage
justifié au premier benchmark.

### Kimi-VL

Kimi-VL-A3B active environ 3 milliards de paramètres mais contient environ
16 milliards de paramètres au total, avec une fenêtre de 128K et de bonnes
capacités haute résolution/OCR. Les fichiers officiels représentent toutefois
plus de 30 Go de poids. Il est dimensionné pour le raisonnement visuel général,
pas la segmentation de cellules, et il est mal adapté à notre machine locale
(Intel, 64 Go de RAM, GPU AMD 8 Go) ainsi qu'à une démo simple.

Conclusion : **aucun VLM au jalon scientifique 1**. Si une couche conversationnelle
est ajoutée après les benchmarks, tester Gemma 4 E4B quantifié avant Kimi.

## Licences : porte de décision

| Candidat | État connu | Politique projet |
|---|---|---|
| baseline maison | code du projet | autorisé |
| U-Net implémenté dans le projet | dépendances permissives à figer | autorisé après audit |
| DINOv2 | code et poids Apache-2.0 | autorisé avec attribution |
| µSAM | code MIT ; exports de modèle annoncés CC-BY-4.0 | autorisé seulement après enregistrement de la licence exacte du checkpoint |
| Cellpose-SAM | code BSD, mais modèles entraînés sur données CC-BY-NC | `license-review`, pas de moteur par défaut |
| CellSAM | code Apache-2.0, poids officiels non commerciaux académiques | `license-review`, pas de moteur par défaut |
| Gemma 4 | fiche officielle Apache-2.0 | optionnel, attribution et modèle exact à figer |
| MedGemma | conditions HAI-DEF spécifiques | non retenu au premier jalon |
| Kimi-VL | dépôt/modèle annoncé MIT | optionnel mais non retenu pour coût et inadéquation |

Le manifeste devra distinguer licence du code, des poids, des données
d'entraînement et des données d'évaluation.

## Plan expérimental recommandé

### Étape 0 — Audit léger, sans entraînement

1. télécharger uniquement le tableur OoC ;
2. produire un manifeste avec URL, date, taille, checksum et licence ;
3. auditer les colonnes, valeurs manquantes et identifiants d'expérience ;
4. vérifier si le split publié sépare réellement les puces/acquisitions ;
5. télécharger BBBC019 et vérifier images/masques manuellement.

### Étape 1 — Prévisualisation reproductible

1. galerie de miniatures et métadonnées ;
2. histogrammes de résolution, intensité et labels ;
3. détection de doublons par hash perceptuel ;
4. embeddings DINOv2 gelés et projection UMAP ;
5. coloration de la projection par label, lignée et temps, sans ajuster de
   classifieur à ce stade.

### Étape 2 — Segmentation sans entraînement

Comparer sur BBBC019 :

- baseline adaptative actuelle ;
- µSAM AIS ;
- µSAM APG.

Mesures : précision, rappel, F1, IoU, temps par mégapixel, mémoire et cas d'échec.
Les 13 images étant peu nombreuses, publier les valeurs image par image et des
intervalles bootstrap, pas seulement une moyenne.

### Étape 3 — Contrôle qualité OoC

1. majorité naïve ;
2. reproduction MobileNetV3 ;
3. petit CNN alternatif ;
4. DINOv2 gelé + régression logistique ou petite tête ;
5. comparaison image seule / métadonnées seules / fusion.

Mesures : balanced accuracy, macro-F1, précision, rappel, AUROC, PR-AUC,
calibration, matrice de confusion et performance par lignée cellulaire.

### Étape 4 — Validation anti-fuite

Le split final doit regrouper, selon les identifiants disponibles, par puce,
expérience, session, canal ou séquence. Des vues proches de la même acquisition
ne doivent jamais se retrouver dans entraînement et test. Les résultats avec le
split publié seront rapportés séparément d'un split groupé plus strict.

### Étape 5 — Intégration produit

L'interface affichera côte à côte : image brute, masque, score de qualité,
incertitude, métadonnées, provenance du moteur et limites. Une prédiction sous un
seuil de confiance devient « à vérifier », jamais une conclusion biologique.

## Ce qu'il ne faut pas faire maintenant

- entraîner un ViT depuis zéro ;
- intégrer Kimi ou Gemma avant les benchmarks ;
- annoncer une prédiction de toxicité sans dataset avec dose et outcome ;
- utiliser un poids non commercial comme dépendance principale ;
- télécharger 6,7 Go sans manifeste ni contrôle de disque ;
- optimiser sur un split susceptible de contenir des vues de la même expérience ;
- reproduire les affirmations d'un concurrent sans code accessible.

## Prochain bloc concret

Le prochain bloc doit être **data-audit**, pas `training` :

1. scripts de manifeste et téléchargement ;
2. métadonnées OoC uniquement ;
3. BBBC019 complet ;
4. rapport automatique d'intégrité ;
5. benchmark de la baseline actuelle sur BBBC019 ;
6. seulement ensuite, branche expérimentale µSAM.

Le meilleur levier non technique reste de faire relire la méthodologie et les
overlays par une personne en biologie/bio-ingénierie. Le règlement annonce un
bonus interdisciplinaire et, surtout, cela réduit le principal risque du projet :
une plateforme techniquement réussie mais scientifiquement mal cadrée.

## Sources principales

- [Challenge Kaggle AI4S](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien)
- [Dataset OoC sur Zenodo](https://zenodo.org/records/10203721)
- [Article et baseline MobileNetV3 du dataset OoC](https://www.mdpi.com/2306-5729/9/2/28)
- [Segment Anything for Microscopy, Nature Methods](https://doi.org/10.1038/s41592-024-02580-4)
- [Dépôt officiel µSAM](https://github.com/computational-cell-analytics/micro-sam)
- [Benchmark MIDL 2026 des foundation models cellulaires](https://arxiv.org/abs/2603.17845)
- [U-Net](https://arxiv.org/abs/1505.04597)
- [CellSAM, Nature Methods](https://www.nature.com/articles/s41592-025-02879-w)
- [Dépôt officiel Cellpose et avertissement de licence des modèles](https://github.com/MouseLand/cellpose)
- [DINOv2 et licence des poids](https://github.com/facebookresearch/dinov2)
- [Fiche officielle Gemma 4](https://ai.google.dev/gemma/docs/core/model_card_4)
- [FAQ officielle MedGemma / HAI-DEF](https://developers.google.com/health-ai-developer-foundations/faqs)
- [Dépôt officiel Kimi-VL](https://github.com/MoonshotAI/Kimi-VL)
- [CellProfiler](https://cellprofiler.org/)
- [État de l'art 2026 du profilage par l'image](https://pmc.ncbi.nlm.nih.gov/articles/PMC13144522/)
- [Revue IA et organ-on-chip](https://pmc.ncbi.nlm.nih.gov/articles/PMC10046732/)
