# The Scenic Route: SSRF con open-redirect + descubrimiento de servicios internos

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae).*

**Concepto.** Un sink "monitorea esta URL" hace una petición server-side (probe) y rechaza IPs internas cuando se le envía la URL directa. El bypass clásico: un **open-redirect** en un servicio de confianza hace que el probe siga un `302` hacia una dirección interna sin re-validarla (CWE-610 → CWE-918).

**Identificación y bypass.**
- Enviar `http://127.0.0.1/` directo al probe → rechazado por el filtro de IPs internas.
- El servicio de "attribution" expone `/go?next=<url>` (open-redirect). El probe sigue el redirect sin re-chequear el destino.
- `/go?next=http://127.0.0.1:80/` → el probe responde **"connection refused"** = alcanzó localhost (puerto cerrado pero alcanzable). Bypass confirmado.

**Descubrimiento interno (probe ≠ app, arquitectura Docker).** Si el probe corre en otro contenedor, `127.0.0.1` de la app le queda inalcanzable (timeout). El probe **sí resuelve nombres de servicio Docker**, así que se escanean nombres: el que **resuelve** (respuesta de conexión/refused) vs "Name or service not known" distingue servicio existente de inexistente. Interpretación de estados:
- `connection refused` = puerto cerrado pero host **alcanzable**.
- `timeout` = firewall, o instancia expirando.
- `Name or service not known` = el nombre no existe (DNS).
- `Network unreachable` = sin ruta/egress.

**Explotación.** `app.js` filtraba una referencia al *control plane* en `127.0.0.1:9101` con ruta `/v1/monitors`. Encadenando el redirect:
`GET /v1` → `/v1/secrets` → `operator_token`, que libera la flag.

```
FLAG{c029ae0b98ff2c72}
```

**Qué NO funcionó.** Variantes de loopback (`0.0.0.0`, `127.0.0.2`, `[::1]`) y apuntar al host público en `:9101` (timeout). También confundir una **instancia expirando** con un firewall (mismo síntoma de timeout) — reintentar en instancia fresca fue clave.

**Herramientas.** `curl`, lectura de `app.js`, interpretación fina de errores de conexión.

## Implicaciones para pentesting/bug bounty
El open-redirect casi siempre está catalogado como low/informational; encadenado con un SSRF filtrado sube a critical. Siempre inventariar todos los `?next=`/`?url=`/`?redirect=` del scope como munición para bypass de allow-lists de SSRF. En entornos contenedizados, el fetcher server-side resuelve nombres de servicio (`web`, `redis`, `api`, `db`), no solo `127.0.0.1`: enumerar por nombre y leer los errores como oráculo. Metadata de cloud (`169.254.169.254`) es el objetivo estándar. Mapea a OWASP A10 (SSRF).
