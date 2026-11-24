# Contrats d'interface

Ce que les composants s'échangent. Toute modification passe par une pull request relue par l'autre
membre de l'équipe.

| Contrat | Produit par | Consommé par |
|---|---|---|
| [Topics MQTT](mqtt-topics.md) | edge, fog, simulateur (horloge) | edge, fog, twin |
| [Rapport de bassin](rapport-de-bassin.schema.json) | edge | fog, twin |
| [Carte Modbus](modbus-map.md) | simulateur | edge |
| [API d'incidents](chaos-api.md) | simulateur | interface web (console d'incidents) |

Conventions communes :

- charges utiles en JSON, encodées en UTF-8 ;
- horodatages en temps simulé, ISO 8601 UTC ;
- identifiants de bassin et de site en minuscules, sans espace (`parc-nice`, `a1`) ;
- grandeurs nommées avec leur unité : `temperature_c`, `ph`, `o2_mg_l`, `salinity_ppt`,
  `nh3_mg_l`, `flow_l_min`, `power_w`, `reagent_pct`.
