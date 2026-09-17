# Storyboard de démonstration — version française

Durée cible : **3 min 18 s**, soit 1 min 42 s de marge sous la limite de cinq
minutes. Le produit réel apparaît immédiatement. La capture française force
l'interface en français ; la capture anglaise force l'interface en anglais.
Les actions, données publiques et temps de scène restent identiques.

## Construction reproductible

`make demo-video` démarre une pile Docker isolée, vérifie les empreintes des
trois images publiques, enregistre une capture Playwright par langue, puis
utilise Demo Studio pour ajouter la narration neuronale locale, l'avatar
synchronisé par Rhubarb, la musique sous licence et les sous-titres. Le jeu de
test gelé n'est jamais ouvert. `make demo-video-check` contrôle durée, codecs,
résolution, taille, piste audio et sept scènes de sous-titres.

## Déroulé

### 0:00–0:18 — Une expérience auditable

Présenter la promesse : images, mesures, provenance et limites scientifiques
réunies dans une expérience locale.

### 0:18–0:50 — Un protocole avant l'analyse

Créer l'expérience, consigner l'objectif et importer les trois images
publiques verrouillées par empreinte. Montrer que l'import est séparé de
l'inférence.

### 0:50–1:26 — Une analyse locale fidèle à la source

Ouvrir le TIFF, distinguer l'aperçu PNG 8 bits du fichier original, lancer le
moteur adaptatif CPU sans poids appris.

### 1:26–1:56 — Des mesures aux limites explicites

Comparer source et overlay. Montrer les composantes connexes, les mesures en
pixels et la réserve qui interdit de les présenter comme des cellules validées.

### 1:56–2:16 — Des exports reproductibles

Télécharger JSON et CSV, puis afficher le panneau de preuve et de provenance.

### 2:16–2:52 — Précision et coût ensemble

Afficher BBBC019, BBBC038, iOrganoAssay, les intervalles, le temps, la mémoire,
les décisions et les hashes des rapports.

### 2:52–3:18 — Une abstention honnête

Montrer le registre des moteurs et le CNN expérimental indisponible ou
abstentionniste. Conclure sur les raccourcis d'acquisition, le test gelé fermé,
les checksums et les limites explicites.

## Contrôles avant publication

- durée inférieure ou égale à 5:00 ;
- interface, narration et sous-titres dans la même langue ;
- avatar visible pendant la narration et musique sous licence ;
- aucun secret, chemin personnel ou donnée de test gelée ;
- dépôt, rapport et vidéo accessibles sans authentification après publication.
