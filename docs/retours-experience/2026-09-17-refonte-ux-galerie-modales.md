# Refonte UX : onglets, galerie, visionneuse et modales

Date : **17 septembre 2026**

Statut : **livré sur `dev`, scénario Playwright complet passant dans une pile
Docker isolée (ports libres)**

## Demande

L'interface était jugée trop textuelle et difficile à utiliser : numérotation
artificielle « 01 02 03 » dans une barre latérale, formulaire et catalogue de
moteurs verbeux, résultats sans possibilité de parcourir les images en grand.
Question posée : peut-on envoyer plusieurs images à la fois et les parcourir
dans des modales ou des pages ?

## Réponse et changements

- **Plusieurs images à la fois** : oui, déjà possible ; la zone de dépôt le dit
  explicitement, accepte le glisser-déposer avec retour visuel, affiche les
  fichiers choisis en puces et une barre de progression fichier par fichier.
- **Galerie d'aperçus** : nouvelle route API `GET /experiments/{id}/images` et
  aperçus PNG 8 bits générés à la demande (`/previews/{name}`), y compris pour
  les TIFF 16 bits (étirement 1–99 percentiles, affichage seulement). Les
  images importées apparaissent en vignettes avant toute analyse.
- **Visionneuse** : toute vignette (import ou résultat) s'ouvre dans une modale
  plein écran avec bascule Original / Segmentation, navigation précédente /
  suivante au clavier et mesures de l'image affichée.
- **Trois onglets** : Espace de travail, Résultats (point vert quand un
  résultat existe, bascule automatique après analyse), Benchmarks. Plus de
  barre latérale numérotée : un rail d'expériences et un bouton « Nouvelle
  expérience » qui ouvre une modale.
- **Indicateur d'étapes** : importer → choisir un moteur → analyser, avec état
  réel (fait, en cours, à faire).
- **Moteurs** : sélecteur compact en groupe radio (nom, statut, une ligne de
  description) ; limites et raisons d'indisponibilité dans une modale
  « Détails et limites ». Les moteurs non exécutables sont visibles mais
  désactivés.
- **Résultats** : tuiles d'indicateurs, galerie cliquable avec composantes et
  surface segmentée par vignette, tableau des mesures par image repliable,
  section « Niveau de preuve, limites et provenance » ouverte par défaut.
- Bouton principal renommé « Lancer l'analyse », progression avec compteur
  d'images et secondes écoulées.

## Vérifications

- backend : 172 tests (3 nouveaux sur listing, aperçu TIFF 16 bits, refus de
  traversée) ;
- `npm run typecheck`, `npm run build` ;
- scénario Playwright mis à jour (création en modale, sélection radio du
  moteur, onglets, exports, ouverture de la visionneuse et bascule
  Original) : `1 passed (3,2 s)` dans une pile Docker reconstruite sur les
  ports 18192/18193, avec contrôle Axe `color-contrast` et plancher 12 px ;
- démo relancée sur `http://localhost:18080` avec le bundle ONNX monté.

## Limites

- aucune image d'exemple embarquée ; la démo suppose des images locales ;
- la visionneuse n'a pas de zoom ni de panoramique ;
- pas de comparaison côte à côte de deux expériences ;
- les libellés témoin/traitement fictifs sont encore envoyés à la création,
  le schéma backend les exige.
