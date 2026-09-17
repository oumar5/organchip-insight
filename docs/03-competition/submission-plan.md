# Plan de soumission et de finale

État au **17 septembre 2026**. Échéance de soumission : **10 octobre 2026,
17 h 59 à Paris**. Finale en ligne avec soutenance : **20 au 30 octobre 2026**.
Le règlement officiel est résumé dans
[competition-requirements.md](requirements.md).

## Lecture stratégique

1. Le challenge n'a pas de leaderboard. Vingt équipes passent en finale ; au
   16 septembre, deux équipes sont inscrites sur Kaggle. Un dossier complet et
   valide a donc de fortes chances d'atteindre la soutenance : **la victoire
   se joue en finale**, devant un jury issu d'une société de puces
   neuro-organoïdes attachée à la standardisation et à la valorisation des
   données.
2. Les 60 % les plus lourds de la grille (impact 30 %, approche et innovation
   30 %) récompensent un problème important, une chaîne complète et une idée
   claire, pas un point de macro-F1 supplémentaire. Le travail de modélisation
   est clos au 17 septembre 2026 : validation GPU,
   comparateurs et ablations A/B exécutés sur train/validation, aucune
   configuration éligible, test jamais ouvert ; le produit intègre au plus un
   démonstrateur ONNX expérimental sans décision automatique.
3. Les travaux publiés sur le même dataset utilisent des splits aléatoires
   (voir [etat-de-l-art.md](../02-research/state-of-the-art.md)). Notre protocole anti-fuite,
   l'audit des raccourcis d'acquisition et l'accès test verrouillé sont la
   contribution scientifique à mettre en avant, en plus de la plateforme.
4. Deux blocages administratifs annulent tout le reste s'ils ne sont pas
   levés : le formulaire externe doit être confirmé et le dépôt GitHub est
   encore **privé**. La licence Apache-2.0 est désormais fixée et versionnée.

## Calendrier de travail

### Semaine 1 — 16 au 22 septembre : débloquer et sécuriser

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | **licence faite** : Apache-2.0 choisie et `LICENSE` ajouté ; équipe solo décidée ; garder le dépôt privé pendant la finalisation seulement, puis le rendre public avant la soumission | fichier versionné ; page GitHub publique encore requise |
| P0 | exécuter la sonde autonome `notebooks/ooc-runtime-probe-kaggle.ipynb` (prête, commit `008f507`) sur Kaggle avec **GPU activé** et Internet désactivé, sans données ; versionner `runtime-report.json` ; si `torch 2.11 / torchvision 0.26`, valider localement la paire puis étendre `kaggle-runtime-contract.json` ; ne jamais relâcher le contrat sans smoke local | rapport de sonde versionné |
| P0 | figer avant les runs un protocole d'ablation : couleur vs niveaux de gris (avec recadrage commun, les deux dispositifs diffèrent de 8 px), 224 px vs ≥ 512 px ou tuiles, seeds, budget de runs et critère de sélection ; ce sont des **hypothèses** à tester sur train/validation, pas des acquis ; métrique primaire = balanced accuracy **par mode d'acquisition** comparée au raccourci, avec effectifs et classes présentes par tranche | protocole d'ablation versionné |
| P0 | outil de préparation reproductible du bundle source (hash calculable localement) ; publier le bundle et les poids ImageNet MobileNetV3-Small comme dataset Kaggle privé avec SHA-256 ; lancer les runs `validation` bornés sur GPU ; publier les tranches mode/résolution/lignée/jour et la comparaison aux comparateurs recalculés sur le split v2 (raccourci `0,7249`, handcrafted `0,6867` de balanced accuracy) ; les scores v1 restent du contexte | REX daté, rapports JSON, checkpoints et hashes |
| P0 | **fait** : split v2 par campagnes fixé avant les runs, v1 conservé, comparateurs recalculés ; audit structurel de 29 campagnes et bruit d'étiquettes documenté sans relabellisation (116 paires dHash ≤ 8, dont 26 à labels contradictoires) | manifeste v2, REX et hashes versionnés |
| P0 | ~~corriger les défauts qui cassent une démo Docker~~ **fait** (commit `d3938a4`, 131 tests, vérification navigateur derrière nginx) ; restent la progression de l'analyse et les groupes témoin/traité | REX [imports et TIFF](../06-retrospectives/2026-09-16-imports-et-tiff.md) |
| P1 | **fait localement** : export JSON complet et CSV par image, détail par image et nom de l'expérience dans les résultats | [REX stabilisation](../06-retrospectives/2026-09-17-stabilisation-produit-exports-securite-docker.md) |
| P1 | **fait localement** : plancher typographique 12 px et contraste 4,5:1 contrôlés après analyse par Playwright + Axe ; 25 défauts initiaux corrigés, zéro violation résiduelle dans le scénario desktop | [REX Playwright](../06-retrospectives/2026-09-17-playwright-e2e.md) |

### Semaine 2 — 23 au 29 septembre : intégrer et comparer

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | ~~gel de la sélection CNN et run `final-eval`~~ **annulé** : aucune configuration éligible au 17 septembre 2026, test jamais ouvert, modélisation CNN close ; consigner le résultat négatif dans le rapport | [contre-audit](../02-research/audits/audit-2026-09-17-classification-cnn.md), phrase de conclusion dans le rapport technique |
| P1 | **fait localement** : démonstrateur ONNX expérimental du run B, `onnxruntime` en dépendance optionnelle, inférence CPU, abstention systématique, softmax non calibré affiché avec le mode d'acquisition et la provenance (hashes), aucune décision automatique `good`/`bad`, aucun overlay ni comptage rattaché ; le contrôle qualité produit reste le moteur adaptatif et les métadonnées ; poids non distribués avant décision de licence | tests API, fiche moteur `experimental`, [REX](../06-retrospectives/2026-09-17-demonstrateur-cnn-onnx.md) |
| P1 | **fait localement** : vue « Comparaison des moteurs » alimentée par quatre rapports versionnés (`reports/benchmarks/*.json`), dont la validation iOrganoAssay pré-enregistrée : F1/IoU, intervalles, coût CPU, mémoire, décision et hashes ; les overlays d'erreur sont produits par les benchmarks mais ne sont pas embarqués dans l'interface | générateur déterministe, tests, [REX de comparaison](../06-retrospectives/2026-09-17-comparaison-moteurs.md), [REX iOrganoAssay](../06-retrospectives/2026-09-17-validation-externe-iorganoassay.md), aucun chiffre saisi à la main |
| P1 | **fait localement selon l'option bornée** : champs témoin/traitement masqués tant qu'aucune affectation explicite par image et aucun agrégat de groupe ne sont livrés | [REX stabilisation](../06-retrospectives/2026-09-17-stabilisation-produit-exports-securite-docker.md) |
| P1 | **fait localement** : benchmark d'instances µSAM APG pré-enregistré sur 12 images BBBC038 (CC0), macro-F1 objet `0,628327` à IoU 0,50 et `0,481698` à IoU 0,75, erreur absolue relative médiane de comptage `15,3409 %` ; 2 critères sur 3 échouent, aucune promotion produit ; l'interface conserve « composantes connexes » et sa réserve OoC | [rapport JSON](../../reports/benchmarks/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json), [REX](../06-retrospectives/2026-09-17-benchmark-instances-bbbc038.md) |
| P2 | ~~Grad-CAM sur le CNN~~ retiré : aucun overlay n'est rattaché au démonstrateur, faute de signal démontré indépendant des métadonnées | — |
| P2 | ~~µSAM `vit_t_lm` en moteur optionnel asynchrone~~ retiré avant soumission : le benchmark `vit_b_lm` coûte déjà 36,7 s/image et 8,9 Go de mémoire, et échoue à 2 critères d'instances sur 3 ; rester en benchmark isolé documenté | [REX BBBC038](../06-retrospectives/2026-09-17-benchmark-instances-bbbc038.md) |

### Semaine 3 — 30 septembre au 6 octobre : figer et raconter

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | **fait localement** : reconstruction `--pull --no-cache`, parcours réel, CLI, contrôles d'accessibilité et persistance après redémarrage | `TASKS.md`, tests Playwright, `make check` |
| P0 | release `v1.0.0-ai4s` : tag, checksums des modèles et rapports, archive Zenodo optionnelle avec DOI | page release |
| P0 | **fait localement** : vidéos candidates anglaise et française de 3 min 18 s tournées sur le produit réel dans la langue de chaque montage, narrations locales, avatar, musique sous licence, sous-titres et SRT ; reste la publication | liens publics testés en navigation privée |
| P0 | **fait localement** : rapports techniques candidats anglais et français de 11 pages, PDF déterministes sans page vide, identité et licence fixées, chaque chiffre relié à un fichier versionné ; reste la publication | PDF publics |
| P0 | **fait localement hors liens publics** : catégorie, équipe Ben Lol OUMAR, résumé 200–300 mots, limites, déclarations et licence Apache-2.0 | brouillon relu |

### Tampon — 7 au 9 octobre

Soumettre le **9 octobre**, vérifier chaque lien sans connexion, garder le
10 octobre pour une correction d'urgence uniquement.

### 10 au 20 octobre : préparer la soutenance

- diapositives de 10 minutes : problème, démo en direct de 3 minutes, preuves,
  limites, valeur, feuille de route ;
- démo de secours : vidéo locale et instance Docker pré-démarrée ;
- questions probables : fuite de données et unité de groupe `YYMMDD`, calibration
  µm facultative et jamais devinée, différence avec Cellpose et CellProfiler, licence des poids,
  généralisation à d'autres puces ou lignées, ce qu'il faudrait pour un jumeau
  numérique, standardisation des métadonnées (OME).

## Correspondance grille officielle → preuves

| Critère | Poids | Preuve principale | Fichier ou artefact |
|---|---:|---|---|
| Importance et impact | 30 % | workflow OoC traçable, standardisation des entrées et preuves exportables | interface, JSON/CSV, rapport |
| Approche et innovation | 30 % | registre de moteurs comparables + accès test verrouillé + audit des raccourcis | `backend/app/ml/registry.py`, protocole CNN, rapports de split |
| Résultats et validation | 20 % | benchmarks versionnés, critères pré-enregistrés et résultat négatif CNN documenté | `reports/benchmarks/`, REX A/B |
| Reproductibilité et implémentation | 10 % | Docker, CLI, manifestes, checksums, tests réels et persistance | `docs/`, `data/manifests/`, `make check` |
| Présentation | 10 % | démo produit réelle, rapport autonome et Writeup concis | vidéo, PDF, Writeup |

## Plan du rapport technique

1. Résumé (½ page) ;
2. Problème et utilisateur : laboratoire OoC, images bright-field, temps perdu,
   absence de traçabilité (1 page) ;
3. Données et licences : OoC Zenodo, BBBC019, BBBC038, manifestes, checksums, audit du
   tableur, split groupé, quasi-doublons (2 pages) ;
4. Méthode : architecture, registre de moteurs, moteur adaptatif, µSAM APG,
   CNN MobileNetV3, protocole `smoke`/`validation`/`final-eval` (3 pages) ;
5. Implémentation : API, CLI, Docker, tests, contrat runtime Kaggle (2 pages) ;
6. Expériences et résultats : tableaux BBBC019 et BBBC038, baselines OoC, CNN
   avec intervalles et tranches, galerie d'erreurs (4 pages) ;
7. Crédibilité et limites : fuite résiduelle, proxy de date, calibration µm
   disponible seulement avec une source utilisateur, petite taille de BBBC019,
   coût µSAM (2 pages) ;
8. Valeur applicative et perspectives : standardisation OME, comparaison de
   conditions, jumeau numérique comme horizon (1 page) ;
9. Reproduction : commandes exactes, hashes, temps attendus (1 page) ;
10. Sources, licences, déclaration des outils d'IA (1 page).

## Storyboard vidéo (5 minutes)

| Temps | Contenu |
|---|---|
| 0:00–0:30 | problème : images OoC sans contrôle qualité ni provenance |
| 0:30–2:30 | produit en direct : créer, importer, analyser, overlays, QC, export |
| 2:30–3:30 | comparaison des moteurs et benchmarks versionnés |
| 3:30–4:30 | crédibilité : split groupé, test jamais ouvert, intervalles, limites et résultat négatif assumé |
| 4:30–5:00 | reproduction en une commande et valeur pour un laboratoire |

## Technologies anticipées

| Besoin | Choix | Version vérifiée le 16/09/2026 | Décision |
|---|---|---|---|
| API | FastAPI, Uvicorn, Pydantic v2 | 0.141.1, 0.53.0, 2.13.5 | conserver ; bornes `pyproject` déjà compatibles |
| Traitement d'image | scikit-image, Pillow, NumPy | 0.26.0, 12.3.0, 2.5.3 | relever la borne `pillow<12` vers `<13` avec le lock |
| Interface | React, Vite, TypeScript 7 (compilateur natif) | 19.3.0, 8.3.0, 7.0.2 | à jour, garder l'épinglage exact |
| Entraînement | PyTorch, torchvision | 2.14.0 sur PyPI ; **2.11.0 attendu sur Kaggle** | étendre le contrat après validation locale |
| Inférence CNN expérimentale | ONNX Runtime CPU | 1.23.2 local ; 1.22.1 à l'export Kaggle | modèle opset 18 exporté, hashes vérifiés, abstention systématique |
| Segmentation zero-shot | micro-sam | 1.8.14 | moteur expérimental ; `vit_t_lm` pour un repli CPU |
| Explicabilité | pytorch-grad-cam | 1.5.7 | optionnel, avec avertissement |
| Tâches longues | file SQLite en processus (`huey` 3.4 SqliteHuey ou thread + table `jobs`) | — | éviter Redis/Celery pour un déploiement local |
| Tests navigateur | Playwright | 1.63.0 | un scénario bout en bout avant la release |
| Rapport PDF | Typst ou Quarto, figures depuis les JSON versionnés | — | aucun chiffre saisi à la main |
| Vidéo | OBS Studio, sous-titres | — | produit réel à l'écran |
| Hébergement démo | Render ou Cloud Run, sinon vidéo + Docker local | — | optionnel selon règlement |
| Archivage | release GitHub + Zenodo DOI, dataset Kaggle pour poids | — | liens valides jusqu'à fin d'évaluation |
| Formats futurs | OME-Zarr (`zarr` 3.4, `ome-zarr` 0.19, Python ≥ 3.12) | — | perspective, pas pour la soumission |

## Risques et parades

| Risque | Parade |
|---|---|
| préflight Kaggle refuse `torch 2.11` | vérifier la version dès cette semaine ; étendre le contrat après smoke local |
| quota GPU insuffisant (≈ 30 h/semaine) | risque éteint : aucun run GPU supplémentaire n'est prévu, la modélisation CNN est close |
| ouverture du test | risque éteint : le test gelé n'a jamais été ouvert et ne le sera pas ; chaque rapport de run porte `test_manifest_opened: false` |
| démo Docker qui échoue devant le jury | test machine propre, vidéo de secours, instance pré-démarrée |
| dépôt privé ou lien mort au moment de l'évaluation | checklist de liens en navigation privée, release figée |
| surpromesse scientifique | vocabulaire « exploratoire », limites dans chaque écran et chaque tableau |
| **risque réalisé** : aucun signal de qualité robuste et indépendant des métadonnées d'acquisition et de culture n'est démontré sur la validation v2 (comparateur mode × bucket de jour, post hoc : `0,8171` sur L, `0,6533` sur RGB) | résultat négatif publié tel quel, QC produit conservé sur le moteur adaptatif et les métadonnées, audit des raccourcis présenté comme contribution, aucun changement de seuil a posteriori |
| le test groupé reste optimiste (dates consécutives, même lot de puces) | analyse de sensibilité « campagnes » et phrase explicite dans le rapport : `YYMMDD` est un proxy, pas un identifiant de puce |

## Ce qu'on ne fait pas avant la soumission

- pas de VLM ni d'assistant conversationnel ;
- pas d'entraînement de ViT, pas de nouveau backbone ;
- pas de nouveau dataset au-delà d'un test externe borné sur organoïdes
  bright-field ;
- pas de prédiction de toxicité ou d'efficacité ;
- pas de refonte d'architecture : SQLite, fichiers et Docker Compose suffisent.
