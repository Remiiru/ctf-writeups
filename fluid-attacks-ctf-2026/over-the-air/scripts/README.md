# Scripts

## `ota_stack_overflow_pwn.py`
Exploit del parser de records OTA: desborda el buffer interno (validación de longitud contra el buffer de entrada, no el destino) para sobrescribir el puntero de handler adyacente (offset `0x48`) con `factory_console` (`execl("/bin/sh")` @ `0x4012d0`), y dispara `call rdx` con el record `commit`. Sin ROP ni leak (binario no-PIE). Transporte TLS. Los offsets/dirección se ajustan a lo que muestre el disasm (radare2) del binario del reto.
