# Render Unto Caesar: HTML→JPEG → LFI → SSRF a chromedriver interno

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae). Categoría Hard.*

**Concepto.** Un servicio convierte HTML enviado por el usuario en una imagen (thumbnail) usando Chromium con `--allow-file-access-from-files`. Ese flag rompe el aislamiento del origen `file://`, convirtiendo el render en un primitivo de **LFI** (CWE-73) y, encadenado, de **SSRF** contra servicios internos (CWE-918).

**LFI vía render.**
- `<iframe src="file:///etc/passwd">` → el contenido aparece en el thumbnail devuelto.
- Recon del layout de fuente: `file:///proc/self/cwd/` para descubrir el working dir del proceso.
- Archivos que Chromium **no renderiza** (`.sh`, `.conf` los descarga en vez de mostrarlos): leerlos con **XHR síncrono** desde el documento ya renderizado (funciona por `--allow-file-access-from-files` + un `SETTLE_SECONDS` de render suficiente para que el JS corra).
- Truco de paginación: para archivos largos que no caben en el viewport `1280x720`, un `<iframe>` con `margin-top` negativo dentro de un `div` con `overflow:hidden` permite "scrollear" y capturar por tramos.

**Pivote SSRF de identidad.** `supervisord.conf` reveló **dos** chromedrivers: uno corriendo como `tributum` (el que nos renderiza) y otro como `archivist` en `HELPER_PORT` (`47210 + seed%8`, p. ej. `47211`) lanzado con `--allowed-origins=*`. El recibo objetivo (`/opt/archivist/vault/…`) es `0700 archivist`, ilegible para `tributum`. Entonces:
1. Desde el HTML renderizado (como `tributum`), `fetch` al chromedriver de `archivist`: `POST /session` → abre un Chrome **como archivist**.
2. Navegar esa sesión a `file:///opt/archivist/vault/`.
3. `execute/sync` con XHR para leer el recibo **con permisos de archivist**.

```
FLAG{73a0bc13a182e680}
```
*(el archivo traía un `}` de más; enviar con uno solo).*

**Qué NO funcionó.** Leer el vault directamente como `tributum` (permisos `0700` de archivist). `<img onerror>` a veces no dispara — usar el approach directo (iframe/XHR).

**Herramientas.** Payloads HTML/JS, XHR síncrono, chromedriver JSON Wire (`POST /session`, `execute/sync`), lectura de `supervisord.conf` / `/proc/self/cwd`.

## Implicaciones para pentesting/bug bounty
Cualquier funcionalidad de "HTML→PDF/imagen" (wkhtmltopdf, headless Chrome, Puppeteer) es superficie de LFI/SSRF: probar `<iframe src=file://>`, `<img src=http://169.254.169.254/...>`, y XHR a servicios internos desde el DOM renderizado. Los flags peligrosos (`--allow-file-access-from-files`, `--disable-web-security`) convierten el render en lectura arbitraria. Un chromedriver/webdriver interno con `--allowed-origins=*` es un pivote de RCE/lateral: cualquiera que alcance su puerto controla un navegador con la identidad del proceso. Mapea a OWASP A10 (SSRF) + A01.
