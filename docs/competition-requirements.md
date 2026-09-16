# Exigences du challenge AI4S

Source officielle : [Kaggle — AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien).
Vérification : 16 septembre 2026.

## Positionnement

**Catégorie déclarée : Tool & Platform**

OrganChip Insight est une plateforme reproductible d'analyse de microscopie pour
les workflows organ-on-a-chip. La segmentation est un composant ; la proposition
centrale est la chaîne de preuves de l'image au rapport.

## Livrables obligatoires

- Writeup Kaggle avec catégorie déclarée au début ;
- vidéo publique de cinq minutes maximum ;
- dépôt de code public et reproductible ;
- rapport technique autonome, idéalement 15 à 20 pages ;
- formulaire d'inscription officiel ;
- remise avant le 10 octobre 2026.

Le dépôt doit comprendre code, README, environnement, instructions de modèles,
scripts de test/inférence/évaluation, descriptions des entrées/sorties et
instructions de reproduction. `backend/inference.py` répond au besoin d'un point
d'entrée d'inférence clair.

## Grille d'évaluation

| Critère | Poids | Preuve prévue |
|---|---:|---|
| Importance et impact | 30 % | problème OoC, utilisateur, temps gagné, scénario réel |
| Approche et innovation | 30 % | registre de moteurs, provenance, comparaison et UX |
| Résultats et validation | 20 % | BBBC019/038, données OoC, baselines et erreurs |
| Reproductibilité | 10 % | Docker, CLI, API, tests, licences et checksums |
| Présentation | 10 % | workflow en trois étapes, vidéo et rapport cohérents |

## Conformité

- déclarer l'utilisation de GPT, Claude et tout autre modèle/API ;
- vérifier indépendamment le contenu généré par IA ;
- documenter licences des données, poids et bibliothèques ;
- ne pas utiliser de données personnelles ou cliniques non autorisées ;
- distinguer résultats mesurés, hypothèses et travail futur ;
- conserver une voie de reproduction sans service payant obligatoire.

## Checklist de soumission

- [ ] inscription officielle confirmée ;
- [ ] dépôt public accessible sans invitation ;
- [ ] release reproductible figée ;
- [ ] dataset et modèles téléchargeables ou procédure documentée ;
- [ ] résultats recréés depuis un environnement propre ;
- [ ] rapport 15–20 pages ;
- [ ] vidéo publique ≤ 5 min ;
- [ ] Writeup avec catégorie, résumé, liens et limites ;
- [ ] déclarations IA, licences et citations complètes.

