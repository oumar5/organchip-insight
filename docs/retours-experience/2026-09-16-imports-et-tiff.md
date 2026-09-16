# Imports robustes et TIFF 16 bits

Date : 16 septembre 2026. Ce bloc répond aux défauts B1–B4 et F1–F5 de l'audit,
dans le périmètre du déploiement local à un processus API.

## Changements

- lecture commune produit/benchmark, sans écrêtage des TIFF gris 16 bits ;
- moteur versionné `adaptive-segmentation-1.1.0`, chemin 8 bits inchangé ;
- décodage réel avant acceptation, limite de pixels, refus des piles et pixels
  flottants ; limite par défaut 16 777 216 pixels et 25 Mio par fichier ;
- requêtes d'import unitaires dans l'interface, nginx 26 Mio pour garder une
  marge multipart ; limites API effectivement transmises par Compose ;
- bilan accepté/rejeté/doublon et motifs de rejet ; déduplication SHA-256
  dans une expérience, y compris sous un nom différent ;
- import distinct de l'inférence, reprise limitée aux fichiers restants ;
- passage en `failed` après exception, images conservées, récupération des
  analyses interrompues au démarrage ;
- rejet des imports et relances durant une analyse, sélection verrouillée
  dans l'interface ; réponses obsolètes de résultats ignorées ;
- résultat invalidé seulement après un ajout effectif, nom de l'expérience
  visible, overlays avec URL versionnée par date du résultat ;
- noms UTF-8 bornés avant stockage, connexions SQLite fermées ;
- candidats indisponibles retirés du sélecteur et conservés dans le catalogue.

## Preuves

`make check` : 110 tests réussis, 1 ignoré ; lint, types, build frontend,
notebook et configuration Compose valides. Les 16 nouveaux tests couvrent
les TIFF little/big endian, équivalence 8/16 bits, pixels excessifs,
multipages, JPEG tronqué, import partiel, taille, noms longs, doublons,
reprise après exceptions, invalidation et récupération au redémarrage.

Vérification navigateur sur les conteneurs reconstruits, derrière nginx à
`http://localhost:18080`, le 16 septembre 2026 :

| Scénario | Observation |
|---|---|
| Deux TIFF synthétiques équivalents 8/16 bits + PNG corrompu | 2 acceptés, 1 rejeté avec motif ; 1 objet par TIFF, 2 au total |
| Réimport du TIFF 16 bits | aucun ajout ; l'expérience garde ses 2 images |
| Trois TIFF de 10 485 882 octets chacun | 3 acceptés, 0 rejet ; lot total supérieur à 25 Mio |
| Analyse de ce lot synthétique | 1, 2 et 3 objets, soit 6 au total |
| Vue 320 pixels | largeur du document égale à 320, pas de débordement horizontal |
| Console navigateur | aucune erreur JavaScript capturée |

Les deux expériences « Vérification » sont conservées dans le volume local.
Les données antérieures sont conservées. Le service utilise les ports
18000/18080 ; lors d'une reconstruction, les passer explicitement si le fichier
`.env` ne les fixe pas, car le port par défaut 8000 est occupé sur cette machine.

## Limites

Ces images synthétiques valident le logiciel, pas le comptage cellulaire réel.
Les intensités 16 bits sont rapportées à 65535, sans calibration du capteur.
Les masques et métriques historiques ne sont pas recalculés ni remplacés.
L'analyse reste synchrone et la coordination suppose un processus API unique.
Les très longs lots peuvent encore dépasser le timeout HTTP ; une file de
tâches persistante constitue un bloc distinct. La déduplication est binaire,
pas perceptuelle, et ne remplace pas l'audit scientifique du dataset.
