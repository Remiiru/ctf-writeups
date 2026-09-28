# Scripts

## `header_underscore_spoof.sh`
Bypass de header de confianza por conflation guion/guion_bajo entre nginx (`underscores_in_headers on`) y gunicorn (`--header-map dangerous`). Envía la variante con guion bajo (`X_Internal_Role`) que nginx no pisa. Reutilizable para cualquier header de confianza (`X_Forwarded_For`, `X_Real_IP`, `X_Admin`…) detrás de un proxy con esa config.
