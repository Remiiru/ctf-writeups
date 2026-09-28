# Scripts

## `tenant_signed_id_cross_shard.sh`
Cadena mínima (~5 requests espaciados) para el cross-tenant de Active Storage: signup en el shard `demo`, subir docs hasta que el blob propio tome el mismo `id` que la flag, y pedir el proxy de descarga con `Host` = shard interno (el `signed_id` = HMAC(id) es válido en ambos shards porque comparten `SECRET_KEY_BASE` y object store). Reutilizable para multi-tenant donde un token firmado ata por id y no por tenant.
