# Writeup: Phantom Fob (TryHackMe)

Arranqué como cualquier reto de red: `nmap -sS -sV -p- 10.65.128.178` y me devolvió tres puertos abiertos. SSH en el 22, un Flask en el 8080 que se identificaba como "Instrument Cluster", y algo raro en el 29536 que no reconocía a primera vista. El nombre del reto, Phantom Fob, ya me tiraba para el lado de CAN bus o key fobs inalámbricos.

## Reconocimiento inicial

El dashboard del 8080 tenía cuatro botones: LOCK, HORN, IMMOB_ARM e IMMOB_DISARM. Curioso que no hubiera Unlock. Leí un poco el HTML y no había nada escondido, todo apuntaba a que el estado real del "vehículo" vivía en otro lado. El puerto 29536 me llamó la atención porque al conectarme con `nc` me respondió con texto plano estilo protocolo, y rápido reconocí el handshake de socketcand:

```
< hi >
< open can0 >
< rawmode >
< send 585 8 ... >
```

O sea, tenía acceso crudo al bus CAN. El reto no iba de web, iba de forjar tramas.

## Mapeando el bus

Me conecté con socketcand y dejé corriendo un `< rawmode >` para loguear todo lo que pasaba en `can0`. Al principio lo único que veía era tráfico periódico, mucho ruido de IDs constantes. Anoté los IDs que aparecían y con qué frecuencia.

Después de un rato pulsando botones en el dashboard para generar eventos, distinguí dos IDs que me interesaban:

- `0x595`: emitía tramas cada ~1 segundo, y el byte[2] incrementaba constantemente. Latido del vehículo, con un contador visible en claro.
- `0x585`: aparecía **solo** cuando pulsaba un botón. Ese era el key fob.

Capturé una pulsación de LOCK limpia:

```
585  8  1a 77 aa dd 24 7b XX YY
```

Y luego otra de HORN:

```
585  8  3c 77 ab dd 24 0e XX YY
```

Comparando las dos, los bytes fijos eran `b1=0x77`, `b3=0xdd`, `b4=0x24`. Los que cambiaban eran `b0`, `b2` y `b5`. `b5` claramente era el comando (LOCK=0x7b, HORN=0x0e), y `b2` moviéndose en cada pulsación tenía pinta de counter. `b0` era la incógnita: el byte de autenticación que el fabricante jura que "no se puede copiar".

## Primer intento: XOR (que no funcionó)

Antes de tocar nada miré un writeup público de este mismo reto por si acaso, y decía que la operación era `auth = counter XOR key XOR command`. Probé calcular `key = b0 XOR b2 XOR b5` con la captura de LOCK, y me dio un valor. Forjé una trama ARM desde una base LOCK cambiando b0 y b5, la mandé, y... nada. El dashboard no movió el immob. Pensé que había leído mal la captura, repetí con otra, mismo resultado. El XOR no cuadraba con esta instancia.

El detalle es que en esta instancia del reto los IDs y el layout estaban randomizados respecto al writeup público, así que asumir la misma operación fue un error mío. Descarté XOR.

## El hallazgo: es suma, no XOR

Volví al análisis mirando pares de comandos distintos capturados en una ventana corta de tiempo, para que el counter `b2` fuera casi el mismo entre ambos (el broadcast de 0x595 lo mantenía chico). Comparé dos pulsaciones consecutivas, LOCK y HORN:

```
LOCK:  b0=0x1a  b2=0xaa  b5=0x7b
HORN:  b0=0x3c  b2=0xab  b5=0x0e
```

Resté mentalmente y vi que `b0 - b5` daba lo mismo en ambos casos salvo por el corrimiento del counter. Es decir, la relación era **aritmética, no XOR**:

```
b0 = (counter + key + command) mod 256
```

O sea que la "key" se recupera con una sola captura legítima:

```python
key = (b0 - b2 - b5) % 256
```

Con la captura de LOCK de arriba: `key = (0x1a - 0xaa - 0x7b) % 256 = 0xf5`.

## Validación de la forja

Antes de barrer nada, quise probar que la fórmula era real y no una casualidad. Capturé una base LOCK fresca, calculé su `key`, y construí una trama ARM cambiando `b2` al counter actual del broadcast (lo sacaba de la última trama de 0x595), `b5=0xbc` y recalculando `b0`. La mandé por socketcand:

```
< send 585 8 XX 77 CC dd 24 bc YY ZZ >
```

El dashboard me devolvió `immob=True`. Confirmado: forja cross-command funcionando, no era replay.

## El segundo problema: la ventana del counter

Con la fórmula validada armé el sweep de los 256 valores de `b5` para encontrar el unlock. Capturaba LOCK, calculaba key, y barría `for cmd in range(256): b0=(b2+key+cmd)%256; send(...)`. Y no pasó nada. Cero. Ni un cambio en el dashboard.

Pensé primero que el command unlock quizás no estaba en el rango 0x00-0xFF de `b5`, aunque el enunciado decía lo contrario. Pero antes de asumir eso, revisé el timing. El sweep tardaba como 0.5s por ronda, y el counter `b2` que el receptor valida viene del broadcast 0x595 que se actualiza cada ~1s. O sea, entre que capturaba la base y terminaba el sweep, el counter ya había caducado y el receptor estaba rechazando todo por counter viejo.

El fix fue reestructurar el bucle: **una trama por command, con base fresca capturada justo antes de cada envío**, y recalcular `b2` con el último broadcast antes de mandar. Así cada intento caía dentro de su propia ventana válida. Técnicamente:

```python
for cmd in range(256):
    base = capture_one_fob_frame()      # LOCK fresca
    key  = (base[0] - base[2] - base[5]) % 256
    counter = latest_broadcast_b2()      # del 0x595 actual
    auth = (counter + key + cmd) % 256
    send_fob(auth, counter, cmd)
```

Reduje también el número de conexiones a socketcand (una sola sesión, varias rondas por conexión) porque antes me había comido timeouts del servicio por saturarlo con reconexiones.

## Flag

A la ronda ~30, con `cmd=0xd7`, el dashboard cambió a unlocked y el stream de `/events` soltó la flag:

```
THM{C4r_H4cking_is_kind4_c00l}
```

## Notas sueltas que me llevo

El fabricante del "Phantom Fob" dice que el comando unlock no se puede copiar, pero el counter que alimenta la autenticación lo publica el propio vehículo **en claro** en el bus cada segundo. Y la key se deduce de una sola trama observada con una resta de módulo 256. No hay criptoanálisis acá, solo aritmética y prestar atención a la ventana temporal del counter.

Lo que me costó fue doble: primero creer el writeup público sobre XOR cuando esta instancia usaba suma, y después no darme cuenta de que el sweep tardaba más que la ventana del counter. Los dos errores tienen la misma raíz: asumir cosas en vez de medirlas en el bus.

`THM{C4r_H4cking_is_kind4_c00l}`