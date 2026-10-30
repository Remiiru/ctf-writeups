# Scripts

## `prototype_pollution_exploit.sh`
Exploit para retos web con "deep merge" inseguro en un endpoint de preferencias/settings que permite prototype pollution server-side. Contamina Object.prototype.unlocked=true usando el gadget constructor.prototype (bypass de filtros que bloquean __proto__), y luego dispara la acción que lee el gate. Reutilizable para cualquier CTF con node-merge/qs/deep-merge sin sanitización de keys.
