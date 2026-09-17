# Finition scientifique : métadonnées, calibration et comparaison

Date : 17 septembre 2026  
Périmètre : produit local FastAPI + React, sans modification des moteurs gelés

## Question

Comment améliorer l'inspection et la traçabilité du produit avant soumission
sans transformer le prototype local en plateforme SaaS ni créer de nouvelle
revendication biologique ?

## Décision

Quatre améliorations bornées ont été intégrées :

1. métadonnées persistantes de puce, puits, lignée et jour de culture ;
2. calibration facultative en µm/pixel, acceptée uniquement avec une source ;
3. zoom et panoramique communs aux vues source et segmentation, avec mode côte
   à côte synchronisé ;
4. comparaison descriptive de deux expériences terminées.

L'authentification, le stockage cloud, la file de tâches, OME-Zarr et les tests
biologiques entre conditions restent hors du périmètre de soumission.

## Garanties de traçabilité

- une migration SQLite additive conserve les bases existantes ;
- modifier le contexte invalide le résultat mais conserve les images ;
- l'analyse copie un instantané des métadonnées dans son résultat JSON ;
- les valeurs pixel ne disparaissent jamais ;
- avec une calibration, le CSV ajoute les aires en µm² et le diamètre en µm ;
- sans calibration, aucune conversion physique n'est affichée ou inventée ;
- la comparaison avertit si les tâches ou moteurs diffèrent et si une échelle
  physique manque.

## Vérifications exécutées

- Ruff : réussi ;
- backend : 189 tests réussis, 1 test conditionnel ignoré ;
- TypeScript et build Vite : réussis ;
- Playwright sur pile Docker isolée : 5 scénarios réussis, 2 conditionnels
  ignorés ;
- le parcours synthétique vérifie création calibrée, exports physiques, zoom,
  vue synchronisée et comparaison de deux expériences.

## Limite maintenue

La comparaison est descriptive. Elle n'établit ni indépendance des unités
biologiques, ni significativité statistique, ni effet contrôle/traitement. La
calibration est une donnée fournie par l'utilisateur : OrganChip Insight ne la
déduit pas des images.
