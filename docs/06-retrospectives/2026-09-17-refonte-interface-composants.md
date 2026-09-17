# Refonte de l'interface : composants, lisibilité, cache nginx

Date : **17 septembre 2026**

Statut : **terminé sur la branche `frontend-ui`, vérifié dans une pile Docker
isolée sur des ports libres ; à fusionner dans `dev`**

## Objectif

Rendre l'interface maintenable et lisible en projection avant la vidéo et la
soutenance, sans changer le contrat API ni les sélecteurs du scénario
Playwright existant.

## Changements

- `App.tsx` (684 lignes) découpé en composants : `Sidebar`, `ExperimentForm`,
  `InferencePanel`, `EngineCatalog`, `ResultsSection`, `SegmentationResults`,
  `QualityResults`, `EvidencePanel`, `BenchmarkSection` ; formatage et libellés
  dans `lib/format.ts`. La vue « Comparaison des moteurs » est reprise telle
  quelle en composant.
- Résultats de segmentation : tableau par image (composantes, surface
  segmentée, aires moyenne et médiane, diamètre équivalent, seuil, polarité)
  et lien vers l'overlay en taille réelle ; « N objets » devient
  « N composantes ».
- Démonstrateur CNN : mention « non calibré » au même niveau visuel que le
  score, mode d'acquisition traduit, provenance présentée en liste
  définitions avec libellés français et hashes en monospace lisible.
- Progression d'analyse : compteur d'images et secondes écoulées dans une
  région `aria-live`, sans second `role="status"` afin de préserver le
  sélecteur `getByRole("status")` du test Playwright.
- Vocabulaire : « preuves » devient « mesures » dans le titre, le parcours et
  l'état vide ; « Preuves externes versionnées » devient « Mesures externes
  versionnées ».
- Typographie : tokens `--font-xs` (12 px), `--font-sm` (13 px) et
  `--font-md` ; 62 tailles ad hoc tokenisées, 17 blocs de texte courant
  relevés à 13 px ; couleurs secondaires ramenées à deux tokens
  (`--muted`, `--muted-on-dark`) mesurés à 4,5:1 ou mieux sur leurs fonds
  (27 couples contrôlés par script, minimum 4,96:1) ; anneaux
  `:focus-visible` explicites ; `prefers-reduced-motion` respecté pour le
  défilement, les transitions et le spinner.
- nginx : `/assets/` servi avec `Cache-Control: public, max-age=31536000,
  immutable` et `404` au lieu du repli SPA, `index.html` en `no-cache`,
  gzip, `server_tokens off`, en-têtes `X-Forwarded-*` vers l'API, en-têtes de
  sécurité déplacés dans un snippet inclus dans chaque `location` (un
  `add_header` local remplace l'ensemble hérité) ; `HEALTHCHECK` sur l'image
  frontend.

## Vérifications

- `npm run typecheck` et `npm run build` à chaque commit ;
- `nginx -t` dans `nginx:1.27-alpine` avec un hôte `backend` factice ;
- pile Docker isolée reconstruite sur des ports libres (voir ci-dessous),
  en-têtes contrôlés par `curl` et scénario Playwright complet (Axe
  `color-contrast`, plancher 12 px, exports JSON/CSV) exécuté contre cette
  pile.

## Incident de méthode à retenir

Le script `scripts/run-e2e.sh` fixe les ports `18182`/`18183`. Pendant cette
vérification, un serveur de développement Vite de l'arbre principal écoutait
déjà sur `18183` : le premier passage Playwright et les premiers `curl` ont
atteint ce serveur et non le conteneur nginx, tout en « passant ». Un test
lancé sur un port déjà occupé valide silencieusement la mauvaise cible. Le
script doit refuser de démarrer si le port est pris, ou choisir un port libre
et le transmettre à Playwright.

## Limites

- aucune image d'exemple embarquée ; la démo suppose des images locales ;
- les libellés témoin/traitement fictifs sont encore envoyés à la création
  (le schéma backend les exige) ;
- aucun test unitaire de composant ; le scénario Playwright reste la seule
  preuve automatisée du frontend.
