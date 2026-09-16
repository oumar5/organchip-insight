# Workflow Kaggle et GitHub

État au 16 septembre 2026 : la [sonde privée v1](retours-experience/2026-09-16-sonde-kaggle.md)
a tourné sur GPU et le smoke privé complet passe, y compris l'export ONNX. Les
datasets privés train/validation, test gelé et ressources hors ligne sont créés.
Le notebook d'entraînement est relié à `dev`. Internet doit rester désactivé
pendant les runs.

## Organisation recommandée

Un seul dossier de préparation **local**, mais des entrées Kaggle distinctes :

| Entrée privée | Contenu | Pourquoi séparer |
|---|---|---|
| Images train/validation | Images sélectionnées par le manifeste retenu, chemins relatifs conservés | Gros volume stable : ne pas le transférer à chaque correction de code |
| Source et protocole | Code CNN filtré, configuration, manifestes autorisés, environnement et provenance | Petit volume versionné à chaque changement pertinent |
| Ressources du modèle | Poids ImageNet, provenance/licence, puis dépendances hors ligne approuvées et hashes | Ressources réutilisables, distinctes du code et des images |
| Test gelé | Images et manifeste de la partition test campagne v2 | À ne joindre qu'après le gel de la sélection |

Le notebook est un objet Kaggle séparé, **pas un quatrième dataset**. Pour la
sonde actuelle, il n'utilise aucune entrée. Un `Quick Save` ou un push GitHub
enregistre le notebook, mais ne garantit pas la publication de
`/kaggle/working`. La validation campagne v2 l'a confirmé : la CLI ne récupérait
que la log de la version, pas les 87,3 MiB d'artefacts du workspace. Les sorties
doivent donc être archivées explicitement avant l'arrêt de la session.

On pourrait réunir code et ressources pour n'avoir que deux datasets. Ce n'est
pas interdit, mais le code change plus souvent que les poids et les dépendances.
La séparation en trois entrées est recommandée ; les chemins exacts sont des
paramètres. Le notebook actuel prévoit déjà trois racines (source, images,
poids) ; regrouper les poids et de futures dépendances suppose d'adapter les
chemins et le bootstrap, pas de prétendre que c'est déjà disponible.

Le test final reste dans une entrée distincte, jointe uniquement après gel des
choix et autorisation de l'évaluation finale. L'organisation finale précise doit
respecter les besoins de provenance du CLI ; le bundle de sélection finale sera
préparé seulement après le run de validation retenu.

Chemins montés retenus pour la validation campagne v2 :

```text
/kaggle/input/datasets/oumarbenlol/organchip-insight-source-campaign-v2/organchip-insight
/kaggle/input/datasets/oumarbenlol/organchip-train-validation-v2/train-validation/images
/kaggle/input/datasets/oumarbenlol/organchip-cnn-offline-resources-v1/resources
```

La version source privée publiée après le durcissement de provenance est la
version 5. Son manifeste logique porte le SHA-256
`2fef17b49d73c5b8480bca4afeb97e5259a61871baeab7559dbcaf4b4b8ffcba` et le
commit source complet `acc92e96afad74c048c5764de6db0dc864538c4b`. Le ZIP de
transport porte le SHA-256
`05d3fd7faeb0f3858aa5fa5db824f17acb3c73ab42a8ce7a7e9fd926b111701a`.
Le notebook vérifie le manifeste logique et le commit avant toute reprise ou
nouvelle exécution.

Le notebook refuse un smoke ou une validation si
`/kaggle/input/datasets/oumarbenlol/organchip-frozen-test-v2-zip` est présent.

## Conservation des sorties

La cellule `archive` du notebook appelle le CLI partagé après le gel de la
validation. Le nom est dérivé du `RUN_ID` :

```text
/kaggle/working/{RUN_ID}-artifacts.zip
```

Le ZIP est déterministe dans un même environnement : ordre et dates internes
fixes, dossier racine unique, permissions normalisées et
`artifact-manifest.json` contenant taille et SHA-256 de chaque fichier. Le
manifeste lit le `run_id` dans le rapport scientifique et enregistre aussi le
commit source, le SHA-256 du bundle, la configuration et le rapport racine. Son
SHA-256 et les empreintes des fichiers sont l'identité canonique ; le hash du
ZIP est seulement un contrôle de transport, car DEFLATE peut varier entre
versions de zlib. Il contient uniquement le dossier du run — checkpoints,
rapports, prédictions, figures, historique, gel et export ONNX — et jamais les
images sous `/kaggle/input`. Le CLI refuse les liens symboliques, un ZIP vide,
une destination située dans le run et l'écrasement silencieux d'une archive.

En `final-eval`, le reçu d'accès test est d'abord copié dans le dossier du run,
puis le rapport final, les prédictions, la figure et ce reçu sont archivés sous
le même contrat. L'archive finale n'est donc plus une opération manuelle séparée.

Procédure obligatoire :

1. exécuter la cellule `archive` après l'export ONNX et le gel ;
2. noter la taille et le SHA-256 affichés ;
3. télécharger le ZIP depuis le lien de cellule ou le panneau **Output** ;
4. vérifier localement avec `shasum -a 256 NOM_DU_ZIP` ;
5. déposer la copie locale dans `data/experiments/ooc-cnn/`, chemin ignoré par
   Git ;
6. créer une version privée Kaggle Model pour les artefacts déployables, après
   décision explicite sur leur licence, et une version privée Kaggle Dataset
   pour le bundle complet de preuve ;
7. enregistrer leurs identifiants, versions et SHA-256 dans le REX et le registre
   de modèles.

Commande de secours depuis une console séparée si le noyau du notebook ne
répond plus :

```bash
make cnn-archive \
  CNN_RUN_DIRECTORY=data/experiments/ooc-cnn/ID_DU_RUN \
  CNN_ARCHIVE_OUTPUT=/kaggle/working/ID_DU_RUN-artifacts.zip \
  CNN_SOURCE_BUNDLE_SHA256=SHA256_DU_BUNDLE \
  CNN_SOURCE_COMMIT=COMMIT_COMPLET
```

GitHub reste la source du code, du notebook **propre et non exécuté**, des
configurations, de la documentation et des manifests légers. Kaggle Models
conserve les binaires destinés à l'inférence (`onnx`) et à la reprise
(`pytorch`). Le Dataset privé conserve l'historique complet du run. Le ZIP local
est une sauvegarde secondaire, pas la source de vérité du code.

Tant que la licence des poids n'est pas décidée, le conteneur Kaggle Model peut
rester privé et vide : on ne crée aucune variation, car Kaggle exige une licence
pour celle-ci. Le Dataset privé, marqué `unknown`, reste alors la source de
preuve binaire sans prétendre accorder des droits de réutilisation.

## Reprendre une validation interrompue

La persistance Kaggle conserve les fichiers, mais la reprise reste explicite et
vérifiée par le moteur. Après chaque époque terminée, le run contient
`last-checkpoint.pt`. Pour reprendre, conserver le même `RUN_ID` et définir :

```python
RESUME_VALIDATION_FROM = (
    "data/experiments/ooc-cnn/kaggle-validation-campaign-v2/last-checkpoint.pt"
)
```

Le notebook réutilise alors le workspace persistant sans recopier le projet et
vérifie ses fichiers contre le bundle source attaché. Le CLI contrôle aussi les
hashes du code, de la configuration, du manifeste, des poids initiaux et du
meilleur checkpoint avant de restaurer modèle, optimiseur, scheduler, AMP,
historique, patience et états aléatoires. Une reprise est refusée après création
du rapport final. Si l'interruption arrive au milieu d'une époque, seule cette
époque est recommencée.

Ne jamais envoyer le dépôt entier : exclure `.git`, `.env`, clés, caches,
expériences personnelles et artefacts de test. L'outil de staging utilise une
liste autorisée de fichiers, vérifie les hashes et exclut l'inventaire historique
complet qui contient des lignes test. La provenance des prochains runs repose
sur le manifeste train/validation v2 autorisé. Les hashes des anciens runs
restent inchangés et continuent d'identifier leurs bundles historiques.

Créer un dataset dans son compte ne signifie pas qu'il contient des « données
personnelles » : les images OoC ici viennent du dataset de recherche déjà acquis.
Toute future image personnelle reste hors de ce transfert sans accord spécifique.
Conserver la citation, la licence et les droits de redistribution des sources.

## GitHub n'est pas une synchronisation implicite

1. Un `git commit` enregistre localement. GitHub ne reçoit rien sans `git push`.
2. Un import de notebook GitHub vers Kaggle crée une copie ; ce n'est pas une
   garantie que chaque futur commit relance ou actualise le notebook.
3. « Link to GitHub » est une fonctionnalité de sauvegarde de notebooks vers
   GitHub, distincte du déploiement GitHub vers Kaggle.
4. Pour certains datasets importés de GitHub, Kaggle propose des mises à jour
   périodiques. Ce mécanisme n'est ni un déclenchement à chaque commit ni une
   garantie de versions immuables pour l'entraînement.

Sources officielles : [import de notebooks](https://www.kaggle.com/product-announcements/572642),
[sauvegarde vers GitHub](https://www.kaggle.com/product-feedback/295170),
[datasets et mises à jour](https://www.kaggle.com/docs/datasets),
[CLI des notebooks](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md).

Workflow retenu pour l'instant : développement et tests sur `dev`, commits locaux,
push sur `dev` quand demandé, préparation d'un bundle rattaché à un commit précis,
puis création/version Kaggle explicitement autorisée. `kaggle kernels push`
**lance aussi une exécution** : ce n'est pas une simple sauvegarde passive.
Pas de workflow automatique ajouté sur `dev`, pas de push/fusion sur `main`.
La publication de la release et le choix de licence restent des décisions séparées.

## Ordre concret

1. Archiver le rapport GPU réel (fait pour la sonde v1).
2. Utiliser le bootstrap ONNX Runtime hors ligne vérifié du notebook, puis
   confirmer le préflight privé sans accès réseau avant l'entraînement.
3. Générer et contrôler le manifeste v2 (fait : 2 056/509/507 images), puis
   figer les ablations train/validation.
4. Construire les trois bundles locaux et leurs hashes. Afficher leur contenu,
   leur taille, leur provenance et les réglages de confidentialité avant upload.
5. Sur confirmation, créer les datasets privés puis lancer le notebook de
   validation avec des versions identifiées. Ne pas importer deux copies du même
   notebook, l'une manuellement et l'autre par la CLI.
6. Exécuter la cellule `archive`, télécharger le ZIP et vérifier son SHA-256.
7. Versionner les binaires dans Kaggle Models et le bundle de preuve dans un
   Dataset privé, sans ajouter ces gros fichiers à GitHub.
8. Après sélection gelée et décision explicite seulement, joindre les entrées
   finales et ouvrir l'évaluation test.

L'utilisateur n'a pas besoin de créer les notebooks manuellement tant que la CLI
authentifiée fonctionne. Le dépôt peut rester privé pendant cette préparation.
