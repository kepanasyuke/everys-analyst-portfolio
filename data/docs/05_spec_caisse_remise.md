---
doc_id: SPEC-CAI-05
titre: Spécification — caisse, remise et encaissement
version: 2026.1
tags: [caisse, encaissement, remise]
---

# Caisse et encaissement

## Encaissement

Une vente peut être réglée en espèces, carte bancaire, chèque ou virement. Le montant rendu en
espèces est calculé automatiquement. Une vente ne peut être clôturée que si la somme des règlements
égale le montant dû, au centime près.

## Remise

La remise commerciale est appliquée ligne par ligne, en pourcentage, et tracée dans le journal.
La **remise maximale autorisée est de 30 %** du prix public. Au-delà du seuil, une validation du
titulaire est demandée. La remise s'applique avant le calcul de la TVA.

## Annulation

Une vente peut être annulée le jour même par le pharmacien. L'annulation crée une écriture
inverse, elle ne supprime jamais l'écriture d'origine. Une vente en tiers payant déjà transmise
ne peut pas être annulée : elle doit faire l'objet d'un avoir.

## Hypothèse à tester (A/B)

Hypothèse : proposer la remise maximale pré-remplie à 20 % au lieu de 0 % augmente le panier
moyen sans dégrader la marge. Indicateur principal : panier moyen TTC. Indicateur de garde-fou :
marge brute par vente. Durée prévue : 4 semaines, deux groupes de 6 officines appariées.

## Critères d'acceptation

- Étant donné une vente de 100,00 € et un règlement de 120,00 € en espèces, quand la validation
  est demandée, alors le rendu affiché est 20,00 €.
- Étant donné une remise saisie à 35 %, quand la validation est demandée, alors une autorisation
  titulaire est exigée.
