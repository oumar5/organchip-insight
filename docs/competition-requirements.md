# Exigences du challenge AI4S

Sources :

- page organisateur, règlement complet en chinois :
  [琶洲算法大赛 — AI + 器官芯片](https://www.aicompetition-pz.com/topic_detail/26)
  (lue le 16 septembre 2026, source de référence pour la grille, le calendrier
  et les livrables) ;
- page Kaggle :
  [AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien)
  (sous-titre officiel : « AI + Organ-on-a-Chip: Open Innovation Challenge for
  In Vitro Life Systems ») ;
- CLI Kaggle, 16 septembre 2026 : échéance `2026-10-10 15:59:59 UTC`, soit
  17 h 59 à Paris ; catégorie `Community` ; dotation affichée 22 200 USD ;
  2 équipes inscrites ; notre équipe est inscrite.

Le challenge est le volet international du 5ᵉ 琶洲算法大赛 (Pazhou Algorithm
Competition, Guangzhou). Le sujet est posé par **圆壳生物 (Yuanke Bio, Suzhou)**,
société de puces neuro-organoïdes issue d'un laboratoire de Sorbonne
Université, qui met en avant la standardisation des données expérimentales,
leur valorisation en actifs et les jumeaux numériques pilotés par l'IA. Ce
profil de jury doit orienter le discours : traçabilité, standardisation,
réutilisation des données, et non « un modèle de plus ».

## Positionnement

**Catégorie déclarée : Tool & Platform.** La page organisateur accepte
explicitement « modèles, outils, plateformes, démos, agents, systèmes de
simulation, chaînes d'analyse ». La direction de référence n° 1 qu'elle cite
est exactement la nôtre : « outils intelligents de reconnaissance,
segmentation, suivi, **contrôle qualité** et analyse de phénotype pour les
images de puces ». Aucune tâche, donnée ni algorithme n'est imposé.

## Livrable unique : le Writeup Kaggle

Le Writeup est la **seule** soumission officielle. Un Writeup non soumis,
en brouillon, inaccessible ou incomplet n'est pas évalué. Il doit réunir :

1. **Vidéo de démonstration** (obligatoire) : 5 minutes maximum, seules les
   5 premières minutes sont garanties lues ; montrer le produit qui tourne,
   pas des diapositives ; lien public sans connexion ni paiement ; tous les
   médias doivent être libres de droits de rediffusion.
2. **Dépôt de code public** (obligatoire) : GitHub, GitLab ou Kaggle ; doit
   contenir code, `README.md`, fichier d'environnement (`requirements.txt`,
   `environment.yml` ou `Dockerfile`), fichiers de modèles ou procédure de
   téléchargement publique, scripts de test/inférence/évaluation/démo,
   description des entrées et sorties, étapes de reproduction. Un script
   principal explicite est recommandé (`inference.py`, `evaluate.py`,
   `run_demo.py`) avec un `main()` clair. Toute dépendance à une API ou un
   service commercial doit être documentée avec une alternative.
3. **Rapport technique** (obligatoire) : dans le corps du Writeup, en pièce
   jointe PDF ou via un lien public. Contenu attendu : titre, équipe, résumé ;
   définition du problème et utilisateur cible ; données, licences, traitement,
   qualité, conformité ; méthode et architecture ; détails d'implémentation ;
   expériences et résultats (quantitatifs, qualitatifs, cas, visualisations) ;
   **analyse de crédibilité et limites** ; valeur applicative ; reproduction ;
   sources et licences de tout modèle, bibliothèque, code ou outil d'IA.
4. **Démo en ligne** (optionnelle) : lien public sans connexion ; si elle
   dépend d'un quota gratuit ou d'un serveur temporaire, le dire et fournir
   captures, vidéo et exécution locale de secours.

Structure recommandée par l'organisateur : vidéo, dépôt, résumé de 200 à
300 mots, rapport technique, lien démo optionnel. Tous les liens doivent
rester valides jusqu'à la fin de l'évaluation.

Éléments encore à confirmer sur la page Kaggle connectée : la déclaration de
catégorie en tête de Writeup et la longueur cible du rapport (15 à 20 pages
notée lors de la lecture du 16 septembre 2026). Ils ne figurent pas sur la
page organisateur.

## Grille d'évaluation officielle

| Critère (organisateur) | Poids | Ce que le jury regarde | Preuve du projet |
|---|---:|---|---|
| Innovation technique | 30 % | nouveauté, profondeur, façon inspirante de combiner IA et OoC | registre de moteurs comparables, protocole anti-fuite à accès test unique, audit des raccourcis d'acquisition, chaîne de preuves image → rapport |
| Achèvement et résultats | 25 % | ça tourne, la démo est claire, la tâche est accomplie, les résultats sont stables | Docker en une commande, vidéo réelle, benchmarks versionnés, tests |
| Valeur pratique | 20 % | usage en R&D OoC, évaluation de médicaments, toxicologie, actifs de données, jumeau numérique, automatisation | contrôle qualité avant analyse, provenance exportable, comparaison témoin/traitement |
| Complétude de la solution | 15 % | problème clair, chaîne technique bouclée, données/méthode/expériences/code/rapport/reproduction complets | docs, manifestes, checksums, scripts |
| Interprétabilité et crédibilité | 10 % | validité scientifique, explication des sorties, limites, incertitude, éthique | overlays, intervalles, tranches par condition, langage « exploratoire » |

La grille lue sur la page Kaggle le 16 septembre 2026 était formulée
différemment (importance et impact 30 %, approche et innovation 30 %,
résultats et validation 20 %, reproductibilité 10 %, présentation 10 %). Les
deux formulations se recouvrent ; le dossier doit satisfaire l'union des deux.
Poser la question de la grille de référence sur le forum Kaggle du challenge
est une action à faible coût qui lève l'ambiguïté et montre l'engagement.

## Calendrier officiel

| Phase | Dates | Contenu |
|---|---|---|
| Soumission | 15 août → **10 octobre 2026** | Writeup Kaggle complet |
| Présélection | 10 → 20 octobre 2026 | revue experte des dossiers, **20 équipes** retenues |
| Finale | 20 → 30 octobre 2026 | **présentation et soutenance en ligne** : solution complète, innovation, valeur, perspectives |
| Résultats | avant novembre 2026 | annonce des lauréats |

Conséquence : la soumission ne clôt pas la compétition. Il faut préparer, dès
maintenant, une soutenance de 10 à 15 minutes avec démo en direct et réponses
préparées sur les limites, la fuite de données, les licences et la valeur pour
un laboratoire de puces.

## Dotation

Champion 80 000 CNY, deuxième 50 000 CNY, troisième 20 000 CNY.

## Conformité

- travail original ; modèles ouverts, bibliothèques tierces et outils d'IA
  autorisés **avec source, licence et usage explicitement indiqués** ;
- LLM, modèles de fondation et AutoML autorisés ; si une fonction centrale
  dépend d'un modèle ou d'une API, le dire dans le rapport ;
- données légales et conformes ; licence, traitement, vie privée et éthique
  décrits dans le rapport ; aucune donnée personnelle ou clinique non
  autorisée ;
- l'organisateur peut vérifier code, données, résultats, authenticité de la
  démo et originalité ;
- les lauréats participent à des actions de promotion et de transfert ;
- propriété intellectuelle selon le règlement officiel ; les auteurs gardent
  leurs droits, l'organisateur peut utiliser les matériaux pour évaluation,
  exposition et communication.

## Checklist de soumission

- [x] inscription Kaggle confirmée (CLI : `userHasEntered = True`) ;
- [ ] dépôt GitHub **rendu public** (il est privé au 16 septembre 2026) ;
- [ ] fichier `LICENSE` ajouté (aucune licence détectée par GitHub) ;
- [ ] release figée avec tag, checksums et DOI Zenodo optionnel ;
- [ ] modèles et données téléchargeables ou procédure documentée ;
- [ ] résultats recréés depuis un environnement propre ;
- [ ] rapport technique complet (PDF public + résumé dans le Writeup) ;
- [ ] vidéo publique ≤ 5 min, produit à l'écran dès la première minute ;
- [ ] Writeup avec catégorie, résumé 200–300 mots, liens, limites ;
- [ ] déclarations IA, licences et citations complètes ;
- [ ] soutenance préparée : diapositives, démo hors ligne de secours, Q/R.
