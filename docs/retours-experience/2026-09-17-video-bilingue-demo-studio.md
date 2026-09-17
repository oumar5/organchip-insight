# REX — Vidéo bilingue avec Demo Studio

Date : **17 septembre 2026**

## Décision

La vidéo silencieuse sous-titrée a été remplacée par deux livrables construits
depuis la même capture réelle et verrouillée : une version anglaise et une
version française. Chaque montage contient une narration locale, un
présentateur visible pendant la voix, une musique de fond sous licence et un
fichier SRT séparé.

## Chaîne reproductible

1. Docker Compose démarre le produit sur des ports isolés.
2. Playwright vérifie les empreintes des trois images publiques, exécute le
   scénario produit et enregistre une capture sans sous-titres incrustés.
3. Demo Studio produit les voix anglaise et française avec le runtime neuronal
   local Chatterbox déjà validé dans le projet Solmik. Aucun audio de référence,
   clonage de voix, service distant ou secret n'est utilisé.
4. Rhubarb génère les formes de bouche, puis Demo Studio compose la capture,
   les sept scènes, l'avatar synchronisé, les sous-titres, les voix et `Summer
   Motivational Corporate` d'Abydos_Music. La notice de licence Pixabay est
   stockée avec le fichier audio.
5. FFmpeg normalise chaque sortie en H.264 yuv420p/AAC, puis le validateur
   mesure aussi le volume moyen pour empêcher le retour d'une piste silencieuse.

Les modèles et environnements de plusieurs gigaoctets restent hors Git. Le
script accepte `ORGANCHIP_NATURAL_VOICE_ROOT` pour pointer vers un runtime local
compatible sans coupler les sources du projet à un chemin personnel.

## Résultats contrôlés

| Livrable | Durée | Format | Volume moyen | Taille |
|---|---:|---|---:|---:|
| Anglais | 198,016 s | 1280×720, H.264/AAC | −21,0 dB | 17 215 398 octets |
| Français | 198,016 s | 1280×720, H.264/AAC | −20,7 dB | 17 211 858 octets |

Les deux vidéos contiennent sept scènes de sous-titres. Les planches de contrôle
ont confirmé la lisibilité des titres, l'absence de texte coupé et la présence
du présentateur pendant les séquences narrées. Les manifestes contiennent 485
repères de bouche en anglais et 472 en français ; un contrôle rapproché sur
quatre images successives a confirmé que la bouche suit ces repères. Le jeu de
test gelé n'a jamais été ouvert.
