---
doc_id: SPEC-SOAP-06
titre: Spécification — intégration SOAP de télétransmission
version: 2026.1
tags: [integration, api, soap, tls]
---

# Intégration SOAP — télétransmission

## Contrat

Le service expose une opération `TransmettreFlux` en SOAP 1.2, encodage document/literal.
L'enveloppe contient un en-tête `EnteteSecurite` (identifiant officine, horodatage, signature) et
un corps `Flux` contenant le lot de factures encodé en base64.

## Exigences de transport

- HTTPS uniquement, **TLS 1.2 minimum**, suites AEAD autorisées.
- Délai d'attente client : 30 secondes. Au-delà, réessai avec back-off exponentiel (3 tentatives).
- Les réponses d'erreur applicative utilisent un code à 4 chiffres et un message en français.

## Idempotence

Chaque flux porte un identifiant unique `idFlux`. Un renvoi avec le même `idFlux` doit renvoyer le
résultat du premier appel sans retraiter le lot. Un `idFlux` déjà traité avec un contenu différent
est rejeté avec le code 4092.

## Supervision

L'état du dernier flux est affiché dans le tableau de bord officine : horodatage, code retour,
nombre de factures acceptées et rejetées. Un flux en échec depuis plus de 24 heures déclenche une
alerte à l'assistance.

## Critères d'acceptation

- Étant donné un flux déjà accepté, quand il est renvoyé avec le même `idFlux`, alors la réponse
  renvoie le code du premier appel et aucun doublon n'est créé.
- Étant donné une réponse serveur en 503, quand le client dépasse 30 secondes, alors trois tentatives
  espacées sont effectuées avant échec définitif.
