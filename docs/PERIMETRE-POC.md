# Périmètre du POC

Les identifiants (EX-\*, K01–K14, M1–M16, P1–P12, F1–F13, I1–I6) renvoient au
[rapport d'architecture](ORCA-rapport-archi-BALADIER-BARBAUD.pdf) et au
[rapport Data Ingestion Pipeline](ORCA-rapport-data-BALADIER-BARBAUD.pdf).

## Inclus / exclu

Bassins, capteurs et actionneurs sont simulés. Démo par défaut : 6 bassins, 2 par profil (A, B, C).
Les bassins sont déclarés dans `config/tanks.yaml` ; un bassin = un conteneur *edge* + un serveur
Modbus.

Optionnel :

- notifications ntfy des alertes `CRITIQUE` ;
- délestage énergétique N0–N3 sur coupure secteur injectée.

Exclu :

- couche cloud (F9) ;
- caméra et vidéo ;
- appairage, NFC, déploiement par lots (F12) ;
- mTLS, révocation, journal d'audit (présentés en soutenance seulement) ;
- authentification, remplacée par un sélecteur de rôle vérifié côté API ;
- Grafana, l'historique est intégré à l'interface ;
- capteurs non simulés : azotés (NO₂⁻, NO₃⁻), turbidité, ORP, conductivité, niveau d'eau, fuite,
  luminosité, température ambiante.

## Simulateur

### Capteurs

| Capteur | Grandeur | Période (temps simulé) |
|---|---|---|
| S01, S02 | Température de l'eau | 60 s |
| S03 | pH | 60 s |
| S04, S05 | O₂ dissous | 60 s |
| S06 | Salinité (profils A et C) | 300 s |
| S08 | Ammoniaque | 6 h |
| S13 | Débit de circulation | 60 s |
| S18 | Consommation électrique | 60 s |
| S19 | Niveau de réactif pH | 1 h |

### Actionneurs

A01 chauffage, A02 groupe froid, A03 aérateur, A04 pompe, A05 injecteur pH, A06 éclairage.

### Modèle physique

- Température : `dT/dt = (T_local − T)/τ + (P_chauffe − P_froid)/C`
- O₂ : échange vers `O2_sat(T, S)` (accéléré par aérateur et pompe), + photosynthèse, − respiration
- pH : baisse lente, remontée de jour, impulsions de l'injecteur
- Ammoniaque : production continue, élimination tant que la pompe tourne
- Débit : nominal si pompe ON, 0 sinon ou si pompe désamorcée
- Consommation : somme des puissances des actionneurs actifs
- Bruit gaussien sur chaque capteur
- Défauts par capteur : biais, dérive, valeur figée, muet, sentinelle

La température du local et la lumière sont des paramètres internes, non mesurés.

### Modbus

- *Input registers* : une valeur entière par capteur avec facteur d'échelle (×10, ×100) ; une
  sonde de température en °F.
- Sentinelle `0xFFFF` sur défaut ; pas de réponse si la sonde est muette.
- *Coils* : un par actionneur.

### Horloge simulée

Publiée sur `orca/sim/clock` (*retained*) : `{real_epoch, sim_epoch, factor}`. Chaque composant
calcule `sim_now = sim_epoch + (real_now − real_epoch) × factor`. Facteur de ×1 à ×600. Tous les
horodatages sont en temps simulé, UTC.

### API d'incidents

- Modifier ou décaler une grandeur physique d'un bassin.
- Activer un défaut sur un capteur ou un actionneur.
- Lancer un scénario du catalogue sur un bassin ou sur tout le parc.
- Couper / rétablir le réseau d'un bassin (`docker network disconnect` / `connect` du conteneur *edge*).
- Chaque injection est horodatée pour mesurer K01 et K02.

## Edge

| Étape | Contenu |
|---|---|
| Démarrage | Attend une configuration valide (*retained*), la persiste en SQLite (I1, EX-B09) |
| P2 | *Polling* Modbus, période par grandeur |
| ACL | Échelles, °F → °C, sentinelle → `INVALIDE`, capteur → bassin |
| P3, P4 | Médian k = 5, moyenne glissante 5 points |
| P5 | Horodatage à la source, monotonie |
| P6a | Fusion T et O₂ par inverse de la variance, cohérence 3σ |
| P6b | Digital twin : Kalman scalaire sur T et O₂ ; résidu > 3σ → `SUSPECTE`, sonde muette → `INTERPOLÉE` |
| P7 | Règles de qualité ordonnées + valeur figée, avec motif |
| P8 | NOMINAL → CRITIQUE, DÉGRADÉ, HORS LIGNE ; confirmation 3/2, hystérésis 10 %, temps mort 15 min |
| Régulation | Hystérésis ; jamais sur une mesure `SUSPECTE` ou `INTERPOLÉE` |
| Garde-fous | Rampe ΔT ≤ 0,5 °C/h, ΔpH ≤ 0,2/h, appliquée aussi aux commandes distantes (EX-X05, I6) |
| Contrôle d'effet | Ack Modbus → conso S18 → effet prédit par le twin |
| Réactif | < 20 % → injection bloquée, `DÉGRADÉ` |
| P9 | Agrégats 5 min (min, max, moyenne, écart-type, nb valides) → Rapport de bassin |
| Tampon | SQLite ; rejeu par criticité puis date, débit limité, clé idempotente |
| MQTT | *Last Will* sur `presence`, *retained* sur `status`, `presence`, `config` |
| Commandes (F3) | Identifiant de corrélation, réponse sur `.../ack` (acceptée, écrêtée, refusée + motif), mode auto/manuel |

## Fog

| Fonction | Contenu |
|---|---|
| Ingestion | Double horodatage, `INSERT … ON CONFLICT DO NOTHING` |
| Stockage | TimescaleDB : hypertables (agrégats, états) + tables alertes, commandes, configurations |
| Alertes | Anti-répétition (EX-A06), cycle ouverte → acquittée → close |
| Présence | `HORS LIGNE` sur *Last Will* ou 3 périodes sans rapport |
| Configuration (F4) | Validation I2/I3, propagation *retained*, statut confirmée / en attente |
| P11 | Régression sur 6 h (heure de franchissement prévue), CUSUM sur l'écart au twin |
| P12 | Corrélation inter-bassins d'un même profil → une alerte « cause commune » |
| Historique | Script qui génère 30 jours simulés en base |
| API | REST (OpenAPI) + WebSocket ; rôles vérifiés côté serveur |

## Interface web

| Écran | Contenu |
|---|---|
| Parc | Grille des bassins : état, présence, grandeurs clés |
| Bassin | Mesures avec qualité et motif, actionneurs (auto/manuel, ack), journal des commandes, écart au twin |
| Bassin 3D | Poissons (plus lents si O₂ bas), bulles si aérateur ON, turbidité, jour/nuit, teinte selon l'état |
| Alertes | Liste, criticité, acquittement, filtres |
| Configuration | Seuils par bassin, statut confirmée / en attente |
| Historique | Par bassin et grandeur : période, qualité par point, trous, seuils, tendance, CUSUM |
| Console d'incidents | Page séparée : perturbations, scénarios, coupure réseau, facteur de temps, chronomètre K01/K02 |
| Rôle | Responsable, technicien, biologiste, admin (l'admin ne peut pas commander) |

## Incidents

| # | Scénario | Injection | Attendu |
|---|---|---|---|
| INC-01 | Chauffage HS (profil A) | Résistance coupée, local à 20 °C | Commande ON sans conso → `MAJEURE` ; tendance, puis `ALERTE`, puis `CRITIQUE` |
| INC-02 | Sonde O₂ n°1 encrassée | Biais croissant | Désaccord avec sonde n°2 et twin → `SUSPECTE`, `DÉGRADÉ`, pas de commande ; CUSUM |
| INC-03 | Sonde pH muette | Pas de réponse Modbus | `INVALIDE`, `DÉGRADÉ`, régulation pH suspendue |
| INC-04 | Sonde figée | Valeur constante | `SUSPECTE` |
| INC-05 | Sentinelle / mauvaise unité | `0xFFFF` ou °F mal déclaré | `INVALIDE`, pas de fausse alerte |
| INC-06 | Pompe désamorcée | Pompe ON, débit 0 | `MAJEURE`, O₂ baisse |
| INC-07 | Coupure réseau | `docker network disconnect` | `HORS LIGNE`, régulation continue, rejeu sans doublon au retour |
| INC-08 | Panne de clim | Local +8 °C | Tous les bassins chauffent → une seule alerte « cause commune » |
| INC-09 | Réactif épuisé | Niveau à 15 % | Injection bloquée, `MAJEURE`, `DÉGRADÉ` |
| INC-10 | Commande dangereuse | +3 °C demandé d'un coup | Écrêtée ou refusée, motif affiché |
| INC-11 | Coupure secteur (optionnel) | Alimentation coupée | Délestage N1 → N3, seul l'aérateur reste |
| INC-12 | Perturbation libre | Valeur au choix | Selon la grandeur |

