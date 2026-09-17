# Exigences du challenge AI4S

Sources relues le **17 septembre 2026** :

- page Kaggle officielle, source de référence pour la grille, le calendrier et
  les livrables :
  [AI4S Open Innovation: AI for Life Science](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien)
  (sous-titre officiel : « AI + Organ-on-a-Chip: Open Innovation Challenge for
  In Vitro Life Systems ») ;
- page organisateur :
  [琶洲算法大赛 — AI + 器官芯片](https://www.aicompetition-pz.com/topic_detail/26) ;
- CLI Kaggle, 16 septembre 2026 : échéance `2026-10-10 15:59:59 UTC`, soit
  17 h 59 à Paris ; catégorie `Community` ; dotation affichée 22 200 USD ;
  2 équipes inscrites ; notre équipe est inscrite.

Le challenge est le volet international du 5ᵉ 琶洲算法大赛 (Pazhou Algorithm
Competition, Guangzhou). La page officielle présente **CellShells Bioscience
Co., Ltd.** comme organisation de soutien et décrit une équipe fondatrice issue
du laboratoire de puces cérébrales de Sorbonne Université. Elle met en avant la
standardisation et la valorisation des données expérimentales ainsi que les
jumeaux numériques pilotés par l'IA. Ce contexte oriente le discours vers la
traçabilité, la standardisation et la réutilisation des données, et non vers
« un modèle de plus ».

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

La page Kaggle impose la déclaration de catégorie en tête du Writeup et
recommande un rapport autonome de 15 à 20 pages hors références et annexes.

## Inscription et équipe

- le formulaire d'inscription externe lié depuis Kaggle est obligatoire en
  plus de l'inscription au challenge ; une équipe qui ne l'a pas rempli n'est
  pas éligible ;
- une équipe compte de 1 à 5 membres et désigne une personne responsable ;
- chaque personne ne peut participer qu'à une équipe ;
- une équipe réunissant compétences IA/informatique et
  biologie/bio-ingénierie/clinique reçoit un bonus de 0,5 dans la dimension
  interprétabilité et fiabilité ; cette composition doit être déclarée dans
  le rapport.

## Grille d'évaluation officielle

| Critère officiel Kaggle | Poids | Ce que le jury regarde | Preuve du projet |
|---|---:|---|---|
| Importance du problème et impact potentiel | 30 % | importance en sciences de la vie, valeur scientifique ou pratique | workflow OoC traçable, données et sorties réutilisables, limites opérationnelles explicites |
| Approche technique et innovation | 30 % | solidité, innovation et usage pertinent de l'IA | registre de moteurs, audit des raccourcis, protocole anti-fuite, chaîne de preuves image → rapport |
| Résultats et validation | 20 % | fiabilité des résultats, comparaisons et expériences | benchmarks versionnés, intervalles, critères de promotion pré-enregistrés, résultat négatif CNN publié |
| Reproductibilité et qualité d'implémentation | 10 % | code, modèles, données et documentation testables | Docker, CLI, tests, manifestes, checksums et instructions hors service payant |
| Qualité de présentation | 10 % | clarté de la vidéo, du récit et de la démonstration | vidéo réelle ≤ 5 minutes, rapport autonome, Writeup concis |

Une grille différente relevée antérieurement sur une page secondaire est
conservée dans l'audit historique. Pour la soumission, la grille Kaggle
ci-dessus est la référence publique actuelle.

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
- [ ] formulaire d'inscription externe confirmé par le propriétaire ;
- [ ] équipe de 1 à 5 membres et responsable déclarés ;
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
