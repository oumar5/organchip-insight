# Documentation OrganChip Insight

Ce dossier est la source de vérité produit, scientifique, technique et de
soumission. Les préfixes numériques indiquent l'ordre de lecture ; ils ne sont
pas des numéros de version.

## Parcours recommandé

1. [`01-product/`](01-product/README.md) — comprendre le produit, son
   architecture, son API, l'inférence et les limites de sécurité.
2. [`02-research/`](02-research/README.md) — suivre les données, protocoles,
   validations, audits et décisions scientifiques.
3. [`03-competition/`](03-competition/README.md) — vérifier les exigences du
   concours, la stratégie Kaggle, la roadmap et la déclaration IA/licences.
4. [`04-submission/`](04-submission/README.md) — relire les rapports bilingues,
   le Writeup, les storyboards vidéo et le runbook de publication.
5. [`05-release/`](05-release/README.md) — préparer la release et vérifier ses
   checksums.
6. [`06-retrospectives/`](06-retrospectives/README.md) — consulter la mémoire
   datée des expériences, incidents et décisions.

Le [README principal](../README.md) reste le point d'entrée d'installation et
le [fichier des tâches](../TASKS.md) reste la liste opérationnelle jusqu'à la
soumission.

## Règles documentaires

- Une performance, une licence ou une capacité n'est annoncée comme acquise
  que si elle est reliée à une source, un script, un rapport ou un test
  versionné.
- Les intentions restent marquées comme `planifié`, `candidat` ou `à valider`.
- Les expériences négatives ne sont pas supprimées : elles sont conservées
  dans les retours d'expérience avec leur contexte.
- Les rapports de soumission existent en français et en anglais ; les
  documents internes peuvent rester en français lorsqu'ils servent de journal
  de décision.
- `make docs-check` vérifie tous les liens locaux et interdit les anciens
  chemins documentaires.
