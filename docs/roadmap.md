# Roadmap de soumission

## Phase 1 — Donnees et preuve de faisabilite

- auditer les datasets prioritaires ;
- choisir une tache principale et une metrique ;
- telecharger un sous-ensemble reproductible ;
- etablir la baseline et le split anti-fuite ;
- documenter la licence et les limites.

## Phase 2 — Modele et evaluation

- integrer une segmentation preentrainee ;
- mesurer la baseline ;
- fine-tuner uniquement si les labels le justifient ;
- extraire les caracteristiques et embeddings ;
- entrainer le modele phenotypique ;
- ajouter calibration, ablations et analyse d'erreurs.

## Phase 3 — Produit

- connecter le modele versionne a FastAPI ;
- afficher masques, controles et traitements dans React ;
- ajouter provenance, avertissements et incertitude ;
- generer un rapport exportable ;
- rendre la demonstration accessible et robuste.

## Phase 4 — Remise

- figer les resultats et artefacts ;
- verifier la reproduction depuis un environnement propre ;
- rediger le rapport de 15 a 20 pages ;
- enregistrer une video de moins de cinq minutes ;
- publier le depot et le Writeup Kaggle ;
- preparer une presentation courte pour la finale.

## Definition de termine

Le projet n'est soumis que si :

- chaque chiffre du rapport provient d'un script versionne ;
- le dataset et les licences sont cites ;
- la demonstration fonctionne sans compte payant ;
- Docker lance l'application sur une machine propre ;
- les limites et echecs sont exposes ;
- le Writeup contient video, depot, resume et rapport.

