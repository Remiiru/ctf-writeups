#!/usr/bin/env python3
# Off The Menu (Fluid Attacks CTF 2026, Reversing/protocolo) -- cliente del protocolo binario "QF"
# de la app Android FleetLink. Reimplementa el codec y usa el opcode oculto OP_0x7F (FieldDiagnostics).
# Uso:    ./qf_protocol_client.py <host> [port]
# Ejemplo: ./qf_protocol_client.py <inst>.chal.ctf.ae 443
#
# Frame: magic(2) opcode(1) len(2 BE) payload(XOR keystream) CRC-16/CCITT-FALSE  (magic FUERA del CRC)
# Keystream LCG: state=(state*1664525+1013904223)&0xFFFFFFFF ; byte=(state>>16)&0xFF
# seed = (nonce ^ (opcode*0x01010101)) & 0xFFFFFFFF ; nonce=0 hasta el handshake.
# Transporte: el config decia :9410 cleartext pero solo :443 esta abierto -> TLS/SNI.

import sys, ssl, socket, struct

HOST = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 443
MAGIC = b"QF"

def keystream(opcode, nonce, n):
    state = (nonce ^ (opcode * 0x01010101)) & 0xFFFFFFFF
    out = bytearray()
    for _ in range(n):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        out.append((state >> 16) & 0xFF)
    return bytes(out)

def crc16_ccitt_false(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc

def build(opcode, plain, nonce):
    enc = bytes(a ^ b for a, b in zip(plain, keystream(opcode, nonce, len(plain))))
    body = struct.pack(">BH", opcode, len(enc)) + enc      # opcode+len+payload (dentro del CRC)
    return MAGIC + body + struct.pack(">H", crc16_ccitt_false(body))

def parse(frame, nonce):
    assert frame[:2] == MAGIC
    opcode = frame[2]
    ln = struct.unpack(">H", frame[3:5])[0]
    enc = frame[5:5+ln]
    return opcode, bytes(a ^ b for a, b in zip(enc, keystream(opcode, nonce, len(enc))))

def recv_frame(s):
    hdr = s.recv(5)
    ln = struct.unpack(">H", hdr[3:5])[0]
    return hdr + s.recv(ln + 2)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection((HOST, PORT), timeout=15) as raw:
    with ctx.wrap_socket(raw, server_hostname=HOST) as s:   # SNI = host
        # OP_01 handshake -> OP_81 devuelve nonce
        s.sendall(build(0x01, b"", 0))
        op, body = parse(recv_frame(s), 0)
        nonce = struct.unpack(">I", body[:4])[0] if len(body) >= 4 else 0
        print(f"[*] handshake op={op:#x} nonce={nonce:#x}")

        # OP_02 auth con creds demo del fleetlink_config.json
        s.sendall(build(0x02, b'{"user":"demo","pass":"demo"}', nonce))
        op, body = parse(recv_frame(s), nonce)
        print(f"[*] auth op={op:#x} -> {body[:80]!r}")

        # OP_7F FieldDiagnostics (opcode oculto) -> environment con SUPPORT_TOKEN
        s.sendall(build(0x7F, b"", nonce))
        op, body = parse(recv_frame(s), nonce)
        print(f"[*] diag op={op:#x}:")
        print(body.decode(errors="replace"))
