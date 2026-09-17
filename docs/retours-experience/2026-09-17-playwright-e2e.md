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

## Addendum — plancher typographique et contraste

Le même scénario a été étendu le 17 septembre 2026 pour contrôler l'état final
de la page après analyse :

- parcours de chaque nœud texte visible et échec si la taille calculée est
  inférieure à `12 px` ;
- audit Axe `color-contrast`, règle WCAG 2 AA, sur tous les éléments visibles ;
- dépendance de test figée `@axe-core/playwright==4.13.0`.

Le premier audit, après relèvement mécanique des tailles, a détecté 25 textes
secondaires sous le ratio `4,5:1` : métadonnées des moteurs, libellés et unités
des métriques, légende de l'overlay et provenance. Les couleurs de ces textes
ont été assombries sans modifier les couleurs d'état.

Résultat après correction sur Chromium :

- zéro texte visible sous `12 px` ;
- zéro violation Axe `color-contrast` ;
- scénario complet toujours passant : `1 passed (3.9s)` ;
- inspection visuelle desktop effectuée sur les sources Vite courantes.

La variable `VITE_PROXY_TARGET` permet d'exécuter cet audit contre une API
temporaire sur un port dédié, sans réutiliser la base locale principale. Axe
automatise le contraste calculable mais ne remplace pas une revue complète du
clavier, des lecteurs d'écran et des différents niveaux de zoom.

## Addendum — comparaison des moteurs et nouvelle tentative sans cache

Le 17 septembre 2026, le scénario a été étendu à la vue « Comparaison des
moteurs ». Il vérifie une métrique BBBC019 issue du résumé généré et la décision
de non-promotion du benchmark BBBC038. Le parcours isolé complet, avec les
images Docker locales et un volume neuf, passe en `4,5 s`.

Une nouvelle tentative de reconstruction a ensuite exécuté :

```bash
docker compose build --pull --no-cache
```

Elle est restée bloquée avant toute étape de build applicatif, pendant la
lecture des métadonnées Docker Hub de `nginx:1.27-alpine`,
`python:3.12-slim` et `node:22-alpine`, puis a été interrompue. Ce résultat
reproduit l'incident initial et ne permet toujours pas de cocher le jalon
« machine propre ». La preuve disponible reste : code validé par `make check`,
pile et volume E2E neufs, parcours Chromium passant avec les images locales.
Le test de release doit être rejoué depuis une machine ou un réseau capable de
joindre Docker Hub.
