# Roadmap vers la soumission

État au 17 septembre 2026. Calendrier officiel de l'organisateur :
soumission du Writeup jusqu'au **10 octobre 2026 (17 h 59 à Paris)**,
présélection de 20 équipes du 10 au 20 octobre, **finale en ligne avec
soutenance du 20 au 30 octobre**, résultats avant novembre. Le plan détaillé
par semaine est dans [plan-soumission.md](submission-plan.md).

## Blocages administratifs

- [ ] dépôt GitHub public (privé au 16 septembre 2026) ;
- [x] fichier `LICENSE` Apache-2.0 ajouté ;
- [x] équipe solo confirmée : **Ben Lol OUMAR**, responsable et unique membre ;
  aucune affiliation institutionnelle déclarée.

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
- [x] bruit de labels documenté sans relabellisation : 116 paires candidates
  dHash ≤ 8, dont 26 à labels contradictoires ; voir le
  [REX dédié](../06-retrospectives/2026-09-17-bruit-labels-ooc.md) ;
- [x] validation externe iOrganoAssay v1.1.0 exécutée une seule fois selon le
  protocole pré-enregistré : macro-F1 `0,822746`, IC 95 %
  `[0,772415 ; 0,867911]`, macro-IoU `0,717835`, contrôle `0,836929`, DSS
  `0,808564` et trois critères sur trois atteints ; résultat limité au premier
  plan d'organoïde, voir le
  [REX dédié](../06-retrospectives/2026-09-17-validation-externe-iorganoassay.md) ;
- [x] clôture de la modélisation CNN sans ouverture du test : aucune
  configuration n'atteint le plancher de `0,65` de balanced accuracy par mode ;
  le test gelé n'a jamais été ouvert et ne le sera pas ; résultat négatif
  consigné dans le [contre-audit](../02-research/audits/audit-2026-09-17-classification-cnn.md).

## Jalon 3 — Expérience scientifique

- [x] démonstrateur ONNX expérimental du run B : abstention
  systématique, softmax non calibré affiché avec le mode d'acquisition et la
  provenance, aucune décision automatique `good`/`bad`, aucun overlay ni
  comptage rattaché ; aucun moteur CNN de contrôle qualité ; poids non
  distribués dans le dépôt, voir le [REX](../06-retrospectives/2026-09-17-demonstrateur-cnn-onnx.md) ;
- [x] vue de comparaison des moteurs alimentée par les rapports versionnés :
  F1/IoU, intervalles, coût CPU, mémoire et décision de promotion sont générés
  depuis quatre rapports verrouillés par SHA-256 ; les overlays d'erreur restent
  des artefacts de benchmark locaux, voir le [REX](../06-retrospectives/2026-09-17-comparaison-moteurs.md) ;
- [x] champs contrôle/traitement masqués tant que l'affectation par image et
  l'agrégation par groupe ne sont pas livrées ;
- [x] export JSON complet et CSV par image depuis l'interface ;
- [x] benchmark d'instances borné (BBBC038) et réserve explicite sur le
  comptage dans l'interface ; la réserve « composantes connexes, non validées
  comme cellules » est affichée ;
- [x] analyse d'erreurs BBBC038 et cas hors distribution documentés ;
- [x] décision de ne pas ajouter de caractéristiques morphologiques plus riches
  avant la soumission : elles modifieraient le moteur gelé sans vérité terrain
  biologique ; piste reportée après le terminus.

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
- [x] interface découpée en composants, tableau par image, cache immuable des
  assets et repli SPA borné (branche `frontend-ui`, REX du 17 septembre) ;
- [x] refonte UX : onglets, dépôt multi-images avec galerie d'aperçus,
  visionneuse original/segmentation, modales de création et de détails ;
- [x] finition scientifique : métadonnées puce/puits/lignée/jour persistées,
  calibration facultative sourcée, conversions physiques dans les exports,
  zoom/panoramique synchronisé et comparaison descriptive de deux expériences ;
- [x] interface et réponses API bilingues français/anglais, choix persistant,
  attribut de langue du document et parcours Playwright dédié ;
- [x] documentation rangée par ordre de lecture `01` à `06`, index de chaque
  domaine et contrôle automatique de tous les liens locaux ;
- [x] audit automatique des artefacts d'expériences CNN : manifestes et hashes
  valides, sélection sur validation et test gelé jamais ouvert ;
- [x] parcours end-to-end navigateur local du démonstrateur CNN ;
- [x] test end-to-end Playwright automatisé sur pile Docker et volume isolés ;
- [x] reconstruction CPU `docker compose build --pull --no-cache`, parcours
  synthétique et réel, audit accessibilité/mobile et persistance des résultats
  après redémarrage ;
- [x] vidéos locales de secours anglaise et française de 3 min, chacune
  capturée dans la langue correspondante, sous-titrées et contrôlées ; démo
  hébergée laissée optionnelle.

## Jalon 5 — Remise (avant le 9 octobre)

- [x] figer données, code et résultats avec inventaire de checksums régénéré
  automatiquement pour chaque livrable suivi ;
- [ ] release taguée avec checksums, DOI Zenodo optionnel ;
- [x] rapports techniques candidats anglais et français de 11 pages, PDF
  déterministes contrôlés page par page, sans page vide, avec l'identité de
  Ben Lol OUMAR ;
  publication encore requise ;
- [x] vidéos candidates anglaise et française de 3 min montrant le produit
  réel, avec narration, avatar, musique sous licence, sous-titres et SRT ;
  publication encore requise ;
- [x] Writeup Kaggle : catégorie, équipe, résumé 200–300 mots, limites,
  déclarations et licence préparés ; liens publics encore requis ;
- [x] brouillons bilingues, figures, PDF et vidéos locales finalisés ;
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
