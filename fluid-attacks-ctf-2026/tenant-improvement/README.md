# Tenant Improvement: cross-tenant por reuso de signed_id entre shards

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Tenant Improvement» (Web, Medium, 170 pts). La metodología nativa quedó registrada en; este writeup es la narrativa completa.*

⚠️ Se ejecutó DESPUÉS de que el gate anti-abuso de la plataforma se disparara: cadena mínima de ~5 requests espaciados (signup → 2 uploads → 1 listado → 1 descarga con Host cambiado), diseñada offline. Ver.

**Concepto.** Rails con horizontal sharding elige el shard por el primer label del `Host` (`request.host.split('.').first` → `interna.*` vs `demo`). El object store de blobs de Active Storage es **único/compartido** entre shards. El `signed_id` de un blob es `HMAC(blob_id, SECRET_KEY_BASE)`: ata al blob **por id, no por shard**. Si dos blobs de shards distintos comparten `id`, comparten `signed_id` (CWE-639 IDOR + CWE-284).

**Explotación.**
1. Signup en el shard `demo`.
2. Subir 2 documentos (ids secuenciales: mi blob toma `id=2`). El seed reveló que el blob de la flag en el shard interno también es `id=2`.
3. Descargar el proxy de **mi** signed_id (id=2) pero con `Host: interna.<host>` → el resolver apunta al shard interno donde `blob id=2` es la flag. El `signed_id` es válido (mismo id + misma clave) → entrega el blob de la víctima.

```
FLAG{281c0348a722cbd7}
```

Pista decisiva del seed: *"Plain rowid alias, not AUTOINCREMENT: a purged document releases its id, so a workspace can always work its way back down to a low one."* — o sea, siempre se puede forzar que mi blob tome un id bajo específico.

**Herramientas.** `curl` (upload + descarga proxy con `Host` cambiado).

## Implicaciones para pentesting/bug bounty
En apps multi-tenant, el aislamiento por base de datos/shard puede ser sólido y aun así filtrarse por un **recurso compartido transversal**: object store, cache, cola, search index. Cuando un token firmado (signed_id, JWT, presigned URL) ata solo por un identificador y no incluye el tenant/shard en el material firmado, se reutiliza cruzando el `Host`/tenant header. Revisar siempre qué exactamente está dentro del HMAC. Mapea a OWASP A01 (Broken Access Control) / API1 (BOLA).
