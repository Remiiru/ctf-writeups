# Scripts

## `jwt_kid_empty_key_forge.py`
Forja un JWT `HS256` con `kid` arbitrario y `role` elevado firmado con **clave HMAC vacía** (`b""`), explotando el fallback `SIGNING_KEYS.get(kid, "")` de `resolve_session_key`. Genera y envía el token en el mismo proceso para evitar un canal que redacta secretos (que corrompe el token → `UnicodeDecodeError` espurio). Reutilizable para cualquier servicio JWT con resolución de clave por `kid` que degrade a clave por defecto/vacía.
