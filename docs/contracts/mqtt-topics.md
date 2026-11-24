# Topics MQTT

Version 1.

Hiérarchie `orca/{site}/{tank}/…` (rapport d'architecture §6.4). Charges utiles en JSON, horodatages
en temps simulé, ISO 8601 UTC.

| *Topic* | Sens | QoS | *Retained* | Flux | Contenu |
|---|---|---|---|---|---|
| `orca/{site}/{tank}/report` | edge → fog | 0 | non | F1 | Rapport de bassin complet ([schéma](rapport-de-bassin.schema.json)) |
| `orca/{site}/{tank}/status` | edge → fog | 1 | **oui** | F1 | Bloc état du rapport |
| `orca/{site}/{tank}/presence` | edge → fog | 1 | **oui** | F8 | `{"online": true}` ; *Last Will* `{"online": false}` |
| `orca/{site}/{tank}/alert/{severity}` | edge → fog | 1 | non | F2 | Alerte locale (`critique`, `majeure`, `information`) |
| `orca/{site}/{tank}/command/{actuator}` | fog → edge | 2 | non | F3 | `{"id", "mode", "value", "requested_by"}` |
| `orca/{site}/{tank}/command/{actuator}/ack` | edge → fog | 2 | non | F3 | `{"id", "result": "accepted\|clipped\|refused", "reason"}` |
| `orca/{site}/{tank}/config` | fog → edge | 1 | **oui** | F4 | Configuration versionnée (seuils, paramètres du modèle local) |
| `orca/{site}/{tank}/maintenance` | fog → edge | 1 | **oui** | F13 | Équipements déclarés en maintenance |
| `orca/sim/clock` | simulator → tous | 1 | **oui** | — | `{"real_epoch", "sim_epoch", "factor"}` |

## Clés d'idempotence

Le tampon de l'*edge* rejoue en « au moins une fois » ; le serveur de parc écrit en
`INSERT … ON CONFLICT DO NOTHING` sur :

| Message | Clé |
|---|---|
| Rapport de bassin | `(tank, window_start)` |
| Alerte, événement | `(tank, type, timestamp)` |
| Commande | `id` (identifiant de corrélation) |

## Rejeu après coupure

Ordre : alertes, puis changements d'état, puis rapports ; chronologique à criticité égale ; débit
limité pour ne pas pénaliser les bassins restés en ligne.
