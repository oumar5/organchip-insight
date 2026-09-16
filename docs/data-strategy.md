# Strategie de donnees

## Objectif de l'audit

Selectionner un dataset permettant une demonstration credible en moins de 25
jours, avec une licence compatible, des labels exploitables et une separation
entrainement/test sans fuite biologique.

## Candidats prioritaires

| Source | Usage potentiel | Risque principal |
|---|---|---|
| BBBC | segmentation, morphologie, reponse a des composes | lien indirect avec organ-on-chip |
| RxRx1 | embeddings et perturbations cellulaires | volume et effets de lot |
| JUMP Cell Painting | profils phenotypiques et mecanismes d'action | complexite et cout de calcul |
| IDR | validation externe sur imagerie biologique | heterogeneite des etudes |
| Donnee OoC publique | validation directe du cas d'usage | disponibilite et annotations |

## Criteres de decision

Chaque candidat doit etre note sur :

1. pertinence organ-on-chip ou transfert justifie ;
2. licence et redistribution ;
3. qualite et provenance ;
4. presence de controles, traitements et replicats ;
5. labels disponibles ;
6. volume compatible avec les ressources ;
7. metrique scientifique defendable ;
8. possibilite de validation externe.

## Protocole anti-fuite

La separation ne doit pas etre faite aleatoirement image par image lorsqu'un
meme puits, lot, plaque, donneur ou experience produit plusieurs images.

Ordre prefere :

1. test externe ou lot complet jamais vu ;
2. validation par plaque ou experience ;
3. entrainement sur les lots restants.

Les transformations apprises, normalisations et selections de caracteristiques
doivent etre ajustees uniquement sur l'entrainement.

## Metriques envisagees

- segmentation : Dice, IoU, precision et rappel par objet ;
- classification : AUROC, macro-F1, precision-recall ;
- regression : MAE, RMSE, correlation et intervalles de confiance ;
- calibration : Brier Score ou Expected Calibration Error ;
- robustesse : performances par plaque, dose, lot et type d'image.

## Decision bloquante

Aucun entrainement competitif ne commence avant la redaction d'une fiche de
dataset avec licence, schema, split, cible et metrique principale.

