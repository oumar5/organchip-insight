# Tâches — chemin jusqu'au terminus

Dernière mise à jour : **17 septembre 2026**  
Branche de travail : **`dev`**  
Soumission prévue : **9 octobre 2026**

## Ce que signifie « terminé à 100 % »

Le projet est terminé pour la compétition lorsque les **phases 1 à 4** de ce
fichier sont entièrement cochées :

1. validation sur images réelles ;
2. release candidate reproductible ;
3. publication officielle ;
4. soumission Kaggle complète et vérifiée.

Les éléments de la section **Après le terminus** ne bloquent pas la soumission.
Ils représentent des améliorations ou de la recherche future. Si l'équipe est
retenue pour la finale, la phase 5 devient alors obligatoire.

## État actuel

- [x] Produit local fonctionnel : interface, API, SQLite et Docker Compose.
- [x] Import multiple PNG/JPEG/TIFF et prise en charge des TIFF 16 bits.
- [x] Galerie, visionneuse Original / Segmentation et exports JSON/CSV.
- [x] Moteur adaptatif et réserve explicite sur les composantes connexes.
- [x] Démonstrateur ONNX optionnel et abstentionniste.
- [x] Benchmarks BBBC019/BBBC038 et comparaison traçable des moteurs.
- [x] Tests backend, lint, type-check, build et Playwright synthétique.
- [x] README anglais et brouillons du rapport, du Writeup et de la vidéo.
- [x] Validation de phase 1 terminée sur les trois images réelles verrouillées.
- [ ] **Prochaine action unique : produire et geler la release candidate de la phase 2.**

## Règles pendant l'exécution

- travailler et committer sur `dev`, jamais directement sur `main` ;
- un commit cohérent par bloc, validé localement avant commit ;
- ne pousser, fusionner, publier ou taguer qu'après décision explicite du
  propriétaire ;
- ne jamais ouvrir le test gelé de classification ;
- ne jamais présenter une composante connexe comme une cellule validée.

---

## Phase 1 — Validation sur images réelles

### 1.1 Jeu de smoke test réel

- [x] Créer un manifeste contenant exactement :
  - une image OoC RGB appartenant au train autorisé ;
  - une image OoC L appartenant au train autorisé ;
  - un TIFF BBBC019.
- [x] Enregistrer pour chaque source : chemin, dataset, licence, mode et
  SHA-256.
- [x] Vérifier que les trois hashes correspondent avant toute analyse.

### 1.2 CLI robuste

- [x] Permettre à `inference.py` d'accepter des fichiers, un dossier ou le
  manifeste réel.
- [x] Refuser clairement : dossier vide, extension inconnue, lien symbolique
  et hash incorrect.
- [x] Éviter l'écrasement de deux overlays issus de fichiers ayant le même nom
  de base.
- [x] Ajouter `make test-real-images`.
- [x] Vérifier automatiquement `result.json`, les trois résultats et les trois
  overlays.

### 1.3 Interface réelle

- [x] Ajouter un parcours Playwright réel séparé ; conserver le parcours
  synthétique comme test rapide obligatoire.
- [x] Importer les trois sources dans une expérience neuve.
- [x] Vérifier la galerie, Source (aperçu) / Segmentation, les mesures et les exports.
- [x] Afficher « format source » et « aperçu PNG 8 bits » sans laisser penser
  que l'original a été converti pour l'analyse.
- [x] Vérifier que les fichiers sources ne changent pas après l'analyse.

### Preuve de fin de phase 1

- [x] `make test-real-images` passe.
- [x] Le parcours Playwright réel passe.
- [x] Les hashes avant/après sont identiques.
- [x] Les résultats restent décrits comme exploratoires.

---

## Phase 2 — Release candidate reproductible

### 2.1 Validation automatisée

- [ ] `make check` passe sur le commit candidat.
- [ ] `make test-e2e` passe avec reconstruction Docker.
- [ ] Le parcours réel de la phase 1 passe sur ce même commit.
- [ ] Le résumé frontend des benchmarks correspond aux rapports versionnés.

### 2.2 Machine propre

- [ ] Exécuter `docker compose build --pull --no-cache` depuis un réseau qui
  accède correctement à Docker Hub.
- [ ] Démarrer le projet sans images applicatives préexistantes.
- [ ] Créer une expérience, importer, analyser, redémarrer puis retrouver les
  résultats.
- [ ] Tester les exports, la galerie et la visionneuse après redémarrage.

### 2.3 Contrôles de release

- [ ] Vérifier clavier, focus, contraste, zoom navigateur et affichage mobile.
- [ ] Vérifier qu'aucun secret, chemin personnel, cache ou donnée brute n'est
  suivi par Git.
- [ ] Générer les checksums des rapports, manifestes, notebooks et éventuels
  poids distribués.
- [ ] Corriger les derniers messages incohérents ou incomplets.
- [ ] Choisir et geler le commit de release candidate.

### Preuve de fin de phase 2

- [ ] Toutes les commandes passent depuis un environnement propre.
- [ ] Le commit candidat et les checksums sont enregistrés.
- [ ] Aucun changement fonctionnel n'est ajouté après le gel, sauf correction
  bloquante validée de nouveau.

---

## Phase 3 — Décisions et publication officielle

### 3.1 Décisions du propriétaire

- [ ] Choisir la licence du code.
- [ ] Choisir la licence du bundle ONNX, ou décider de ne pas le distribuer.
- [ ] Compléter le nom de l'équipe et la liste des auteurs.
- [ ] Autoriser le push de `dev`.
- [ ] Décider de rendre le dépôt public.
- [ ] Autoriser explicitement la fusion linéaire de `dev` vers `main`.
- [ ] Valider le nom et la date du tag de release.

### 3.2 Publication

- [ ] Pousser l'état validé de `dev` après autorisation.
- [ ] Fusionner vers `main` uniquement après autorisation explicite.
- [ ] Créer le tag et la release GitHub depuis le commit validé.
- [ ] Joindre notes de release, checksums et instructions de reproduction.
- [ ] Publier les poids uniquement si licence, attribution et hashes sont
  résolus.
- [ ] Vérifier le dépôt et la release sans être connecté à GitHub.

### Preuve de fin de phase 3

- [ ] Le dépôt public, le tag et la release sont accessibles sans connexion.
- [ ] Un tiers peut retrouver le code exact et vérifier les checksums.
- [ ] La procédure d'installation ne dépend d'aucun fichier privé implicite.

---

## Phase 4 — Rapport, vidéo et soumission Kaggle

### 4.1 Rapport technique

- [ ] Relire et compléter le rapport anglais.
- [ ] Remplacer tous les champs `TO COMPLETE`.
- [ ] Ajouter les figures générées depuis les rapports versionnés.
- [ ] Vérifier les légendes, citations, licences et limites.
- [ ] Exporter le PDF et contrôler visuellement chaque page.
- [ ] Publier le PDF sur une URL publique stable.

### 4.2 Vidéo de cinq minutes maximum

- [ ] Préparer une expérience de démonstration reproductible.
- [ ] Enregistrer le produit réel en suivant le storyboard.
- [ ] Ajouter les sous-titres anglais.
- [ ] Vérifier qu'aucun secret, chemin personnel ou donnée gelée n'apparaît.
- [ ] Publier la vidéo sur une URL accessible sans connexion.

### 4.3 Writeup Kaggle

- [ ] Finaliser le résumé de 200–300 mots.
- [ ] Ajouter les liens exacts vers dépôt, release, PDF et vidéo.
- [ ] Ajouter la déclaration des outils d'IA, données, modèles et licences.
- [ ] Conserver clairement le résultat négatif CNN et les limites du comptage.
- [ ] Vérifier tous les liens dans une fenêtre privée.
- [ ] Soumettre le Writeup le **9 octobre 2026**.

### Preuve du terminus

- [ ] Le Writeup est soumis, pas seulement sauvegardé en brouillon.
- [ ] Le dépôt, la release, le PDF et la vidéo sont publics et accessibles.
- [ ] La reproduction locale fonctionne depuis la release publiée.
- [ ] Une copie locale des liens, rapports, hashes et reçus est archivée.

**Lorsque ces quatre preuves sont cochées, la version de soumission du projet
est terminée à 100 %.**

---

## Phase 5 — Seulement si l'équipe est finaliste

- [ ] Préparer une présentation de 10 minutes.
- [ ] Préparer une démonstration en direct de 3 minutes.
- [ ] Préparer une vidéo locale et une pile Docker pré-démarrée comme secours.
- [ ] Préparer les réponses sur splits, raccourcis d'acquisition, calibration,
  comptage, licences et généralisation.
- [ ] Répéter la soutenance avec chronomètre et questions contradictoires.

---

## Après le terminus — non bloquant

Ces éléments ne doivent pas retarder la release ou la soumission :

- [ ] zoom et panoramique avancés dans la visionneuse ;
- [ ] comparaison côte à côte de plusieurs expériences ;
- [ ] démo hébergée optionnelle ;
- [ ] DOI Zenodo ;
- [ ] schéma de métadonnées avec identifiants de puce et de puits ;
- [ ] calibration physique et vocabulaire de jours normalisé ;
- [ ] annotations expertes des artefacts et annotations d'instances ;
- [ ] import OME-Zarr et séries longitudinales ;
- [ ] comparaison de conditions au niveau biologique approprié.
