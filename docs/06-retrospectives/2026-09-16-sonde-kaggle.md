# Première sonde GPU Kaggle — 16 septembre 2026

## Faits observés

Sonde exécutée par la CLI Kaggle 2.0.1, sur accord de l'utilisateur, depuis
`dev` propre au commit `163d255`. Version 1 du notebook privé
[OrganChip Runtime Probe](https://www.kaggle.com/code/oumarbenlol/organchip-runtime-probe).
GPU demandé : `NvidiaTeslaT4`, durée maximale demandée : 600 secondes.
Les métadonnées relues après exécution confirment : privé, GPU activé, Internet
désactivé, aucune source dataset/compétition/notebook/modèle jointe.

Le notebook embarque uniquement du code de diagnostic et le contrat logiciel.
Ni données, ni poids préentraînés, ni fichier de secrets ne sont transférés.
Les trois cellules récupérées du serveur ont les mêmes sources que le notebook
local ; leur sérialisation JSON diffère. Aucun entraînement n'est réalisé.

| Élément | Valeur réellement observée |
|---|---|
| Python | 3.12.13 |
| torch / torchvision | 2.10.0+cu128 / 0.25.0+cu128 |
| CUDA / cuDNN | 12.8 / 91002 |
| GPU visibles | 2 × Tesla T4 ; forward exécuté sur le GPU par défaut, pas en multi-GPU |
| numpy / pandas | 2.0.2 / 2.3.3 |
| ONNX | 1.22.0 |
| ONNX Runtime | absent |
| Forward MobileNetV3 synthétique CUDA | réussi, sortie de forme [1, 2] |
| Parité ONNX/PyTorch | non vérifiée : import `onnxruntime` impossible |
| Contrat global | refusé, `runtime_checks_passed: false` |

Le statut Kaggle `COMPLETE` signifie que la sonde s'est terminée, pas que tous
ses contrôles ont réussi. Toutes les versions installées examinées respectent
les bornes du contrat v1 ; le seul blocage relevé est le paquet manquant.
L'hypothèse « Kaggle tourne probablement en torch 2.11 » n'est donc pas confirmée
pour cette image GPU. Cette observation ne décrit pas toutes les images Kaggle
futures, ni l'image CPU.

## Preuves archivées avant modification du contrat

- [Rapport brut](../../reports/runtime/kaggle-probe-2026-09-16-v1/runtime-report.json)
- [Métadonnées serveur, dont digest Docker](../../reports/runtime/kaggle-probe-2026-09-16-v1/kernel-metadata.json)
- [Journal Kaggle](../../reports/runtime/kaggle-probe-2026-09-16-v1/kernel.log.json)
- [Provenance et hashes](../../reports/runtime/kaggle-probe-2026-09-16-v1/provenance.json)

Le contrat runtime et les configurations scientifiques restent inchangés.
Aucun score de classification, de segmentation ou de comptage n'est établi.

## Décision et suite

Ne pas élargir les bornes torch/torchvision sans raison : elles conviennent à
l'environnement observé. Le pipeline actuel exige ONNX Runtime dès la validation
et prévoit l'export dans le notebook. Deux voies existent : fournir cette
dépendance hors ligne avec un hash et une phase d'installation explicitement
contrôlée, ou séparer l'entraînement GPU et l'export local avec des contrats par
étape. Aucune de ces deux adaptations n'est implémentée dans cette sonde.

Préférence pour la suite : fournir les dépendances manquantes dans le petit
bundle de ressources, puis vérifier la parité dans le même environnement GPU.
Cela nécessite de faire évoluer explicitement le bootstrap hors ligne et ses
tests : le notebook actuel interdit les commandes d'installation. Ne pas ajouter
un `pip install` improvisé ou activer Internet pendant un run scientifique.

La prochaine sonde doit réussir avant le run CNN. Préparer ensuite le split v2,
le bundle source filtré et les poids vérifiés ; ne pas téléverser les images du
test final dans les entrées de validation. Voir le [workflow Kaggle](../03-competition/kaggle-workflow.md).
