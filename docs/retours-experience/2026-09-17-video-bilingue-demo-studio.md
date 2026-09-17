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
3. `prepare_demo_studio_video.py` produit les voix locales avec `say` :
   `Daniel` pour l'anglais et `Thomas` pour le français. Aucun clonage de voix,
   modèle distant ou secret n'est utilisé.
4. Demo Studio compose la capture, les sept scènes, l'avatar, les sous-titres,
   les voix et `Summer Motivational Corporate` d'Abydos_Music. La notice de
   licence Pixabay est stockée avec le fichier audio.
5. FFmpeg normalise chaque sortie en H.264 yuv420p/AAC, puis le validateur
   mesure aussi le volume moyen pour empêcher le retour d'une piste silencieuse.

Le runtime optionnel Rhubarb n'étant pas installé, le présentateur est statique
et n'effectue pas de synchronisation labiale. Cette limite est visuelle et ne
modifie ni la narration, ni les sous-titres, ni les preuves produit.

## Résultats contrôlés

| Livrable | Durée | Format | Volume moyen | Taille |
|---|---:|---|---:|---:|
| Anglais | 198,016 s | 1280×720, H.264/AAC | −20,0 dB | 16 095 982 octets |
| Français | 198,016 s | 1280×720, H.264/AAC | −19,4 dB | 16 089 692 octets |

Les deux vidéos contiennent sept scènes de sous-titres. Les planches de contrôle
ont confirmé la lisibilité des titres, l'absence de texte coupé et la présence
du présentateur pendant les séquences narrées. Le jeu de test gelé n'a jamais
été ouvert.
