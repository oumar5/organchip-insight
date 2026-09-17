# Stabilisation produit : exports, sécurité et Docker

Date : **17 septembre 2026**

Statut : **terminé et vérifié localement**

## Objectif

Fermer les écarts produit qui pouvaient rendre la démonstration trompeuse ou
difficile à reproduire après l'intégration du démonstrateur CNN.

## Changements

Le commit `2059835` apporte :

- export JSON complet du résultat courant avec provenance ;
- export CSV avec une ligne par image et des colonnes adaptées au type de
  résultat ;
- boutons d'export dans l'interface et réponses HTTP en pièces jointes ;
- remplacement du vocabulaire « objets » par « composantes connexes » et
  réserve explicite : ce comptage n'est pas validé comme nombre de cellules ou
  de noyaux sur les images OoC ;
- masquage des champs témoin/traitement tant qu'une image ne peut pas être
  rattachée réellement à un groupe ;
- en-têtes de sécurité sur FastAPI et Nginx, avec CSP restrictive sur
  l'interface Docker ;
- overlay Compose optionnel montant le bundle ONNX en lecture seule, sans
  ajouter les poids au dépôt ni à l'image ;
- exclusion de l'état de développement `backend/data/` de Git.

## Vérifications logicielles

`make check` a réussi :

- Ruff propre ;
- **163 tests réussis, 1 ignoré** ;
- typecheck et build frontend réussis ;
- notebooks synchronisés ;
- configuration Compose valide.

Les deux images Docker ont ensuite été construites réellement. L'image backend
Python 3.12 a installé ONNX Runtime CPU `1.23.2` et l'image frontend a compilé
le bundle React sans erreur.

## Vérification Docker avec modèle

La pile isolée a été démarrée sur les ports `18082`/`18083` avec :

```bash
ORGANCHIP_QUALITY_MODEL_DIR_HOST=/chemin/absolu/vers/onnx \
ORGANCHIP_BACKEND_PORT=18082 \
ORGANCHIP_FRONTEND_PORT=18083 \
docker compose -p organchip-quality-smoke \
  -f docker-compose.yml -f docker-compose.quality.yml \
  up -d --build --wait
```

Le catalogue servi à travers Nginx a signalé le moteur
`ooc-quality-cnn-campaign-v2-gray448` comme `experimental` et `runnable: true`.
Les en-têtes observés une seule fois dans la réponse étaient :

- `X-Content-Type-Options: nosniff` ;
- `X-Frame-Options: DENY` ;
- `Referrer-Policy: no-referrer` ;
- `Permissions-Policy: camera=(), microphone=(), geolocation=()` ;
- une CSP limitée à l'origine locale, sans framing.

## Vérification navigateur

Le parcours Docker de bout en bout a été rejoué : création d'une expérience,
sélection du CNN expérimental, import de l'image de validation
`230517_47.png`, inférence CPU, affichage de l'abstention et de la provenance.
Les boutons **Exporter JSON** et **Exporter CSV** ont chacun déclenché un
téléchargement. La console navigateur ne contenait aucune erreur ni alerte.

Le test gelé n'a pas été ouvert. Les poids sont restés sur le poste local et
ont été montés en lecture seule ; ils n'ont pas été copiés dans Git ou Docker.

## Limites restantes

- l'export ne remplace pas encore une vue de comparaison des rapports de
  benchmark ;
- l'affectation contrôle/traitement reste à concevoir par image et par unité
  expérimentale avant de réafficher ces champs ;
- le benchmark d'instances BBBC038 reste nécessaire pour quantifier l'erreur
  de comptage ;
- le parcours navigateur est vérifié manuellement, mais doit encore être
  automatisé avec Playwright avant la release.
