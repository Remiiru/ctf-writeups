# Clave HMAC hardcodeada en APK → forja de claims de autorización

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Signed Sincerely» (categoría **Mobile**, Easy; Quillaruta Carga, app Android «Despacho»). Superficie móvil.*

Detalle real de la app: clave hardcodeada `qr-despacho-v3-9c41e7a8f2b06d5e` (en `strings.xml`/`BuildConfig.kt`); `RequestSigner.kt` → string canónico `METHOD\npath\nbody` (sin newline final), digest hex en `X-Despacho-Signature`; envelope `{"session":{...},"request":{...}}` con `clearance` (`courier`/`supervisor`/`auditor`) dentro; endpoint `POST /api/v1/dispatch/manifest/consolidated` con `clearance:"auditor"` forjado.

**Concepto.** La app móvil firma cada request con HMAC-SHA256 usando una clave compartida **hardcodeada** en el APK (`strings.xml` / `BuildConfig`) — CWE-798. El envelope incluye los claims de autorización (`clearance`) dentro del propio cuerpo firmado por el cliente, y el gateway confía en ellos solo verificando la firma (sin estado). Al extraer la clave, se re-firma un envelope con `clearance` elevado (`auditor`) y se accede a endpoints restringidos (CWE-639).

**Explotación.**
1. Desempacar el zip decompilado y leer: `strings.xml`/`BuildConfig` (claves), `RequestSigner` (algoritmo + string canónico), `ApiClient` (estructura del envelope), `DispatchApi` (rutas), `Session` (claims: `courier_id`, `depot`, `clearance`, `issued_at`).
2. Extraer el string canónico exacto: `method\npath\nbody` (sin trailing newline), digest hex minúscula en el header `X-Despacho-Signature`.
3. Replicar la serialización del cuerpo **byte a byte** (Kotlin `JSONObject.toString` = JSON compacto sin espacios).
4. Forjar `clearance=auditor` y re-firmar con la clave extraída.
5. `POST` al endpoint restringido con el mismo `Content-Type`/headers y body EXACTO que el firmado.

```
FLAG{ad86b9acfa976595}
```

**Qué NO funcionó.** Fuzzear `clearance` sin firma (rechazado). La firma debe calcularse sobre los **bytes exactos** enviados; re-serializar distinto invalida la firma.

**Herramientas.** `unzip`, `python3` (`hmac`/`hashlib`/`json`), `curl`.

## Implicaciones para pentesting/bug bounty
Un gateway "stateless" que confía en claims firmados por el cliente es explotable en cuanto la clave de firma vive en el binario (hardcoded key es la regla, no la excepción, en apps móviles). Extraer `strings.xml`/`BuildConfig`/`res/raw` y buscar secretos; reproducir el canonical string exacto es el 90% del trabajo. Los claims de autorización nunca deben venir del cliente aunque estén firmados con clave que el cliente posee. Mapea a OWASP MASVS (crypto/storage) + API1/API5.
