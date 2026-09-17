# Roadmap vers la soumission

État au 17 septembre 2026. Calendrier officiel de l'organisateur :
soumission du Writeup jusqu'au **10 octobre 2026 (17 h 59 à Paris)**,
présélection de 20 équipes du 10 au 20 octobre, **finale en ligne avec
soutenance du 20 au 30 octobre**, résultats avant novembre. Le plan détaillé
par semaine est dans [plan-soumission.md](plan-soumission.md).

## Blocages administratifs

- [ ] dépôt GitHub public (privé au 16 septembre 2026) ;
- [ ] fichier `LICENSE` (aucune licence détectée).

## Jalon 1 — Socle démontrable

- [x] FastAPI + React + Docker ;
- [x] branche de travail `dev` ;
- [x] création et persistance SQLite des expériences ;
- [x] upload vérifié PNG/JPEG/TIFF ;
- [x] inférence zéro entraînement ;
- [x] overlays et métriques réelles ;
- [x] registre de moteurs et limites visibles ;
- [x] CLI `inference.py` ;
- [x] tests backend, type-check et build ;
- [x] documentation produit, recherche, UX et validation.

## Jalon 2 — Données et benchmark

- [x] manifeste BBBC019 Microfluidics avec checksum ;
- [x] script de téléchargement reproductible ;
- [x] métriques premier plan et rapport d'erreurs ;
- [x] benchmark d'instances BBBC038 borné, pré-enregistré et exécuté : résultat
  mitigé, 2 critères sur 3 échouent, aucune promotion produit ;
- [x] audit métadonnées du dataset OoC ;
- [x] split OoC groupé par préfixe d'acquisition ;
- [x] baseline OoC image-only avec test tenu à l'écart ;
- [x] comparaison segmentation adaptative / µSAM sur BBBC019 ;
- [x] décision produit : moteur adaptatif disponible ; µSAM conservé en
  benchmark isolé après échec de 2 critères BBBC038 sur 3 ;
- [x] audit exhaustif des quasi-doublons sur le nouveau split ;
- [x] baseline de confondants mode/résolution avant CNN ;
- [x] runtime MobileNetV3 séparant `smoke`, `validation` et `final-eval` ;
- [x] smoke CPU avec hashes d'images vérifiés et export ONNX contrôlé ;
- [x] exécution de la sonde Kaggle et validation du runtime hors ligne ;
- [x] protocole d'ablation CNN pré-enregistré (couleur/gris, résolution,
  seed, budget et règle d'arrêt) ;
- [x] validation CNN complète sur GPU Kaggle avec tranches par mode,
  résolution, lignée et jour ;
- [x] recalcul des comparateurs majorité, mode/résolution et handcrafted sur v2 ;
- [x] exécution des ablations A/B sur train/validation ; C non lancé car le
  seuil conditionnel RGB pré-enregistré n'est pas atteint ;
- [x] audit structurel des campagnes (3 jours, lignée commune) : 29 campagnes,
  270 images test exposées ;
- [x] manifeste v2 généré avec paramètres figés
  (`data/splits/ooc-campaign-v2-lock.json`), v1 conservé ;
- [ ] documentation du bruit de labels intra-groupe ;
- [x] clôture de la modélisation CNN sans ouverture du test : aucune
  configuration n'atteint le plancher de `0,65` de balanced accuracy par mode ;
  le test gelé n'a jamais été ouvert et ne le sera pas ; résultat négatif
  consigné dans le [contre-audit](audit-2026-09-17-classification-cnn.md).

## Jalon 3 — Expérience scientifique

- [x] démonstrateur ONNX expérimental du run B : abstention
  systématique, softmax non calibré affiché avec le mode d'acquisition et la
  provenance, aucune décision automatique `good`/`bad`, aucun overlay ni
  comptage rattaché ; aucun moteur CNN de contrôle qualité ; poids non
  distribués dans le dépôt, voir le [REX](retours-experience/2026-09-17-demonstrateur-cnn-onnx.md) ;
- [x] vue de comparaison des moteurs alimentée par les rapports versionnés :
  F1/IoU, intervalles, coût CPU, mémoire et décision de promotion sont générés
  depuis trois rapports verrouillés par SHA-256 ; les overlays d'erreur restent
  des artefacts de benchmark locaux, voir le [REX](retours-experience/2026-09-17-comparaison-moteurs.md) ;
- [x] champs contrôle/traitement masqués tant que l'affectation par image et
  l'agrégation par groupe ne sont pas livrées ;
- [x] export JSON complet et CSV par image depuis l'interface ;
- [x] benchmark d'instances borné (BBBC038) et réserve explicite sur le
  comptage dans l'interface ; la réserve « composantes connexes, non validées
  comme cellules » est affichée ;
- [x] analyse d'erreurs BBBC038 et cas hors distribution documentés ;
- [ ] caractéristiques morphologiques plus riches (optionnel).

## Jalon 4 — Stabilisation produit

- [x] import séparé de l'analyse, récapitulatif acceptés/rejetés, erreurs
  lisibles, verrou de sélection pendant l'analyse ;
- [x] limite nginx cohérente avec la limite par fichier ;
- [x] TIFF 16 bits, limite de pixels, reprise après échec d'analyse ;
- [x] plancher typographique de 12 px et contraste AA contrôlés dans Chromium
  par Playwright + Axe après analyse ;
- [x] file de tâches et progression retirée du périmètre : µSAM n'est pas
  promu comme moteur produit avant la soumission ;
- [x] limites de pixels et en-têtes de sécurité API/Nginx ;
- [x] parcours end-to-end navigateur local du démonstrateur CNN ;
- [x] test end-to-end Playwright automatisé sur pile Docker et volume isolés ;
- [ ] test sur machine propre CPU : deux reconstructions avec accès Docker Hub
  sont restées bloquées au chargement des métadonnées des images de base ; le
  parcours isolé passe avec les images locales, voir le [REX](retours-experience/2026-09-17-playwright-e2e.md) ;
- [ ] démo hébergée optionnelle, vidéo et Docker local en secours.

## Jalon 5 — Remise (avant le 9 octobre)

- [ ] figer données, code, résultats et citations ;
- [ ] release taguée avec checksums, DOI Zenodo optionnel ;
- [ ] rapport technique 15–20 pages selon le plan de l'organisateur ;
- [ ] vidéo ≤ 5 minutes montrant le produit réel ;
- [ ] Writeup Kaggle : catégorie, résumé 200–300 mots, liens, limites,
  déclarations IA et licences ;
- [x] brouillons anglais du rapport, du Writeup et du storyboard vidéo ; les
  liens publics, auteurs, licences, figures et export PDF restent à finaliser ;
- [ ] vérification de tous les liens en navigation privée.

## Jalon 6 — Finale (20 au 30 octobre)

- [ ] diapositives de 10 minutes et démo en direct de 3 minutes ;
- [ ] démo de secours hors ligne ;
- [ ] réponses préparées sur fuite, calibration, licences, généralisation et
  standardisation des données.

## Définition de terminé

Le projet est prêt à soumettre lorsque chaque chiffre vient d'un script versionné,
les licences sont vérifiées, Docker fonctionne sur une machine propre, les limites
sont visibles et un évaluateur peut reproduire l'inférence sans service payant.
