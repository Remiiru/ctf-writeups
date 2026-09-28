# JWT kid confusion a clave HMAC vacía

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Nothing to sign here» (Web/JWT, Easy; Cooperativa de Pagos Caudalix).*

El bug exacto (venía el fuente):
```python
def resolve_session_key(kid):
    return OctKey.import_key(SIGNING_KEYS.get(kid, ""))
```
Creds demo `CX-4471 / abarrotes-4471`; con `role: "tesoreria"` forjado, `GET /api/settlements/master` devolvió el ledger con `custodian_note: FLAG{...}`.

**Concepto.** El server resuelve la clave de firma con `SIGNING_KEYS.get(kid, "")`: un `kid` fuera de la whitelist cae al **string vacío**, que se importa como una clave HMAC válida de longitud 0. Permite forjar tokens con `kid` arbitrario y rol elevado firmados con clave vacía (CWE-347, verificación de firma rota).

**Identificación.** Leer el fuente antes de atacar black-box: el bug estaba en la función de resolución de clave, no en cripto. El patrón delator es `dict.get(kid, "")` → key vacía importada como OctKey/HMAC.

**Explotación.**
1. Replicar localmente la librería exacta del `requirements.txt` (p. ej. `joserfc 1.6.7`) para confirmar que `import_key("")` produce `b""` usable y que `encode`/`decode` + claims registry validan OK. Así se distingue un fallo lógico de un problema de transporte.
2. Forjar: header `{alg:HS256, kid:<arbitrario>}`, claims con el rol privilegiado (`role=tesoreria`), firmar con `hmac.new(b"", signing_input, sha256)`.
3. Entregar con `curl` el token completo sin pasarlo por canales que redacten secretos (evita corromperlo).

```
FLAG{71a030a64a72d8b6}
```

**Qué NO funcionó.** Parecía `alg=none` pero el server fuerza `algorithms=["HS256"]`. El `UnicodeDecodeError` inicial era corrupción del token al pasarlo por un canal que redactaba secretos, no que la clave vacía fuera inútil. Crackear la SESSION_KEY real era innecesario.

**Herramientas.** `curl`, `python3`, `joserfc 1.6.7`, `hmac`/`hashlib`.

## Implicaciones para pentesting/bug bounty
La familia de bugs de `kid`: path traversal (`kid: ././dev/null` → clave conocida), SQLi en el claim `kid`, y el fallback a clave vacía/por defecto que vimos acá. Siempre que haya JWT con `kid`, probar valores fuera de rango y ver si el server degrada a una clave predecible. Y replicar la librería exacta localmente para no confundir un fallo de transporte con uno criptográfico. Mapea a OWASP A02/A07.
