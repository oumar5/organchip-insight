# Expérience utilisateur

## Parcours principal

```text
Créer l'expérience
  -> sélectionner le moteur
  -> importer les images
  -> lancer l'inférence
  -> contrôler les overlays
  -> examiner les métriques et limites
```

Le parcours est volontairement linéaire. Un utilisateur ne doit pas choisir un
hyperparamètre avant d'avoir vu une première sortie.

## Hiérarchie de l'interface

- barre latérale : navigation et expériences persistées ;
- en-tête : promesse et disponibilité du service ;
- carte 01 : contexte et groupes de l'expérience ;
- carte 02 : moteur, fichiers et action principale ;
- résultats : mesures, overlays, provenance et avertissements.

## Principes

1. **Montrer avant d'affirmer** : chaque mesure de segmentation est accompagnée
   d'un overlay.
2. **Progressive disclosure** : la configuration scientifique avancée apparaît
   après la première baseline.
3. **Pas de faux résultat** : aucun chiffre simulé dans le produit.
4. **Statut visible** : disponible, en cours, terminé ou en échec.
5. **Langage prudent** : “exploratoire” tant que la validation manque.
6. **Local-first** : les données ne quittent pas l'environnement par défaut.

## États à couvrir

| État | Comportement attendu |
|---|---|
| Aucune expérience | appel clair à créer une étude |
| Expérience sans image | bouton d'inférence inactif ou message explicite |
| Téléversement invalide | fichier rejeté sans casser le lot |
| Analyse en cours | action bloquée, indicateur de progression |
| Analyse terminée | métriques, overlays et provenance visibles |
| Résultat rechargé | récupération depuis SQLite après redémarrage |
| Petit écran | navigation compacte et cartes empilées |

## Accessibilité minimale

- contrastes texte/fond élevés ;
- labels natifs pour tous les champs ;
- focus clavier visible ;
- messages d'erreur avec `role="alert"` ;
- textes alternatifs pour les overlays ;
- aucune information transmise uniquement par la couleur.

## Tests UX avant publication

Le test modéré doit vérifier qu'un utilisateur externe peut :

1. expliquer la différence entre baseline et modèle validé ;
2. produire un résultat sans aide en moins de trois minutes ;
3. retrouver la version du pipeline ;
4. identifier au moins une limitation ;
5. relancer une analyse avec les images déjà stockées.

