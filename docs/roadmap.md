# Roadmap vers la soumission

État au 16 septembre 2026. Calendrier officiel de l'organisateur :
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
- [ ] benchmark BBBC038 (optionnel, non bloquant) ;
- [x] audit métadonnées du dataset OoC ;
- [x] split OoC groupé par préfixe d'acquisition ;
- [x] baseline OoC image-only avec test tenu à l'écart ;
- [x] comparaison segmentation adaptative / µSAM sur BBBC019 ;
- [x] décision produit : aperçu adaptatif, analyse µSAM asynchrone ;
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
- [ ] exécution des ablations A/B puis C conditionnelle sur train/validation ;
- [x] audit structurel des campagnes (3 jours, lignée commune) : 29 campagnes,
  270 images test exposées ;
- [ ] décision et génération éventuelle du manifeste v2 avec paramètres figés,
  v1 conservé ;
- [ ] documentation du bruit de labels intra-groupe ;
- [ ] ouverture unique du test après gel de la sélection et des hashes, avec
  archivage externe du reçu local avant fermeture du workspace final.

## Jalon 3 — Expérience scientifique

- [ ] moteur CNN de contrôle qualité dans le registre, inférence ONNX Runtime,
  seuil gelé, abstention « à vérifier » ;
- [ ] vue de comparaison des moteurs alimentée par les rapports versionnés ;
- [ ] rattacher chaque image à contrôle/traitement à l'import, agrégation par
  groupe avec intervalles, ou masquer les champs non livrés ;
- [ ] export CSV/JSON depuis l'interface et tableau par image ;
- [ ] benchmark d'instances borné (BBBC038) et réserve explicite sur le
  comptage dans l'interface ;
- [ ] analyse d'erreurs et cas hors distribution ;
- [ ] caractéristiques morphologiques plus riches (optionnel).

## Jalon 4 — Stabilisation produit

- [x] import séparé de l'analyse, récapitulatif acceptés/rejetés, erreurs
  lisibles, verrou de sélection pendant l'analyse ;
- [x] limite nginx cohérente avec la limite par fichier ;
- [x] TIFF 16 bits, limite de pixels, reprise après échec d'analyse ;
- [ ] plancher typographique et contraste AA sur tout texte informatif ;
- [ ] file de tâches et progression (si µSAM devient un moteur produit) ;
- [ ] limites de pixels et en-têtes de sécurité ;
- [ ] test end-to-end navigateur ;
- [ ] test sur machine propre CPU ;
- [ ] démo hébergée optionnelle, vidéo et Docker local en secours.

## Jalon 5 — Remise (avant le 9 octobre)

- [ ] figer données, code, résultats et citations ;
- [ ] release taguée avec checksums, DOI Zenodo optionnel ;
- [ ] rapport technique 15–20 pages selon le plan de l'organisateur ;
- [ ] vidéo ≤ 5 minutes montrant le produit réel ;
- [ ] Writeup Kaggle : catégorie, résumé 200–300 mots, liens, limites,
  déclarations IA et licences ;
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
