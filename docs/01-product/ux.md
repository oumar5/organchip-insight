# Expérience utilisateur

## Parcours principal

```text
Créer une expérience (modale)
  -> renseigner le contexte et, si connue, une calibration sourcée
  -> déposer plusieurs images à la fois
  -> choisir un moteur exécutable
  -> lancer l'analyse
  -> parcourir les résultats en galerie et en visionneuse zoomable
  -> comparer descriptivement deux expériences terminées
  -> exporter JSON/CSV, lire limites et provenance
```

Le parcours est linéaire et l'état d'avancement est visible en permanence dans
un indicateur à trois étapes (importer, choisir un moteur, analyser). Aucun
hyperparamètre n'est demandé avant une première sortie.

## Hiérarchie de l'interface

- barre d'application : marque, trois onglets (Espace de travail, Résultats,
  Benchmarks) et disponibilité de l'inférence ;
- rail gauche : liste des expériences persistées et bouton de création ;
- espace de travail : sélecteur d'expérience, indicateur d'étapes, zone de
  dépôt multi-images avec galerie d'aperçus, sélecteur de moteur compact avec
  détails en modale, contexte expérimental éditable et bouton d'analyse ;
- résultats : indicateurs agrégés, galerie d'images cliquables, visionneuse
  plein écran avec zoom/panoramique, bascule et vue synchronisée
  original/segmentation, tableau des mesures pixel/physiques par image,
  comparaison descriptive de deux expériences, niveau de preuve et provenance ;
- benchmarks : comparaison des moteurs générée depuis les rapports versionnés.

Les aperçus d'images sont des rendus PNG 8 bits produits par l'API pour
l'affichage seulement (étirement 1–99 percentiles des images monocanal) ; les
mesures utilisent toujours les pixels d'origine.

Modifier le contexte invalide le résultat courant : l'utilisateur relance
l'analyse afin que les exports gardent un instantané cohérent des métadonnées.
La comparaison n'est proposée qu'entre résultats terminés. Elle signale les
moteurs différents et l'absence d'une calibration nécessaire à la comparaison
physique ; elle ne réalise aucun test statistique entre conditions biologiques.

## Principes

1. **Montrer avant d'affirmer** : chaque mesure de segmentation est accompagnée
   d'un overlay consultable en grand et comparable à l'original.
2. **Moins de texte, plus d'images** : les explications longues vivent dans des
   modales et des sections repliables, pas dans le flux principal.
3. **Pas de faux résultat** : aucun chiffre simulé, aucune classe automatique
   pour le démonstrateur CNN, badge « À vérifier » systématique.
4. **Statut visible** : disponibilité de l'inférence, étape courante, import et
   analyse en cours avec progression.
5. **Langage prudent** : « exploratoire » et « composantes connexes » tant que
   la validation manque.
6. **Local-first** : les données restent dans l'environnement de déploiement.

## États à couvrir

| État | Comportement attendu |
|---|---|
| Aucune expérience | appel clair à créer une étude, modale de création |
| Expérience sans image | bouton d'analyse inactif, indicateur d'étapes sur « importer » |
| Téléversement invalide | fichier rejeté avec motif, lot conservé |
| Import en cours | barre de progression fichier par fichier |
| Analyse en cours | bouton verrouillé, compteur d'images et temps écoulé |
| Analyse terminée | bascule automatique sur l'onglet Résultats |
| Résultat rechargé | récupération depuis SQLite après redémarrage |
| Métadonnées modifiées | résultat invalidé, images conservées, nouvelle analyse requise |
| Calibration absente | valeurs en pixels uniquement, aucune conversion implicite |
| Comparaison incompatible | message explicite si les tâches diffèrent |
| Petit écran | onglets défilants, liste d'expériences via le sélecteur |

## Accessibilité minimale

- plancher typographique de 12 px, texte courant à 13 px ;
- contrastes texte/fond d'au moins 4,5:1, contrôlés par Axe dans le scénario
  Playwright ;
- labels natifs pour tous les champs, sélecteur de moteur en groupe radio ;
- focus clavier visible, mouvement réduit respecté ;
- modales natives (`dialog`) fermables par Échap, visionneuse navigable au
  clavier ;
- messages d'erreur avec `role="alert"`, bilan d'import avec `role="status"` ;
- textes alternatifs pour les aperçus et overlays ; aucune information portée
  par la seule couleur.

## Tests UX avant publication

Le test modéré doit vérifier qu'un utilisateur externe peut :

1. créer une expérience et importer plusieurs images en une fois ;
2. produire un résultat sans aide en moins de trois minutes ;
3. ouvrir une image en grand et comparer original et segmentation ;
4. zoomer et déplacer simultanément les deux vues ;
5. comparer deux résultats terminés sans confondre description et preuve biologique ;
6. retrouver la version du pipeline et les hashes du moteur ;
7. identifier au moins une limitation ;
8. relancer une analyse avec les images déjà stockées.
