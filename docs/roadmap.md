# Roadmap vers la soumission

État au 16 septembre 2026. La date limite publiée est le 10 octobre 2026.

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
- [ ] benchmark BBBC038 ;
- [x] audit métadonnées du dataset OoC ;
- [x] split OoC groupé par préfixe d'acquisition ;
- [x] baseline OoC image-only avec test tenu à l'écart ;
- [x] comparaison segmentation adaptative / µSAM sur BBBC019 ;
- [x] décision produit : aperçu adaptatif, analyse µSAM asynchrone ;
- [x] audit exhaustif des quasi-doublons sur le nouveau split ;
- [x] baseline de confondants mode/résolution avant CNN ;
- [x] runtime MobileNetV3 séparant `smoke`, `validation` et `final-eval` ;
- [x] smoke CPU avec hashes d'images vérifiés et export ONNX contrôlé ;
- [ ] validation CNN complète sur GPU Kaggle ;
- [ ] ouverture unique du test après gel de la sélection et des hashes.

## Jalon 3 — Expérience scientifique

- [ ] rattacher chaque image à contrôle/traitement, puce, puits et temps ;
- [ ] agrégation par unité expérimentale ;
- [ ] comparaison avec tailles d'effet et intervalles ;
- [ ] caractéristiques morphologiques plus riches ;
- [ ] export CSV/JSON et rapport ;
- [ ] analyse d'erreurs et cas hors distribution.

## Jalon 4 — Stabilisation produit

- [ ] file de tâches et progression ;
- [ ] limites de pixels et sécurité renforcée ;
- [ ] tests end-to-end navigateur ;
- [ ] test sur machine propre CPU ;
- [ ] déploiement public ou démonstration enregistrée de secours ;
- [ ] audit accessibilité et performance.

## Jalon 5 — Remise

- [ ] figer données, code, résultats et citations ;
- [ ] rapport 15–20 pages ;
- [ ] vidéo ≤ 5 minutes ;
- [ ] dépôt public et release ;
- [ ] Writeup Kaggle ;
- [ ] présentation de finale.

## Définition de terminé

Le projet est prêt à soumettre lorsque chaque chiffre vient d'un script versionné,
les licences sont vérifiées, Docker fonctionne sur une machine propre, les limites
sont visibles et un évaluateur peut reproduire l'inférence sans service payant.
