# Workflow Kaggle et GitHub

État au 16 septembre 2026 : la [sonde privée v1](retours-experience/2026-09-16-sonde-kaggle.md)
a tourné sur GPU ; ONNX Runtime manque. Aucun dataset OrganChip n'a été créé
par cette opération. Les notebooks scientifiques ne sont pas encore prêts à
lancer : split v2, préparation des bundles et résolution du runtime restent à faire.

## Organisation recommandée

Un seul dossier de préparation **local**, mais des entrées Kaggle distinctes :

| Entrée privée | Contenu | Pourquoi séparer |
|---|---|---|
| Images train/validation | Images sélectionnées par le manifeste retenu, chemins relatifs conservés | Gros volume stable : ne pas le transférer à chaque correction de code |
| Source et protocole | Code CNN filtré, configuration, manifestes autorisés, environnement et provenance | Petit volume versionné à chaque changement pertinent |
| Ressources du modèle | Poids ImageNet, provenance/licence, puis dépendances hors ligne approuvées et hashes | Ressources réutilisables, distinctes du code et des images |

Le notebook est un objet Kaggle séparé, **pas un quatrième dataset**. Pour la
sonde actuelle, il n'utilise aucune entrée. Les outputs (checkpoints, rapports,
ONNX) restent les sorties versionnées du notebook ; nul besoin de créer un
dataset pour chaque fichier ou chaque run.

On pourrait réunir code et ressources pour n'avoir que deux datasets. Ce n'est
pas interdit, mais le code change plus souvent que les poids et les dépendances.
La séparation en trois entrées est recommandée ; les chemins exacts sont des
paramètres. Le notebook actuel prévoit déjà trois racines (source, images,
poids) ; regrouper les poids et de futures dépendances suppose d'adapter les
chemins et le bootstrap, pas de prétendre que c'est déjà disponible.

Le test final reste dans une entrée distincte, jointe uniquement après gel des
choix et autorisation de l'évaluation finale. L'organisation finale précise doit
respecter les besoins de provenance du CLI ; les chemins finaux du notebook v1
ne constituent pas encore un export v2 prêt à téléverser.

Ne jamais envoyer le dépôt entier : exclure `.git`, `.env`, clés, caches,
expériences personnelles et artefacts de test. L'outil de staging doit utiliser
une liste autorisée de fichiers, vérifier les hashes et vérifier l'absence des
labels/rapports test dans le bundle de sélection. Le filtre de copie actuel du
notebook ne suffit pas à garantir cela : l'inventaire historique complet et
certains rapports contiennent des informations test. Il faudra adapter la
provenance à un inventaire autorisé, sans casser silencieusement les hashes v1.

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
2. Préparer ONNX Runtime hors ligne et son bootstrap vérifié ; refaire une sonde
   privée sans images et obtenir le succès du contrôle ONNX.
3. Générer et contrôler le manifeste v2 (fait : 2 056/509/507 images), puis
   figer les ablations train/validation.
4. Construire les trois bundles locaux et leurs hashes. Afficher leur contenu,
   leur taille, leur provenance et les réglages de confidentialité avant upload.
5. Sur confirmation, créer les datasets privés puis lancer le notebook de
   validation avec des versions identifiées. Ne pas importer deux copies du même
   notebook, l'une manuellement et l'autre par la CLI.
6. Archiver les résultats. Après sélection gelée et décision explicite seulement,
   joindre les entrées finales et ouvrir l'évaluation test.

L'utilisateur n'a pas besoin de créer les notebooks manuellement tant que la CLI
authentifiée fonctionne. Le dépôt peut rester privé pendant cette préparation.
