---
doc_id: SPEC-REM-03
titre: Spécification — remboursement et tiers payant
version: 2026.1
tags: [remboursement, tiers-payant, fiscalite]
---

# Remboursement, tiers payant et fiscalité

## Taux de prise en charge

Le taux de remboursement est porté par la fiche article : 100 %, 65 %, 30 % ou 0 % (non
remboursable). Le taux est recopié sur la ligne de vente au moment de la délivrance : une
modification ultérieure du référentiel ne réécrit pas l'historique.

## Tiers payant

En tiers payant, la part assurance maladie n'est pas encaissée au comptoir. La créance est transmise
par télétransmission dans un flux SESAM-Vitale. Une créance rejetée doit être corrigée puis
retransmise dans un délai de **48 heures** ; au-delà, l'officine passe en impayé.

## Fiscalité

Les médicaments remboursables sont soumis à une **TVA à 5,5 %**. Les produits de parapharmacie
sont soumis à une TVA à 20 %. La TVA est calculée sur le prix public TTC, arrondie au centime.

## Cas limites

- Un article à 0 % de remboursement reste vendable, mais aucune créance n'est créée.
- Une ordonnance multi-prescripteurs génère une créance par prescripteur.
- Le tiers payant est refusé si la carte Vitale est absente et qu'aucune attestation n'est saisie.

## Critères d'acceptation

- Étant donné un article remboursable à 65 %, quand la vente est validée en tiers payant, alors la
  part patient est de 35 % du prix public et une créance est créée.
- Étant donné une créance rejetée depuis plus de 48 heures, quand l'écran de suivi est ouvert, alors
  la créance apparaît en impayé.
