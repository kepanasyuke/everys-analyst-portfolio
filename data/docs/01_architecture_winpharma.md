---
doc_id: ARCH-01
titre: Architecture WinPharma — vue d'ensemble
version: 2026.1
tags: [architecture, reseau, securite]
---

# Architecture de WinPharma

WinPharma est une application trois-tiers installée dans l'officine : client Windows lourd,
serveur d'application, serveur de base de données. Les échanges entre le poste de travail et le
serveur d'application passent par un protocole binaire propriétaire sur TCP, encapsulé dans TLS.
La version 2026.1 impose **TLS 1.3 obligatoire** pour toute connexion cliente, y compris depuis
les postes secondaires du back-office.

## Composants

- **Client officine** : application desktop C++ sous Windows, interface de comptoir.
- **Serveur d'application** : services métier (dispensation, stock, caisse), API SOAP pour les tiers.
- **Serveur de base de données** : historique des ventes, référentiel articles, journal d'audit.
- **Services cloud Everys** : télétransmission, mise à jour des bases prix, supervision.

## Flux réseau

Le client ouvre une session authentifiée (identifiant + mot de passe + jeton de poste). La session
expire après 30 minutes d'inactivité. Les appels aux services cloud utilisent HTTPS avec
vérification stricte du certificat ; un certificat expiré bloque la télétransmission et doit être
renouvelé par l'administrateur de l'officine.

## Contraintes d'exploitation

L'application est critique : une indisponibilité de plus de 15 minutes en heures d'ouverture est
considérée comme un incident majeur. Le mode dégradé permet la vente au comptoir sans
télétransmission, avec reprise différée des déclarations.
