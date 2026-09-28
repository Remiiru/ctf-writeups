# Scripts

## `despacho_hmac_forge.py`
Forja y firma un envelope con `clearance: auditor` usando la clave HMAC-SHA256 hardcodeada en el APK (`qr-despacho-v3-…`), reproduciendo el string canónico exacto (`METHOD\npath\nbody`) y la serialización compacta de Kotlin. Reutilizable para cualquier gateway stateless que confíe en claims de autorización emitidos por un cliente que posee la clave de firma. Los nombres de campo (`courier_id`/`depot`/`session`/`request`) se ajustan a lo que muestre el decompilado.
