# API d'incidents (simulateur)

API HTTP du simulateur, appelée par la console d'incidents. Documentation interactive :
http://localhost:8100/docs.

Version 1, premier jet.

| Méthode | Chemin | Effet |
|---|---|---|
| `GET` | `/tanks` | État physique de tous les bassins |
| `POST` | `/tanks/{tank}/perturb` | Perturbation libre : `{"quantity": "temperature_c", "offset": -3}` ou `{"set": …}` |
| `POST` | `/tanks/{tank}/faults` | Défaut de capteur ou d'actionneur : `{"device": "S04", "type": "drift\|stuck\|mute\|sentinel", "rate": …}` |
| `DELETE` | `/tanks/{tank}/faults/{device}` | Retire un défaut |
| `POST` | `/tanks/{tank}/network` | `{"connected": false}` : coupe la liaison réseau du bassin (INC-07) |
| `POST` | `/scenarios/{id}` | Lance un scénario du catalogue (`INC-01` … `INC-12`), sur un bassin ou tout le parc |
| `POST` | `/tanks/{tank}/replay` | `{"quantity": "temperature_c", "dataset": "…", "start": "…"}` : la grandeur suit une série réelle |
| `DELETE` | `/tanks/{tank}/replay/{quantity}` | Revient au modèle |
| `PUT` | `/clock` | `{"factor": 60}` : facteur d'accélération du temps |
| `GET` | `/injections` | Historique des injections horodatées (calcul des délais K01, K02) |
