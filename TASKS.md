# Tâches — OrganChip Insight

Dernière mise à jour : **17 septembre 2026**  
Branche de travail : **`dev`**  
Échéance interne de soumission : **9 octobre 2026**

Ce fichier est la liste opérationnelle à consulter en premier. Les protocoles,
résultats et justifications scientifiques restent dans `docs/` et
`reports/`.

## Règles de travail

- [ ] Travailler et committer sur `dev`, jamais directement sur `main`.
- [ ] Valider chaque bloc localement avant commit.
- [ ] Ne pousser, publier, fusionner ou taguer qu'après décision explicite du
  propriétaire du projet.
- [ ] Ne jamais ouvrir le test gelé de classification.
- [ ] Ne jamais présenter les composantes connexes comme des cellules validées.
- [ ] Un commit cohérent par bloc de travail.

## P0 — Prochain bloc : tests sur images réelles

- [ ] Créer un manifeste de smoke test avec trois sources réelles autorisées :
  une image OoC RGB du train, une image OoC L du train et un TIFF BBBC019.
- [ ] Enregistrer dans le manifeste le chemin, le dataset, la licence, le mode
  d'acquisition et le SHA-256 de chaque source.
- [ ] Étendre le CLI pour accepter un dossier d'images et un manifeste, sans
  dépendre d'un glob du shell.
- [ ] Refuser clairement un dossier vide, une extension inconnue, un lien
  symbolique et une source dont le hash ne correspond pas.
- [ ] Corriger le risque de collision des overlays pour deux sources ayant le
  même nom de base mais des extensions ou dossiers différents.
- [ ] Ajouter `make test-real-images` : vérification des hashes, inférence,
  présence de `result.json`, nombre de résultats et présence des overlays.
- [ ] Ajouter un parcours Playwright réel séparé et local, sans remplacer le
  scénario synthétique obligatoire.
- [ ] Vérifier dans l'interface un PNG RGB, un PNG L et un TIFF, puis contrôler
  Original / Segmentation dans la visionneuse.
- [ ] Afficher clairement dans l'interface le format de la source et préciser
  qu'un aperçu PNG 8 bits n'est pas l'image utilisée pour la mesure.
- [ ] Consigner le résultat du smoke réel sans interpréter le nombre de
  composantes comme un comptage cellulaire.

## P0 — Validation de release

- [ ] Rejouer `make check` sur l'état final.
- [ ] Rejouer `make test-e2e` avec reconstruction Docker.
- [ ] Exécuter `docker compose build --pull --no-cache` depuis un réseau qui
  accède correctement à Docker Hub.
- [ ] Tester le démarrage et le parcours complet sur une machine ou un profil
  Docker sans images applicatives préexistantes.
- [ ] Tester `inference.py` sur les trois images réelles verrouillées.
- [ ] Vérifier création, import multiple, analyse, reprise après erreur,
  galerie, visionneuse, exports JSON/CSV et benchmarks.
- [ ] Vérifier clavier, focus, contraste, zoom navigateur et affichage mobile.
- [ ] Générer un manifeste de checksums pour les rapports, manifestes,
  notebooks et éventuels poids publiés.
- [ ] Vérifier qu'aucun secret, chemin personnel, cache ou donnée brute n'entre
  dans la release.

## P0 — Décisions du propriétaire

- [ ] Choisir la licence du code.
- [ ] Choisir la licence et le mode de distribution du bundle ONNX, ou décider
  de ne pas le publier.
- [ ] Autoriser ou refuser le push de `dev`.
- [ ] Décider quand rendre le dépôt public.
- [ ] Décider explicitement de la fusion linéaire de `dev` vers `main`.
- [ ] Fixer la date et le nom du tag de release.
- [ ] Compléter le nom de l'équipe et la liste des auteurs.

## P0 — Livrables de soumission

- [ ] Relire et compléter le rapport technique anglais.
- [ ] Ajouter les figures issues des rapports versionnés et leurs légendes.
- [ ] Exporter le rapport en PDF et vérifier chaque page visuellement.
- [ ] Finaliser le Writeup Kaggle et remplacer tous les champs `TO COMPLETE`.
- [ ] Enregistrer la vidéo produit en suivant le storyboard, durée maximale
  cinq minutes.
- [ ] Ajouter les sous-titres anglais et vérifier la lisibilité à vitesse
  normale.
- [ ] Publier la vidéo sur une URL accessible sans connexion.
- [ ] Ajouter au Writeup les liens exacts vers le dépôt public, la release, le
  PDF, la vidéo et la démo optionnelle.
- [ ] Vérifier tous les liens depuis une fenêtre privée.
- [ ] Soumettre le Writeup le 9 octobre, garder le 10 octobre comme tampon.

## P1 — Finition produit

- [ ] Retirer du schéma backend les champs témoin/traitement fictifs encore
  envoyés lors de la création, ou implémenter leur affectation réelle par
  image avant de les réafficher.
- [ ] Ajouter zoom et panoramique dans la visionneuse si le temps le permet.
- [ ] Ajouter une comparaison côte à côte de deux expériences seulement si
  elle peut être terminée et testée avant le gel de release.
- [ ] Vérifier les messages français et anglais encore incohérents.
- [ ] Ajouter une capture reproductible de la vue Benchmarks pour le rapport.
- [ ] Préparer une petite expérience de démonstration reproductible sans
  donnée gelée ni information personnelle.

## P1 — Publication et archivage

- [ ] Créer la release GitHub à partir de l'état explicitement validé.
- [ ] Joindre checksums, rapport PDF, notes de release et instructions de
  reproduction.
- [ ] Publier le bundle modèle uniquement si sa licence et ses attributions
  sont résolues.
- [ ] Vérifier que le notebook Kaggle référence une release ou un commit figé.
- [ ] Créer un DOI Zenodo pour la release si le calendrier le permet.
- [ ] Archiver hors Kaggle une copie des reçus, rapports et hashes de la
  soumission.

## P1 — Préparation de la finale

- [ ] Préparer une présentation de 10 minutes.
- [ ] Limiter la démonstration en direct à 3 minutes.
- [ ] Préparer une vidéo locale et une pile Docker déjà démarrée comme secours.
- [ ] Préparer les réponses sur les splits, les raccourcis d'acquisition, la
  calibration, le comptage, les licences et la généralisation.
- [ ] Répéter la soutenance avec chronomètre et questions contradictoires.

## Après la soumission

- [ ] Définir un schéma de métadonnées stable avec identifiants de puce et de
  puits, calibration physique et vocabulaire de jours normalisé.
- [ ] Organiser une annotation experte des types d'artefacts OoC.
- [ ] Obtenir des annotations par points ou instances relues par un biologiste
  avant toute revendication de comptage cellulaire.
- [ ] Étudier OME-Zarr et l'import de séries longitudinales.
- [ ] Concevoir une comparaison de conditions avec affectation explicite par
  image et agrégation au niveau biologique approprié.

## Déjà livré

- [x] Interface React, API FastAPI, persistance SQLite et Docker Compose.
- [x] Import multiple PNG/JPEG/TIFF, TIFF 16 bits, doublons et limites de
  taille/pixels.
- [x] Galerie, aperçus, visionneuse Original / Segmentation et navigation par
  onglets.
- [x] Moteur adaptatif, overlays, mesures et réserve explicite sur le comptage.
- [x] Exports JSON et CSV par image.
- [x] Registre de moteurs et démonstrateur ONNX abstentionniste optionnel.
- [x] Benchmarks BBBC019 et BBBC038 versionnés avec coûts et limites.
- [x] Comparaison des moteurs générée depuis les rapports et leurs hashes.
- [x] Tests backend, lint, type-check, build et Playwright synthétique.
- [x] Contrôle du contraste et plancher typographique dans le parcours testé.
- [x] README anglais et brouillons du rapport, du Writeup et de la vidéo.
