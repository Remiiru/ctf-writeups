# Scripts

## `render_lfi_iframe.html`
Etapa 1 — payload HTML para el servicio html→JPEG con Chromium `--allow-file-access-from-files`: LFI vía `<iframe src=file://>` (archivos renderizables) y XHR síncrono (archivos que Chromium descargaría). El truco de `margin-top`/`overflow:hidden` pagina archivos largos en el viewport 1280x720.

## `render_ssrf_archivist.html`
Etapa 2 — pivote SSRF de identidad: desde el HTML renderizado (como `tributum`) hace `fetch` al chromedriver de `archivist` (`HELPER_PORT`, `--allowed-origins=*`), abre una sesión Chrome como archivist y lee el vault `0700` con `execute/sync`. Ajustar `HELPER_PORT` (=47210+seed%8) y la ruta del recibo a lo leído en la etapa 1.
