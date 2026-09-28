# Stack overflow → sobrescritura de function pointer en parser de records

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Over The Air» (Pwn, Easy, 145 pts; unidad «Ferrolinq»).*

Payload real: record tipo **2** (manifest) `len=0x50`, value = `"A"*0x48 + p64(0x4012d0)` (`factory_console`, hace `execl("/bin/sh")`); luego record tipo **3** (commit) `len=0` → dispara `call rdx`. Offset `0x48` = `rbp-0x228` (handler ptr) − `rbp-0x270` (buffer destino, que es `rbp-0x290 + 0x20`). Binario x86-64 en host aarch64 → offset validado por desensamblado estático; acertó a la primera.

**Concepto.** Un parser de records (`type u8`, `len u16be`, `value`) valida la longitud contra el buffer de **ENTRADA** (`<=0x200`) pero copia con `memcpy` a un buffer **INTERNO** mucho más pequeño, desbordándolo (CWE-121/CWE-787). El buffer interno está adyacente en el stack a un **puntero de función** (handler de `ack`) que otro tipo de record (`commit`) invoca con `call rdx`. Se controla ese puntero y se redirige a una función del binario que ejecuta `/bin/sh` — sin ROP ni leak de libc (el binario no es PIE).

**Explotación.**
1. Reversing del parser (`r2: pd @ sym.main`). Framing: header 3 bytes (`type`, `len` big-endian), `value`.
2. La validación de longitud se compara contra el tamaño del buffer de **entrada** (`<=0x200`), no del destino interno → overflow en el `memcpy`.
3. Offset exacto: buffer destino en `rbp-0x270` (el código suma `+0x20` antes del `memcpy`), puntero de handler en `rbp-0x228` → **0x48** de distancia.
4. Gadget útil: `factory_console`, una función del propio binario que hace `execl('/bin/sh')`, alcanzable como `call rdx`.
5. Payload: record tipo-2 (`manifest`) con `len = offset+8` y `value = relleno + p64(target_fn)`; luego record tipo-3 (`commit`) que dispara `call rdx`.
6. Enviar por el socket (TLS) y usar la shell para leer `/flag.txt`:

```
SHELL OUT: uid=1000(ctf) ...
FLAG{24e0a2830bdd8aae}
```

**Qué NO funcionó.** Asumir que el parser está "hardened" por validar cada longitud (valida contra el buffer equivocado). El binario x86-64 no era ejecutable en host aarch64 → el offset se validó por **análisis estático del disasm** antes de disparar. No hizo falta leak de libc ni ROP (no PIE + función `execl`).

**Herramientas.** `radare2`, `python3` (`socket`/`ssl`/`struct`), `readelf`.

## Implicaciones para pentesting/bug bounty
En parsers de protocolos binarios (firmware, OTA, IoT, appliances), el bug clásico no es el clásico return-address overwrite sino la sobrescritura de **estructuras adyacentes** (function pointers, vtables, flags de estado) cuando la validación de longitud mira el buffer de origen en vez del destino. Buscar `memcpy`/`memmove` cuyo `len` provenga del atacante y verificar contra qué tamaño se valida. Con binario no-PIE y una función tipo `system`/`execl` presente, el exploit es directo sin infoleak. Complementa el triage de.
