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
- [x] Release candidate reproductible de phase 2 validée et gelée sur `dev`.
- [x] Équipe de compétition fixée à une personne ; aucun bonus
  interdisciplinaire revendiqué.
- [x] Licence du code fixée à Apache-2.0 et bundle ONNX non distribué dans la
  soumission.
- [ ] **Prochaine action unique : pousser les commits techniques validés, puis
  confirmer le formulaire externe et autoriser la publication.**

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

- [x] `make check` passe sur le commit candidat.
- [x] `make test-e2e` passe avec reconstruction Docker.
- [x] Le parcours réel de la phase 1 passe sur ce même commit.
- [x] Le résumé frontend des benchmarks correspond aux rapports versionnés.

### 2.2 Machine propre

- [x] Exécuter `docker compose build --pull --no-cache` depuis un réseau qui
  accède correctement à Docker Hub.
- [x] Démarrer le projet sans images applicatives préexistantes.
- [x] Créer une expérience, importer, analyser, redémarrer puis retrouver les
  résultats.
- [x] Tester les exports, la galerie et la visionneuse après redémarrage.

### 2.3 Contrôles de release

- [x] Vérifier clavier, focus, contraste, zoom navigateur et affichage mobile.
- [x] Vérifier qu'aucun secret, chemin personnel, cache ou donnée brute n'est
  suivi par Git.
- [x] Générer les checksums des rapports, manifestes, notebooks et éventuels
  poids distribués.
- [x] Corriger les derniers messages incohérents ou incomplets.
- [x] Choisir et geler le commit de release candidate.

### Preuve de fin de phase 2

- [x] Toutes les commandes passent depuis un environnement propre.
- [x] Le commit candidat et les checksums sont enregistrés.
- [x] Aucun changement fonctionnel n'est ajouté après le gel, sauf correction
  bloquante validée de nouveau.

## Piste scientifique optionnelle — validation externe bornée

Cette piste peut renforcer la candidature, mais elle ne bloque pas le terminus
et ne doit retarder ni la publication ni le Writeup.

- [x] Rechercher des datasets externes récents et vérifier taille, licence,
  annotations et proximité avec le cas d'usage.
- [x] Décision go prise sur **iOrganoAssay v1.1.0** : CC0-1.0, archive vérifiée
  de 1,82 Go et sous-ensemble officiel de 28 triplets de validation ; protocole,
  critères, adaptation d'entrée et manifeste gelés avant calcul des scores.
- [x] Exécuter une fois le benchmark adaptatif sur les 28 triplets, sans
  modification postérieure des paramètres : macro-F1 `0,822746`, IC 95 %
  `[0,772415 ; 0,867911]`, contrôle `0,836929`, DSS `0,808564`, 1 image sur 28
  sous F1 `0,50` ; les trois critères pré-enregistrés sont atteints.
- [x] Publier le résultat complet dans les rapports JSON/CSV, la comparaison
  d'interface et le
  [REX dédié](docs/retours-experience/2026-09-17-validation-externe-iorganoassay.md),
  avec la réserve que le GT cible un organoïde et n'est pas un masque exhaustif
  d'instances ou de cellules.
- [x] Conserver le **Brain Organoid Dataset** comme alternative non exécutée :
  lancer deux validations externes ferait doublon avant la soumission.
- [x] Ne pas intégrer **MultiOrg** avant la soumission : environ 35,4 Go,
  CC-BY-NC-SA-4.0, tâche de détection d'organoïdes et non de qualité OoC.
- [x] Ne fusionner aucun de ces datasets avec la classification `good`/`bad` et
  ne pas rouvrir le test gelé ; le protocole externe et les hashes sont séparés.

---

## Phase 3 — Décisions et publication officielle

### 3.1 Décisions du propriétaire

- [x] Choisir la licence du code : **Apache-2.0**.
- [x] Ne pas distribuer le bundle ONNX dans cette soumission ; conserver le
  démonstrateur optionnel et sa procédure de montage local.
- [x] Choisir une équipe solo ; le propriétaire est l'unique membre et
  responsable.
- [x] Identité publique confirmée : **Ben Lol OUMAR**, responsable et unique
  membre ; aucune affiliation institutionnelle déclarée.
- [ ] Confirmer l'inscription obligatoire via le formulaire externe de
  l'organisateur, avec un responsable d'équipe et 1 à 5 membres.
- [ ] Pousser les commits locaux validés : `dev` est actuellement en avance sur
  `origin/dev` ; aucune publication n'est faite sans autorisation explicite.
- [ ] Décider de rendre le dépôt public.
- [ ] Autoriser explicitement la fusion linéaire de `dev` vers `main`.
- [ ] Valider le nom et la date du tag de release.

### 3.2 Publication

- [x] Préparer les notes de release candidates, les artefacts et le runbook de
  publication sans inventer les décisions du propriétaire.
- [ ] Pousser l'état validé de `dev` après autorisation.
- [ ] Fusionner vers `main` uniquement après autorisation explicite.
- [ ] Créer le tag et la release GitHub depuis le commit validé.
- [ ] Joindre notes de release, checksums et instructions de reproduction.
- [ ] Publier les poids uniquement si licence, attribution et hashes sont
  résolus.

Le dépôt peut rester privé pendant la finalisation, mais il doit devenir
public **avant** la soumission du Writeup et rester accessible sans connexion
pendant toute l'évaluation. Attendre un éventuel prix rendrait la candidature
inéligible.
- [ ] Vérifier le dépôt et la release sans être connecté à GitHub.

### Preuve de fin de phase 3

- [ ] Le dépôt public, le tag et la release sont accessibles sans connexion.
- [ ] Un tiers peut retrouver le code exact et vérifier les checksums.
- [ ] La procédure d'installation ne dépend d'aucun fichier privé implicite.

---

## Phase 4 — Rapport, vidéo et soumission Kaggle

### 4.1 Rapport technique

- [x] Relire et compléter les rapports candidats anglais et français.
- [x] Remplacer tous les champs `TO COMPLETE` par des résultats ou par une
  réserve explicite relevant du propriétaire.
- [x] Ajouter les figures générées depuis les rapports versionnés.
- [x] Vérifier les légendes, citations, licences et limites.
- [x] Exporter les deux PDF reproductibles et contrôler visuellement leurs 16
  pages en anglais et en français.
- [ ] Publier le PDF sur une URL publique stable.

### 4.2 Vidéo de cinq minutes maximum

- [x] Préparer une expérience de démonstration reproductible fondée sur le
  manifeste réel verrouillé de la phase 1.
- [x] Enregistrer un candidat reproductible de 3 min 18 s sur le produit réel et
  produire les montages anglais et français avec Demo Studio.
- [x] Ajouter narration locale, avatar, musique sous licence, sous-titres visibles
  et fichiers SRT dans les deux langues.
- [x] Vérifier durée, résolution, codecs, taille, secrets, chemins personnels et
  absence de donnée gelée.
- [ ] Publier les deux vidéos sur des URL accessibles sans connexion.

### 4.3 Writeup Kaggle

- [x] Finaliser le résumé de 200–300 mots.
- [ ] Ajouter les liens exacts vers dépôt, release, PDF et vidéo.
- [x] Ajouter la déclaration des outils d'IA, données, modèles et licences.
- [x] Conserver clairement le résultat négatif CNN et les limites du comptage.
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
