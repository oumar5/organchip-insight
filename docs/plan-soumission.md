# Plan de soumission et de finale

État au **16 septembre 2026**. Échéance de soumission : **10 octobre 2026,
17 h 59 à Paris**. Finale en ligne avec soutenance : **20 au 30 octobre 2026**.
Le règlement officiel est résumé dans
[competition-requirements.md](competition-requirements.md).

## Lecture stratégique

1. Le challenge n'a pas de leaderboard. Vingt équipes passent en finale ; au
   16 septembre, deux équipes sont inscrites sur Kaggle. Un dossier complet et
   valide a donc de fortes chances d'atteindre la soutenance : **la victoire
   se joue en finale**, devant un jury issu d'une société de puces
   neuro-organoïdes attachée à la standardisation et à la valorisation des
   données.
2. Les 55 % les plus lourds de la grille (innovation 30 %, achèvement et
   résultats 25 %) récompensent une chaîne complète qui tourne et une idée
   claire, pas un point de macro-F1 supplémentaire. Le travail de modélisation
   doit être borné : un run `validation` GPU, un accès test unique, puis
   intégration produit.
3. Les travaux publiés sur le même dataset utilisent des splits aléatoires
   (voir [etat-de-l-art.md](etat-de-l-art.md)). Notre protocole anti-fuite,
   l'audit des raccourcis d'acquisition et l'accès test verrouillé sont la
   contribution scientifique à mettre en avant, en plus de la plateforme.
4. Deux blocages administratifs annulent tout le reste s'ils ne sont pas
   levés : le dépôt GitHub est **privé** et n'a **aucune licence**.

## Calendrier de travail

### Semaine 1 — 16 au 22 septembre : débloquer et sécuriser

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | choisir la licence du code (Apache-2.0 recommandée : brevets, compatible MIT/BSD des dépendances), ajouter `LICENSE`, passer le dépôt en public au plus tard à la release | fichier versionné, page GitHub publique |
| P0 | exécuter la sonde autonome `notebooks/ooc-runtime-probe-kaggle.ipynb` (prête, commit `008f507`) sur Kaggle avec **GPU activé** et Internet désactivé, sans données ; versionner `runtime-report.json` ; si `torch 2.11 / torchvision 0.26`, valider localement la paire puis étendre `kaggle-runtime-contract.json` ; ne jamais relâcher le contrat sans smoke local | rapport de sonde versionné |
| P0 | figer avant les runs un protocole d'ablation : couleur vs niveaux de gris (avec recadrage commun, les deux dispositifs diffèrent de 8 px), 224 px vs ≥ 512 px ou tuiles, seeds, budget de runs et critère de sélection ; ce sont des **hypothèses** à tester sur train/validation, pas des acquis ; métrique primaire = balanced accuracy **par mode d'acquisition** comparée au raccourci, avec effectifs et classes présentes par tranche | protocole d'ablation versionné |
| P0 | outil de préparation reproductible du bundle source (hash calculable localement) ; publier le bundle et les poids ImageNet MobileNetV3-Small comme dataset Kaggle privé avec SHA-256 ; lancer les runs `validation` bornés sur GPU ; publier les tranches mode/résolution/lignée/jour et la comparaison aux baselines de raccourci (0,695) et handcrafted (0,692) | REX daté, rapports JSON, checkpoints et hashes |
| P0 | **avant les runs GPU**, décider du split v2 par « campagnes » selon la règle pré-enregistrée dans [protocole-campagnes-v2.md](protocole-campagnes-v2.md) (audit structurel fait, commit `efc0d05` : 29 campagnes à 3 jours, 21 arêtes traversant v1, 270 des 473 images test exposées avec leur propre lignée) ; si retenu, générer le manifeste v2 avec les paramètres figés, conserver v1, re-mesurer baseline handcrafted et raccourci, ne jamais choisir entre v1 et v2 sur les scores test ; documenter le bruit de labels intra-groupe (26 paires quasi-doublons à labels contradictoires) | manifeste v2 ou décision motivée, REX, hashes |
| P0 | ~~corriger les défauts qui cassent une démo Docker~~ **fait** (commit `d3938a4`, 131 tests, vérification navigateur derrière nginx) ; restent la progression de l'analyse et les groupes témoin/traité | REX [imports et TIFF](retours-experience/2026-09-16-imports-et-tiff.md) |
| P1 | export `result.json` et CSV par image depuis l'interface ; tableau par image ; nom de l'expérience dans les résultats | capture d'écran dans le REX UX |
| P1 | plancher typographique 12 px et contraste 4,5:1 sur tout texte informatif | audit contraste re-exécuté |

### Semaine 2 — 23 au 29 septembre : intégrer et comparer

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | gel de la sélection CNN (checkpoint, seuil, hashes), **un seul** run `final-eval`, reçu archivé hors Kaggle, REX | rapport final signé par hashes |
| P0 | moteur `ooc-image-quality-cnn` dans le registre : `onnxruntime` ajouté aux dépendances optionnelles de l'API, inférence CPU, seuil gelé, calibration, zone d'abstention « à vérifier », tranche par mode/résolution affichée ; si le CNN ne bat pas le raccourci, exposer à la place un QC explicite fondé sur le moteur adaptatif et les métadonnées | tests API, fiche moteur `experimental` |
| P1 | vue « Comparaison des moteurs » dans l'interface, alimentée par les rapports versionnés (`reports/benchmarks/*.json`) : F1/IoU, intervalles, coût CPU, overlays d'erreur | capture, aucun chiffre saisi à la main |
| P1 | affectation témoin/traitement à l'import, agrégats par groupe avec bootstrap par image, ou masquage explicite des champs si non livré | tests, capture |
| P1 | benchmark d'instances borné : µSAM APG sur un sous-ensemble stratifié de BBBC038 (CC0, masques d'instances), erreur de comptage et précision/rappel par objet ; dans l'interface, « composantes connexes » avec réserve explicite tant qu'aucune validation de comptage n'existe sur images OoC | rapport JSON, capture |
| P2 | Grad-CAM sur le CNN, présenté comme aide visuelle avec ses limites (voir Ivanova & Ivanovs 2026) | overlay d'attention dans le REX |
| P2 | µSAM `vit_t_lm` en moteur optionnel asynchrone si le coût CPU le permet ; sinon rester en benchmark isolé documenté | mesure temps/mémoire |

### Semaine 3 — 30 septembre au 6 octobre : figer et raconter

| Priorité | Tâche | Preuve attendue |
|---|---|---|
| P0 | test sur machine propre : `docker compose up --build`, parcours complet, CLI `inference.py`, `make check` | REX « machine propre » |
| P0 | release `v1.0.0-ai4s` : tag, checksums des modèles et rapports, archive Zenodo optionnelle avec DOI | page release |
| P0 | vidéo ≤ 5 min tournée sur le produit réel, sans musique sous droits, sous-titres anglais | lien public testé en navigation privée |
| P0 | rapport technique PDF selon le plan de l'organisateur, 15 à 20 pages, chaque chiffre relié à un fichier versionné | PDF public |
| P0 | Writeup Kaggle : catégorie, résumé 200–300 mots, liens, limites, déclarations IA et licences | brouillon relu |

### Tampon — 7 au 9 octobre

Soumettre le **9 octobre**, vérifier chaque lien sans connexion, garder le
10 octobre pour une correction d'urgence uniquement.

### 10 au 20 octobre : préparer la soutenance

- diapositives de 10 minutes : problème, démo en direct de 3 minutes, preuves,
  limites, valeur, feuille de route ;
- démo de secours : vidéo locale et instance Docker pré-démarrée ;
- questions probables : fuite de données et unité de groupe `YYMMDD`, calibration
  µm absente, différence avec Cellpose et CellProfiler, licence des poids,
  généralisation à d'autres puces ou lignées, ce qu'il faudrait pour un jumeau
  numérique, standardisation des métadonnées (OME).

## Correspondance grille officielle → preuves

| Critère | Poids | Preuve principale | Fichier ou artefact |
|---|---:|---|---|
| Innovation technique | 30 % | registre de moteurs comparables + protocole d'accès test unique + audit des raccourcis | `backend/app/ml/registry.py`, `backend/training/ooc_cnn/protocol.py`, `reports/ooc-grouped-split-v1.json` |
| Achèvement et résultats | 25 % | démo Docker complète, CNN validé et évalué une fois, benchmarks versionnés | vidéo, `reports/benchmarks/` |
| Valeur pratique | 20 % | contrôle qualité avant analyse, export traçable, comparaison de conditions | interface, `result.json`, CSV |
| Complétude | 15 % | docs, manifestes, checksums, tests, CI, reproduction en une commande | `docs/`, `data/manifests/`, `make check` |
| Interprétabilité et crédibilité | 10 % | overlays, intervalles, tranches, abstention, limites écrites | interface, REX |

## Plan du rapport technique

1. Résumé (½ page) ;
2. Problème et utilisateur : laboratoire OoC, images bright-field, temps perdu,
   absence de traçabilité (1 page) ;
3. Données et licences : OoC Zenodo, BBBC019, manifestes, checksums, audit du
   tableur, split groupé, quasi-doublons (2 pages) ;
4. Méthode : architecture, registre de moteurs, moteur adaptatif, µSAM APG,
   CNN MobileNetV3, protocole `smoke`/`validation`/`final-eval` (3 pages) ;
5. Implémentation : API, CLI, Docker, tests, contrat runtime Kaggle (2 pages) ;
6. Expériences et résultats : tableaux BBBC019, baselines OoC, CNN avec
   intervalles et tranches, galerie d'erreurs (4 pages) ;
7. Crédibilité et limites : fuite résiduelle, proxy de date, absence de
   calibration µm, petite taille de BBBC019, coût µSAM (2 pages) ;
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
| 3:30–4:30 | crédibilité : split groupé, accès test unique, intervalles, limites |
| 4:30–5:00 | reproduction en une commande et valeur pour un laboratoire |

## Technologies anticipées

| Besoin | Choix | Version vérifiée le 16/09/2026 | Décision |
|---|---|---|---|
| API | FastAPI, Uvicorn, Pydantic v2 | 0.141.1, 0.53.0, 2.13.5 | conserver ; bornes `pyproject` déjà compatibles |
| Traitement d'image | scikit-image, Pillow, NumPy | 0.26.0, 12.3.0, 2.5.3 | relever la borne `pillow<12` vers `<13` avec le lock |
| Interface | React, Vite, TypeScript 7 (compilateur natif) | 19.3.0, 8.3.0, 7.0.2 | à jour, garder l'épinglage exact |
| Entraînement | PyTorch, torchvision | 2.14.0 sur PyPI ; **2.11.0 attendu sur Kaggle** | étendre le contrat après validation locale |
| Inférence CNN produit | ONNX Runtime CPU | 1.30.0 | modèle opset 18 déjà exporté et vérifié |
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
| quota GPU insuffisant (≈ 30 h/semaine) | 20 époques MobileNetV3-Small sur 2 599 images tiennent en moins d'une heure ; garder `validation` et `final-eval` séparés |
| test ouvert deux fois | reçu archivé hors Kaggle, rapport final publié avec ses hashes |
| démo Docker qui échoue devant le jury | test machine propre, vidéo de secours, instance pré-démarrée |
| dépôt privé ou lien mort au moment de l'évaluation | checklist de liens en navigation privée, release figée |
| surpromesse scientifique | vocabulaire « exploratoire », limites dans chaque écran et chaque tableau |
| le CNN ne bat pas le raccourci mode/résolution à mode égal | publier le résultat négatif tel quel, garder le QC produit sur le moteur adaptatif et les métadonnées d'acquisition, présenter l'audit de raccourci comme contribution |
| le test groupé reste optimiste (dates consécutives, même lot de puces) | analyse de sensibilité « campagnes » et phrase explicite dans le rapport : `YYMMDD` est un proxy, pas un identifiant de puce |

## Ce qu'on ne fait pas avant la soumission

- pas de VLM ni d'assistant conversationnel ;
- pas d'entraînement de ViT, pas de nouveau backbone ;
- pas de nouveau dataset au-delà d'un test externe borné sur organoïdes
  bright-field ;
- pas de prédiction de toxicité ou d'efficacité ;
- pas de refonte d'architecture : SQLite, fichiers et Docker Compose suffisent.
