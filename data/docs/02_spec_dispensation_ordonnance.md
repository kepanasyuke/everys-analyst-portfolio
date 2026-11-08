---
doc_id: SPEC-DISP-02
titre: Spécification — dispensation sur ordonnance
version: 2026.1
tags: [dispensation, ordonnance, metier]
---

# Dispensation d'une ordonnance

## Objectif

Permettre au pharmacien de délivrer les médicaments prescrits, de contrôler la conformité de
l'ordonnance et de préparer la facturation à l'assurance maladie.

## Règles métier

1. Une ordonnance contient au moins une ligne de prescription : code CIP13, posologie, durée.
2. La dispensation est **refusée** si l'ordonnance est datée de plus de 12 mois.
3. Pour une prescription de stupéfiants, la durée maximale est de 28 jours et un double contrôle
   pharmacien est **obligatoire** avant validation.
4. Le pharmacien peut substituer un princeps par un générique si le prescripteur n'a pas coché
   « non substituable » ; la substitution est tracée dans le journal d'audit.
5. Une ligne peut être délivrée partiellement ; le reliquat reste ouvert 30 jours.

## Critères d'acceptation

- Étant donné une ordonnance valide, quand le pharmacien valide la dispensation, alors une vente
  est créée avec le statut « délivrée ».
- Étant donné une ordonnance de plus de 12 mois, quand le pharmacien tente la validation, alors le
  système affiche un blocage et aucune vente n'est créée.
- Étant donné une ligne de stupéfiants sans double contrôle, quand la validation est demandée,
  alors la validation est refusée avec le motif « contrôle pharmacien manquant ».

## Points ouverts

- Faut-il autoriser la dispensation partielle d'un stupéfiant ? Avis pharmacien référent attendu.
- Le délai de 30 jours pour le reliquat est-il aligné avec la réglementation DOM ?
