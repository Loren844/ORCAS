# Carte Modbus (par bassin)

Un serveur Modbus TCP par bassin, port `5020 + index du bassin` (ordre de `config/tanks.yaml`),
*unit id* 1. Le contrôleur interroge chaque capteur à sa période propre (P2).

Version 1.

## *Input registers* (capteurs, lecture seule)

Valeurs entières non signées sur 16 bits. `0xFFFF` = valeur sentinelle (défaut capteur).

| Adresse | Capteur | Grandeur | Unité brute | Conversion par l'ACL | Période |
|---|---|---|---|---|---|
| 0 | S01 | Température eau n°1 | 0,01 °C | `raw / 100` | 60 s |
| 1 | S02 | Température eau n°2 | 0,1 **°F** | `(raw / 10 − 32) × 5/9` | 60 s |
| 2 | S03 | pH | 0,01 | `raw / 100` | 60 s |
| 3 | S04 | O₂ dissous n°1 | 0,01 mg/L | `raw / 100` | 60 s |
| 4 | S05 | O₂ dissous n°2 | 0,01 mg/L | `raw / 100` | 60 s |
| 5 | S06 | Salinité | 0,1 ‰ | `raw / 10` | 300 s |
| 6 | S08 | Ammoniaque | 0,001 mg/L | `raw / 1000` | 6 h |
| 7 | S13 | Débit | 0,1 L/min | `raw / 10` | 60 s |
| 8 | S18 | Consommation | 1 W | `raw` | 60 s |
| 9 | S19 | Niveau de réactif pH | 0,1 % | `raw / 10` | 1 h |

Sonde muette : le serveur ne répond pas (exception Modbus ou *timeout*).

## *Coils* (actionneurs, lecture / écriture)

| Adresse | Actionneur |
|---|---|
| 0 | A01 Chauffage |
| 1 | A02 Groupe froid |
| 2 | A03 Aérateur |
| 3 | A04 Pompe de circulation |
| 4 | A05 Injecteur de correcteur pH (impulsion) |
| 5 | A06 Éclairage |
