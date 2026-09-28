# Reset token predecible por UUIDv1

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Time Served» (Web, Easy; el código lo marcaba con un `TODO`).*

Detalle real: cuenta `ana.rios@correo.example`; `/mailbox/<mi-email>` filtró mis tokens UUIDv1 → `node=49f9d6894147`, `clockseq=0x1c3c` (constantes del proceso); `POST /recover` para `admin@nubrera.example` (no filtra por staff); `/audit` público dio el timestamp de `reset.requested` a microsegundos; reconstrucción con node+clockseq fijos → **hit en el 3er candidato** (los UUID reales caen en ms exactos). ⚠️ El barrido amplio inicial fue uno de los detonantes del gate anti-abuso de la plataforma —.

**Concepto.** El servidor genera tokens de reseteo de password con `uuidv1()` (basado en tiempo + MAC/node + clockseq) en vez de un valor aleatorio (CWE-330/CWE-340). Con un token propio conocido (para derivar `node`/`clockseq`) y un log público con timestamps de alta resolución, se reconstruye el UUIDv1 del token de la víctima (admin).

**Explotación.**
1. Leer el fuente: buscar generación de tokens con `uuidv1`/`v4`, `Math.random`, `Date.now`, contadores. Confirmar que es UUIDv1 (time-based: timestamp 100ns desde 1582 + node + clockseq).
2. Obtener un token UUIDv1 **propio** (aquí `/mailbox/<mi-email>` lo entregaba) y decodificar `time_low`/`time_mid`/`time_hi` → timestamp; `clockseq` (bits con variante 10) y `node` (últimos 6 bytes).
3. Disparar el reset de la víctima y leer del endpoint público de auditoría el **timestamp exacto** del evento.
4. Reconstruir candidatos con `node`+`clockseq` fijos, variando el timestamp (los tokens reales caen en ms exactos → ~1 candidato por ms).
5. Sondear `/recover/<token>`: `200` = válido, `404` = no. Resetear la password de la víctima y escalar.

```
FLAG{96a7b55a398febba}
```

**Qué NO funcionó.** El throttle de `/recover` parecía límite duro pero se recarga continuamente. Un barrido amplio (±3ms, 6000 candidatos) falló porque el sub-ms del uuid no se usa (cae en ms exactos); restringir a `us%1000==0` y anclar con un token propio **fresco** (offset ~-0.7ms) dio el hit al 3er intento.

**Herramientas.** `curl`, `python3`.

## Implicaciones para pentesting/bug bounty
Cualquier token de seguridad (reset, invitación, verificación, session id) generado con UUIDv1, `Math.random`, timestamps o contadores es reconstruible. Un token propio sirve de "muestra" para derivar los campos fijos (node/clockseq/MAC). Los logs/endpoints de auditoría con timestamps de alta resolución son el otro ingrediente. Mapea a OWASP A02 (Cryptographic Failures) / A07.
