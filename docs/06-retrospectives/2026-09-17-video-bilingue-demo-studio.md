# REX — Vidéo bilingue avec Demo Studio

Date : **17 septembre 2026**

## Décision

La vidéo silencieuse sous-titrée a été remplacée par deux livrables construits
depuis deux exécutions du même scénario réel et verrouillé : une capture de
l'interface anglaise et une capture de l'interface française. Chaque montage
contient une narration locale, un
présentateur visible pendant la voix, une musique de fond sous licence et un
fichier SRT séparé.

## Chaîne reproductible

1. Docker Compose démarre le produit sur des ports isolés.
2. Playwright vérifie les empreintes des trois images publiques, exécute deux
   fois le même scénario produit et enregistre une capture anglaise puis une
   capture française, sans sous-titres incrustés. Chaque langue utilise un
   volume Docker jetable distinct afin que la seconde capture ne réutilise ni
   expérience ni résultat de la première.
3. Demo Studio produit les voix anglaise et française avec le runtime neuronal
   local Chatterbox déjà validé dans le projet Solmik. Aucun audio de référence,
   clonage de voix, service distant ou secret n'est utilisé.
4. Rhubarb génère les formes de bouche, puis Demo Studio compose la capture,
   les sept scènes visuelles, quatorze séquences narratives, l'avatar
   synchronisé, les sous-titres, les voix et `Summer
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
| Anglais | 180,117 s | 1280×720, H.264/AAC | −21,7 dB | 16 680 507 octets |
| Français | 180,011 s | 1280×720, H.264/AAC | −21,4 dB | 16 130 939 octets |

Les deux vidéos contiennent quatorze séquences de sous-titres courts réparties
sur sept scènes visuelles. La plus longue contient 83 caractères en anglais et
88 en français. Les planches de contrôle
ont confirmé la correspondance entre la langue de l'interface, la narration et
les sous-titres, la lisibilité des titres, l'absence de texte coupé et la présence
du présentateur pendant les séquences narrées. Les manifestes contiennent 383
repères de bouche en anglais et 393 en français ; un contrôle rapproché sur
quatre images successives a confirmé que la bouche suit ces repères. Le jeu de
test gelé n'a jamais été ouvert.

## Revalidation du 18 septembre 2026

Le premier montage de 3 min 18 s restait lisible, mais une phrase complète par
scène produisait des sous-titres trop hauts et la capture précédait le zoom
synchronisé ainsi que la comparaison de deux expériences. Les deux langues ont
donc été recapturées et remontées. La durée est désormais de 3 minutes et chaque
scène visuelle est racontée en deux phrases courtes successives. Ce découpage
étale le texte dans le temps sans retirer l'explication technique.

Le validateur a confirmé les deux pistes H.264/AAC, la résolution 1280×720, un
volume moyen proche de −21 dB et quatorze séquences de sous-titres par langue.
Une planche de quatorze images de la version française et une planche de huit
images par langue ont été relues manuellement : le présentateur reste visible,
les sous-titres n'occultent pas les mesures, les titres sont lisibles et les
écrans correspondent au storyboard. La nouvelle capture montre la visionneuse
source/segmentation avec zoom synchronisé et la comparaison descriptive de
deux expériences. Elle ne simule pas de calibration physique : les trois images
publiques de démonstration ne partagent pas de source documentée en µm/pixel.
