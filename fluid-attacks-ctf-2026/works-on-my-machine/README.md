# Vite dev server: bypass de fs.allow/fs.deny (CVE-2025-30208)

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Works On My Machine» (Web, Easy).*

**Concepto.** Un Vite dev server expuesto sirve archivos con `/@fs/<abs_path>` pero valida el allow-list (`fs.allow`). Agregando un separador de query trailing extra (`?raw??` o `?import&raw??`) se evaden los regex de query (`rawRE`/`urlRE`) que disparan la validación de acceso, pero el plugin de asset `?raw` igual lee el archivo crudo desde la raíz del filesystem → lectura arbitraria fuera del allow (CVE-2025-30208, CWE-22).

**Identificación.** Fingerprint: `/@vite/client`, `/src/*.jsx`, sourcemaps inline (`sourcesContent`) → confirmar Vite dev server expuesto y leer `vite.config.js` (`fs.allow`, `fs.deny`).

**Explotación.**
1. Fuga inicial de archivos denegados **bajo el root** con dot-trailing (CVE-2025-46565): `curl --request-target "/.env/."` devuelve el `.env`.
2. El `.env` apunta a un archivo **fuera** del allow (`/opt/…`).
3. Para archivos fuera de `fs.allow`, `/@fs/<abs_path>` + separador de query trailing **doble**:
```
curl --request-target "/@fs/opt/vitrina/keystore/deploy.secrets?import&raw??"
-> 200 con el contenido: REGISTRY_TOKEN=FLAG{5bdbb5f3e01cc8fb}
```
El `??` hace que `rawRE`/`urlRE` no matcheen (evita el `403` de `ensureServingAccess`) mientras el plugin `?raw`/`?import&raw` lee el archivo crudo.
4. Interpretar `403` ("outside of Vite serving allow list") vs `500` ENOTDIR para distinguir si el archivo existe.

```
FLAG{5bdbb5f3e01cc8fb}
```

**Advisories exactos (para no adivinar).** `GHSA-859w-5945-r5v3` (dot-trailing: `curl --request-target /.env/. http://host` — evade el glob del deny para archivos **bajo el root**) y `GHSA-v2wj-q39q-566r` (`server.fs.deny` bypassed with queries: `?raw`, `?import&raw`). El `--request-target` manda el path crudo sin que curl lo normalice.

**Detalle real del camino (fue un loop largo).** Con `.env` (bajo `/app`) el dot-trailing bastó. Pero el `.env` apuntaba **fuera** del allow (`YURUMI_SECRET_STORE=/opt/vitrina/keystore/deploy.secrets`), y `/opt` está fuera de `fs.allow`. Observación decisiva tras muchos intentos : el path `/app/././opt/...` daba **500 ENOTDIR** (no 403), o sea el **allow-check compara el path como string-prefix** ("empieza con `/app`") *antes* de normalizar los `.`, mientras el `readFile` usa el path ya normalizado por Node → cruza el allow. El `.` final evadía el allow pero rompía el `readFile` (ENOTDIR sobre archivo regular). La combinación que finalmente sirvió el contenido crudo del archivo fuera del allow fue `/@fs/opt/vitrina/keystore/deploy.secrets?import&raw??` (query trailing **doble**), que evade `rawRE`/`urlRE` y hace que el plugin lo lea crudo.

**Qué NO funcionó.** Path traversal con `.` a secas (404 por normalización); dot-trailing sobre archivos regulares (`ENOTDIR`); `?raw`/`?url`/`?import` simples (`403`); Host header a `design.yurumi.test` (Vite con `allowedHosts:true`, no cambia nada); leer `/api/tokens` (vive en otro host, fuera de scope). La clave era el separador trailing **doble** (`??`).

**Herramientas.** `curl --request-target`, `search_web`.

## Implicaciones para pentesting/bug bounty
Un Vite dev server expuesto en producción/staging es lectura arbitraria de archivos casi garantizada: ir directo a CVE-2025-30208 (`?raw??`, `?import&raw??`) para archivos fuera del allow y CVE-2025-46565 (dot-trailing) para los denegados bajo el root, sin perder tiempo en traversal `.`. Fingerprint por `/@vite/client` y `/@fs/`. Mapea a OWASP A05 (Security Misconfiguration) / A01.
