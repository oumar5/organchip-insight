# Parcours Playwright end-to-end — 17 septembre 2026

## Objectif

Transformer le parcours navigateur déjà vérifié manuellement en une preuve
automatisée et reproductible, sans utiliser les données OoC ni le modèle CNN.

## Scénario livré

Le test Chromium exécute dans l'ordre :

1. démarrage de l'application via Nginx et vérification de la disponibilité de
   l'inférence ;
2. création d'une expérience unique ;
3. sélection explicite du moteur `adaptive-segmentation-v1` ;
4. import d'un PNG 64×64 synthétique embarqué dans le test ;
5. analyse et affichage de l'overlay ;
6. présence de « composantes connexes » et de la réserve scientifique OoC ;
7. téléchargement puis lecture de l'export JSON ;
8. téléchargement puis lecture de l'export CSV ;
9. absence d'erreur JavaScript et de réponse HTTP 4xx/5xx inattendue.

Le 404 de `/experiments/{id}/results` avant la première analyse est explicitement
autorisé : il représente l'état attendu « aucune analyse terminée » et est déjà
géré par l'interface. Toute autre réponse en erreur fait échouer le test.

## Isolation

`scripts/run-e2e.sh` utilise :

- le projet Compose `organchip-e2e` ;
- les ports backend/frontend `18182` et `18183` ;
- un volume SQLite propre au run ;
- un `trap` qui arrête les conteneurs et supprime le volume, même en cas d'échec.

Le scénario ne modifie donc ni la pile de démonstration, ni ses expériences.

## Commandes

Première installation du navigateur :

```bash
npm --prefix frontend exec playwright install chromium
```

Run normal, avec reconstruction Docker :

```bash
make test-e2e
```

Un repli hors ligne existe pour un poste qui possède déjà des images locales
correctement étiquetées :

```bash
ORGANCHIP_E2E_SKIP_BUILD=1 make test-e2e
```

Ce repli ne prouve pas une reconstruction depuis un cache vide ; il vérifie le
parcours applicatif dans une pile et une base de données neuves.

## Résultat observé

- Chromium géré par Playwright : `153.0.8010.12` ;
- Playwright : `1.63.0` ;
- test : `1 passed (2.5s)` ;
- conteneurs, réseau et volume E2E supprimés à la fin ;
- JSON et CSV téléchargés et relus dans le test.

La première tentative de reconstruction a construit le backend puis est restée
bloquée sur la récupération des métadonnées Docker Hub pour `node:22-alpine` et
`nginx:1.27-alpine`. Deux `docker pull` directs ont reproduit le blocage. Le run
fonctionnel a donc utilisé le repli hors ligne avec les images locales déjà
validées. Cela clôt le scénario Playwright, mais **pas** le test ultérieur sur
une machine réellement propre avec accès au registre.

## Incidents utiles rencontrés

1. le libellé « Moteur » entrait en collision avec « Moteur actif et
   candidats » ; le test cible désormais le `select` de `.field-grid` ;
2. l'assertion française attendait « non validé » alors que l'interface affiche
   « pas validé » ; l'assertion suit le texte réel ;
3. une écoute naïve des erreurs console prenait le 404 pré-analyse pour un
   défaut ; le test contrôle maintenant les URL et statuts HTTP précisément.

## Limites et suite

- un seul navigateur et un seul parcours heureux ;
- pas de test de reprise après échec ni du CNN optionnel ;
- pas de mesure automatique du contraste ;
- la reconstruction Docker sur machine propre reste un jalon séparé ;
- le scénario doit être ajouté au CI seulement après décision sur le coût des
  minutes et la disponibilité de Docker/Chromium sur le runner.
