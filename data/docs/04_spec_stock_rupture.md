---
doc_id: SPEC-STOCK-04
titre: Spécification — stock, seuil et rupture
version: 2026.1
tags: [stock, approvisionnement, metier]
---

# Gestion du stock et des ruptures

## Modèle

Chaque article possède un stock physique, un stock réservé et un seuil de réapprovisionnement.
Le stock disponible est égal au stock physique moins le stock réservé :

    disponible = physique - réservé

## Règles

1. Une vente décrémente le stock physique à la validation, pas à la saisie.
2. Un article dont le stock disponible est inférieur ou égal au seuil génère une alerte de
   réapprovisionnement.
3. Une rupture est déclarée quand le stock disponible est égal à zéro ; la rupture est datée et
   historisée par article et par officine.
4. Le réassort automatique est proposé chaque jour à 18 h 00, il n'est jamais exécuté sans
   validation du titulaire.
5. Un retour fournisseur augmente le stock au moment de l'expédition, pas de la réception.

## Cas limites

- Deux postes vendent le même dernier article à la même seconde : la transaction la plus lente doit
  être refusée avec le message « stock insuffisant », jamais autorisée en négatif.
- Un article périmé est sorti du stock disponible et bascule en statut « quarantaine ».

## Indicateurs

Le taux de rupture est calculé sur 30 jours glissants : nombre de jours en rupture divisé par
nombre de jours ouvrés. Un taux supérieur à 4 % déclenche une revue de l'assortiment.
