# Bypass-Me – Writeup

Empecé por descomprimir el archivo entregado:

```bash
unzip bypass-me_z7MR1xz.zip -d ex/bypass-me
```

Dentro, encontré un script Python `limbo-arc.py` y un directorio `archive/` con algunos archivos de texto en `pub/`. El `README.txt` mencionaba que había un bloque de mantenimiento sellado que el cliente no debería entregar, y que era justo lo que necesitaba recuperar.

Primero revisé el contenido de los archivos públicos, por si había pistas:

```bash
cat ex/bypass-me/archive/pub/*
```

Eran mensajes genéricos de bienvenida, cambios, soporte y estado. Nada útil directamente. El verdadero objetivo claramente estaba en el comportamiento del cliente.

Le eché un vistazo al `limbo-arc.py`. Es un script de recuperación de bloques que usa un catálogo interno. Lo primero que hice fue correrlo como sugería el README:

```bash
python3 limbo-arc.py --list
```

Salida:

```
 1  pub/welcome.txt
 2  pub/changelog.txt
 3  pub/support.txt
 4  pub/status.txt
```

Solo muestra los primeros cuatro. Intenté pedir el bloque 5:

```bash
python3 limbo-arc.py 5
```

> limbo-arc: block 5 is not allocated on this node

Rechazado. Probé con 0:

```bash
python3 limbo-arc.py 0
```

Y ahí apareció:

```
flag{16b1t_bl0ck_0_und3rfl0w_2_r00t}
```

Funcionó. Pero quería entender por qué.

Volviendo al código, la función `lookup(block)` hace esto:

```python
block &= 0xFFFF
if block > PUBLIC_BLOCKS:
    return None
slot = block - 1
if slot < len(CATALOG):
    return CATALOG[slot]
return None
```

El problema está en que **no valida que `block` sea mayor que 0**. Cuando paso `0`, el `& 0xFFFF` lo deja en 0, luego `slot = -1`, y `CATALOG[-1]` en Python devuelve el último elemento de la lista, que es `"maint/keys.blk"`.

Ese bloque no existe en el filesystem. El cliente lo tiene ofuscado en una variable `_SEALED` y una clave `_K`. Cuando se accede, el `main()` detecta que el path termina en `.blk` y llama a `unseal()`, que hace un XOR entre el blob decodificado en base64 y la clave `_K`.

Verifiqué que también funciona con `65536`, porque `65536 & 0xFFFF == 0`. Lo mismo con `131072`, etc. Cualquier múltiplo de 65536 cae en el mismo bucket por el truncamiento de 16 bits.

El error clave fue asumir que `block > PUBLIC_BLOCKS` era suficiente, sin considerar el caso `block = 0`. Y confiar en que el truncamiento `& 0xFFFF` era un saneamiento, cuando en realidad abre una condición de subdesbordamiento (underflow) en el índice.

La solución sería validar `block` entre 1 y `PUBLIC_BLOCKS`, inclusive. Algo como:

```python
if not (1 <= block <= PUBLIC_BLOCKS):
    return None
```

Pero claro, eso no estaba hecho.

Así que la flag es:

```
flag{16b1t_bl0ck_0_und3rfl0w_2_r00t}
```