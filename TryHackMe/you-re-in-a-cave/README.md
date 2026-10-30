# THM: You're In A Cave

Arranqué con un escaneo rápido de puertos y me encontré con tres servicios: el 80 con Apache y PHP, el 2222 con SSH y algo raro en el 3333. Ese último me llamó la atención porque al conectarme con `nc` apareció una interfaz de texto tipo juego RPG, con prompts para elegir acciones. Lo primero que pensé fue que era un servicio web viejo disfrazado, y no me equivoqué.

```
PORT     STATE SERVICE
80/tcp   open  http
2222/tcp open  ssh
3333/tcp open  dec-notes
```

## El juego y el backend oculto

El menú del juego dejaba elegir cosas como `look`, `inventory`, `attack` y una opción `door` que te pedía resolver un acertijo. Al principio intenté jugarlo "en serio" para ver si daba la flag directo, pero me di cuenta rápido de que el prompt tecleaba contra un backend HTTP. Si ponías ciertos strings, el servidor hacía un `GET http://cave.thm/<input>` y deserializaba la respuesta como un objeto Java con campos `name`, `command` y `output`. El objeto `output` después se pasaba a `/bin/sh -c`, así que había un RCE escondido ahí.

Antes de llegar a eso, un truco simple: probé el comando `lamp` en el juego (una de las acciones "raras") y me devolvió el listado de `/home/cave/src`. Ahí estaba el `RPG.java` completo. No necesitaba ingeniería inversa, solo leer el fuente.

## XXE en action.php

El backend lo servía el Apache del puerto 80. Había un `action.php` que procesaba XML. Lo probé con un payload clásico de entidad externa y confirmé que era vulnerable:

```xml
<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>
```

Con eso leí lo que quise. Primero `RPG.java` para entender el flujo de deserialización y sacar el `serialVersionUID` exacto de la clase `Action`. Con eso ya podía forjar mis propios objetos. Después leí `/etc/passwd`, y por último el archivo más jugoso: la llave GPG privada que estaba en `/var/www/adventurer/`.

## El RCE y la primera flag

Con el `serialVersionUID` en mano, escribí un pequeño forjador en Java que serializaba un objeto `Action` con:

```
command = x";<comando>;echo "
output  = lo que quieras
```

Lo mandé por `action.php` apuntando al 3333 vía el parámetro XML y con eso tuve shell como el usuario `cave`. La primera pregunta del reto pedía "lo raro tallado en la puerta", y la respuesta estaba en el `info.txt` al que llegué por este RCE: una regex extraña.

```
^ed[h#f]{3}[123]{1,2}xf[!@#*]$
```

Esa era la respuesta a la pregunta 1 y también la pista para lo que venía.

## Fuerza bruta contra la regex

La regex tenía pinta de ser una contraseña. La expandí con `exrex` y salieron 1296 candidatos. Los tiré contra el SSH del puerto 2222 para el usuario `door` (que vi en `/etc/passwd`) y uno entró:

```
edfh#22xf!
```

Entré como `door` por SSH y ahí me encontré con el archivo `oldman.gpg` y la llave privada que había exfiltrado antes. La passphrase de la llave estaba escondida en el `info.txt`, después de un escape ANSI `^[[A` que ocultaba la línea real cuando la imprimías normal:

```
breakingbonessince1982
```

Descifré el `.gpg` y salió el nombre de un arma.

```
bone-breaking-war-hammer
```

Esa era la respuesta a la pregunta 2, "qué arma usaste para vencer al esqueleto". Y también era un input: el binario `skeleton` leía la variable de entorno `INVENTORY`. Con eso exportado, `./skeleton` me devolvió una contraseña de texto plano para el usuario `skeleton`.

## Privesc dentro del contenedor

`su skeleton` me dejó leer su `info.txt`, que hablaba de una "pared invisible": una descripción bastante literal del contenedor Docker en el que estaba corriendo todo.

Revisé los permisos de `skeleton` y encontré un `sudo -n /bin/kill` sin contraseña. Por sí solo no servía para gran cosa, pero había un detalle: `/root/start.sh`, el entrypoint del contenedor, era escribible por `skeleton`. Así que lo reescribí con un payload que corriera como root la próxima vez que el contenedor arrancara.

El problema fue cómo reiniciar. Matar PID 1 directo no hace nada (Docker lo protege). Intenté matar el shell padre y no pasó nada. Al final lo que funcionó fue matar el proceso final `/bin/bash` hijo de PID 1, o el `su - cave` según el momento. Cuando ese proceso moría, Docker recreaba el contenedor, corría mi `start.sh` modificado y copiaba el `/root/info.txt` a donde yo pudiera leerlo. De ahí salió la tercera flag:

```
THM{no_wall_can_stop_me}
```

## Escape del contenedor

La última pregunta pedía la flag "afuera", así que había que escapar del contenedor. Confirmé que era privilegiado (se veía en `/proc/self/status` y en los devices montados) y me tiré por el clásico `release_agent` de cgroup v1.

Primer intento, fallo: usé el subsistema `rdma` en el `/etc/mtab`, y el kernel simplemente no disparó el `release_agent`. El `release_agent` solo se ejecuta cuando el `release_agent` está configurado en un cgroup que se **vacía completamente** de procesos. Si dejo un proceso vivo escribiendo el `cgroup.procs`, no pasa nada.

Segundo intento, otro fallo: puse `echo $$ > cgroup.procs`, que es el clásico del exploit público. El problema es que `$$` es el PID del shell padre, y ese shell sigue corriendo el script, así que el cgroup nunca se vacía del todo. Necesitaba que el proceso que escribe el PID **terminara solo**.

Lo que hice fue lanzar un subproceso con `sh -c "sleep 0.1"`, agarrar su PID, y escribir **ese** PID al `cgroup.procs`. Cuando el `sleep` terminaba, el cgroup quedaba vacío y el kernel disparaba el `release_agent` como root en el host.

También corregí dos cosas más: cambiar el subsistema a `memory` (el `rdma` no me servía) y expandir `$host_path` en el `cmd` del `/cmd`, sacando el path desde el campo `perdir=` de `/etc/mtab`.

El `/cmd` quedó corriendo como root en el host. Verifiqué con un `id > /tmp/hostid.txt` y salió `uid=0(root)`. Listo: había roto el aislamiento. Copié el `/root/info.txt` del host y de ahí salió la última flag.

```
THM{digging_down_then_digging_up}
```

## Resumen de respuestas

```
Q1: ^ed[h#f]{3}[123]{1,2}xf[!@#*]$
Q2: bone-breaking-war-hammer
Q3: THM{no_wall_can_stop_me}
Q4: THM{digging_down_then_digging_up}
```