# Warning Signs: warning de PHP rompe la CSP + XSS reflejado + exfil same-origin

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae).*

**Concepto.** La app usa una CSP con nonce (`script-src 'nonce-X'`) que bloquea el XSS reflejado. Pero la config de PHP (`display_errors=1` + `output_buffering=0` + `max_input_vars=1000`, vista en `supervisord.conf`) permite **emitir salida antes** de que `index.php` mande el header CSP: al enviar **más de 1000 variables GET**, PHP imprime el warning *"Input variables exceeded 1000"* ANTES de ejecutar el script → cuando `header('Content-Security-Policy: …')` corre da *"headers already sent"* → **la respuesta sale sin CSP** (CWE-1188 config + CWE-116 encoding).

**Bypass del filtro de reflexión.** El sink `/panel` refleja `$ref` con un `scrub` que hace `htmlspecialchars` y luego `urldecode`, bloqueando `%3c` **por parámetro**. Técnica:
- **Partir el `<`** en el borde entre dos parámetros: `zone=%3` y `sign=c…` → concatenados dan `%3c` → el `urldecode` final produce `<`.
- **Doble-codificar** `"`, `&`, `>` (sobreviven a `htmlspecialchars` como `%22`/`%26`/`%3e`; el `urldecode` final los restaura).
- Usar **backticks** para evitar comillas en el JS.

**Payload y exfil.**
```html
<svg/onload="location=`/ledger?ticket=X&entry=${localStorage.duty_key}`">
```
El bot (Playwright) guarda `/flag.txt` en `localStorage.duty_key`; el `onload` (más confiable que `img/onerror`) lo lee y navega a `/ledger` — un **sink same-origin**, sin necesidad de egress externo. Luego se lee `/ledger?ticket=X`:

```
FLAG{e807a6bbf7b80f84}
```

**Herramientas.** `curl`/script para generar >1000 params, entendimiento de `htmlspecialchars`+`urldecode`, `svg onload`.

## Implicaciones para pentesting/bug bounty
Dos lecciones reusables: (1) una CSP servida por la aplicación (no por el servidor web) es frágil — cualquier output previo (`display_errors`, `var_dump` de debug, BOM, whitespace antes de `<?php`) la anula por "headers already sent"; forzar warnings (`max_input_vars`, tipos inválidos, límites) es una vía real de bypass de CSP. (2) Los filtros que decodifican **después** de sanitizar (`htmlspecialchars` → `urldecode`) se rompen partiendo el payload entre parámetros o con doble encoding. Cuando no hay egress externo, exfiltrar a un endpoint same-origin del propio target. Mapea a OWASP A03 (Injection/XSS).
