# REX — Finalisation bilingue et documentaire

Date : **17 septembre 2026**

## Constat initial

Le produit était utilisable en français, mais la candidature annonçait deux
langues sans offrir un parcours logiciel entièrement bilingue. Les PDF anglais
et français étaient cohérents sur le fond, mais leur générateur imposait trop
de sauts de page : des titres se retrouvaient seuls et plusieurs pages
paraissaient vides. La vidéo anglaise utilisait enfin une narration anglaise
sur une capture d'interface française.

## Corrections

1. Un contexte de langue français/anglais persistant a été ajouté au frontend.
   Il contrôle l'interface, les formats de nombres et de dates, les libellés
   scientifiques connus et l'attribut `lang` du document.
2. Le client transmet `Accept-Language`. L'API localise les erreurs destinées à
   l'utilisateur et les métadonnées du registre de moteurs, puis renvoie
   `Content-Language`.
3. Un parcours Playwright vérifie le français par défaut, le basculement vers
   l'anglais et la persistance après rechargement.
4. Le générateur PDF utilise des sauts conditionnels pour garder les titres
   avec leur contenu. Les deux rapports sont passés de 16 à 11 pages A4 sans
   retirer de résultat, et chaque page a été rendue puis inspectée.
5. La chaîne vidéo enregistre désormais une capture par langue dans deux
   volumes Docker jetables et indépendants avant de les transmettre séparément
   à Demo Studio.
6. La documentation est classée par ordre de lecture dans six domaines. Un
   contrôle automatique refuse tout lien local cassé et tout ancien chemin.
7. Un audit automatique vérifie les artefacts CNN : présence, taille et hash
   des fichiers manifestés, parité ONNX, sélection fondée uniquement sur la
   validation et absence de reçu d'accès au test gelé.

## Décision

Le français et l'anglais sont deux présentations du même produit et des mêmes
preuves, pas deux variantes scientifiques. Les rapports restent strictement
alignés par section. Les artefacts d'expériences restent hors Git lorsqu'ils
sont volumineux ; leur intégrité et les décisions qu'ils soutiennent sont en
revanche contrôlées par un script versionné.

La réorganisation ne supprime aucun retour d'expérience : les échecs et les
changements de direction restent nécessaires à la crédibilité de la
candidature.
