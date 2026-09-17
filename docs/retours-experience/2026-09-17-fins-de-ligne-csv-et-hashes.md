# Fins de ligne des CSV et hashes de provenance

Date : **17 septembre 2026**

Statut : **défaut de reproductibilité corrigé ; hashes documentés inchangés**

## Constat

Dans un clone frais du dépôt, trois tests échouaient alors qu'ils passent
dans l'arbre de travail local : `Inventory hash mismatch`,
`CNN inventory checksum mismatch` et un `manifest_sha256` différent pour le
rapport de campagnes. Toutes leurs entrées sont pourtant versionnées.

Cause : cette machine a `core.autocrlf=input`. Le module `csv` de Python
écrit des fins de ligne CRLF ; Git les normalisait en LF au commit. Les
SHA-256 verrouillés (split v1 `5ffcf7ff…`, inventaire `26fbe2f6…`) avaient été
calculés sur les octets locaux CRLF, donc les octets commités ne leur
correspondaient plus. Cinq CSV suivis étaient concernés :
`data/splits/ooc-grouped-v1.csv`, `reports/ooc-image-inventory-2026-09-16.csv`,
les deux CSV de benchmark BBBC019 et les prédictions handcrafted v1. Les
fichiers de la campagne v2 avaient été écrits en LF et n'étaient pas touchés,
ce qui explique pourquoi les runs Kaggle v2 vérifiaient leurs hashes sans
erreur.

Conséquence avant correction : toute reproduction sur machine propre, y
compris par le jury, faisait échouer les contrôles fail-closed des protocoles
v1, sans qu'aucune vérification locale ne le révèle. Les comptes de tests
annoncés dans les REX étaient exacts localement et faux dans un clone.

## Correction

- `.gitattributes` déclare `*.csv -text` : les CSV sont des artefacts hachés,
  Git ne doit jamais en modifier les octets ;
- les cinq CSV ont été réenregistrés avec leurs octets exacts
  (`git add --renormalize`) ; les blobs commités portent désormais les SHA-256
  documentés, sans changer une seule valeur de hash dans les verrous, les
  configurations ou les REX.

Vérification : après correction, `git show HEAD:data/splits/ooc-grouped-v1.csv`
a pour SHA-256 `5ffcf7ff0d69901f7362903d2532462c2758386dfbee2d6265b7a11d61b30d8c`
et l'inventaire `26fbe2f67ed71389b61c815ce5a0813524da9f2d5ac52429b839fc873aeb17a0`.

## Règles retenues

1. Tout fichier dont un hash est verrouillé est traité comme binaire par Git.
2. Le test « machine propre » se fait sur un clone frais, jamais sur l'arbre de
   travail : `git worktree add --detach <dossier> HEAD` puis la suite complète.
3. Les futurs écrivains CSV doivent fixer explicitement le terminateur de ligne
   (`newline=""` et `lineterminator="\n"`) pour que les octets ne dépendent
   plus de la plateforme ; à appliquer dans `audit_data.py`, `split_ooc.py`,
   `evaluate.py` et `train_ooc_baseline.py` sans régénérer les artefacts v1.
