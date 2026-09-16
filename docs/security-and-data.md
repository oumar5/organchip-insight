# Sécurité, données et conformité

## Modèle de menace du MVP

Le déploiement actuel est prévu pour un poste local ou une démonstration
contrôlée. Il ne comprend pas d'authentification et ne doit pas être exposé
directement sur Internet.

## Protections présentes

- noms de fichiers réduits à leur nom de base ;
- nom stocké préfixé par un identifiant aléatoire ;
- extensions autorisées limitées ;
- contenu vérifié par Pillow ;
- taille maximale configurable ;
- artefacts servis uniquement depuis le dossier de l'expérience ;
- aucun appel à un service externe pendant l'inférence par défaut ;
- base SQLite et images dans un volume local.

## Protections nécessaires avant déploiement public

- authentification et séparation par utilisateur ;
- quotas de taille et de nombre de fichiers ;
- analyse antivirus et limites de pixels décompressés ;
- exécution asynchrone avec timeouts ;
- HTTPS, journaux structurés et politique de rétention ;
- sauvegardes et suppression vérifiable ;
- en-têtes de sécurité et restriction CORS stricte.

## Données interdites au MVP

- données nominatives ;
- images cliniques non anonymisées ;
- datasets sans licence ou consentement vérifiable ;
- secrets dans les noms de fichiers ou métadonnées ;
- données dont la redistribution publique est interdite pour la remise.

## Registre de provenance minimal

Chaque dataset intégré doit avoir : source, version, date d'accès, licence,
checksum, citation, schéma de métadonnées, unité de split et restrictions.

