# Contrôleur de bassin (edge)

Un processus par bassin. Tout ce qui est nécessaire à la survie du bassin est calculé ici, sans
dépendance au réseau : acquisition Modbus, prétraitement, fusion, *digital twin*, qualification,
décision, régulation sous garde-fous, tampon local et publication du Rapport de bassin.

Langage : Rust. Voir le [périmètre](../docs/PERIMETRE-POC.md#5-edge-rust-un-conteneur-par-bassin).
