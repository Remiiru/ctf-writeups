# Fools Mate - Writeup

Target: `10.67.176.93`. Arranco con el scan de siempre.

```
rustscan -a 10.67.176.93 -- -sV -sC
```

Solo dos puertos: `22/tcp` SSH y `80/tcp` HTTP. El banner del 80 tira Express y el `<title>` de la página es "Endgame Trainer". Under the hood es Node, así que ya me imagino el stack: algún endpoint REST para mover piezas, probablemente validando el tablero con `chess.js`.

Antes de meterme al navegador, reviso el vault porque el nombre "Fools Mate" me suena. Y sí, hay un walkthrough viejo de una variante del mismo reto: "Fools Mate **Revenge**". Ese se resolvía con prototype pollution server-side. El endpoint era `/api/settings`, mandabas algo con `constructor.prototype` en el payload, contaminabas `Object.prototype.unlocked = true` y recién ahí el backend te dejaba reclamar la recompensa. Buen material, pero ojo: ese es "Revenge", no "Fools Mate". Apostar a que son idénticos es justo el tipo de trampa que me suele dejar veinte minutos peleando con un endpoint que ni existe.

Cargo la página y me encuentro con un tablero de ajedrez, posición mate-en-1, un botón de "reset" y poco más. Miro el HTML. La lógica del juego vive en un `app.js` que importa `chess.js` del lado del cliente. Eso ya huele a lo de siempre: la validación de jugadas se hace en el navegador, y el backend es solo un cartero que recibe `from` y `to` y decide si fue mate.

Abro el panel de red con el tablero corriendo y hago un mate de prueba para ver el tráfico. Confirmo la hipótesis: el front manda un `POST /api/move` con `{"from": "...", "to": "..."}` y el server contesta con un JSON que incluye `status`, `winner` y, si corresponde, `flag`. No hay firma, no hay nonce, no hay validación de que la jugada realmente sea legal.

Primer intento antes de tirarme al mate directo: pruebo si existe el endpoint de `/api/settings` de la variante Revenge, por si acaso lo dejaron pegado.

```
curl -s -c jar http://10.67.176.93/api/state
curl -s -b jar http://10.67.176.93/api/settings
```

`/api/state` contesta con la posición inicial (sin problemas). `/api/settings` da 404. Bien, confirmado: esta build no tiene el gate de recompensa. También pruebo `/api/reset` y también da 404. Nada que romper por ese lado.

Ahora lo obvio, que justamente era lo que el nombre del reto me estaba gritando: la defensa es *client-side*. El backend no revalida el mate, así que no necesito tocar `chess.js` ni preocuparme de que la jugada sea legal según las reglas completas del ajedrez. Solo necesito mandarle al server dos casillas que él considere válidas para entrar a `checkmate`.

El mate del loco es el candidato perfecto. Si la posición es la clásica (peones f2, g2, blancas a mover), la jugada ganadora es `a1` a `a8`: la torre corta por la columna a y da mate porque el rey negro no tiene escape. Ese es el "fool's mate" que le da nombre al reto y a la flag.

Le pego directo por API:

```
curl -s -b jar -X POST http://10.67.176.93/api/move \
  -H 'Content-Type: application/json' \
  -d '{"from":"a1","to":"a8"}'
```

Respuesta:

```json
{"status":"checkmate","winner":"white","flag":"THM{cl13nt_s1d3_ch3ckm4t3}"}
```

Sin `unlocked`, sin gate, sin nada. El server aceptó el mate, lo reconoció como tal y me entregó la flag de una.

Lo que me cobró tiempo: haber asumido al principio que este era idéntico a "Fools Mate Revenge" y saltar directo a preparar el payload de prototype pollution con `constructor.prototype`. Antes de siquiera probar el endpoint de settings perdí un par de minutos armando el exploit mentalmente, y cuando llegué a pegarle y me devolvió 404, tuve que retroceder. La lección (que ya dejé anotada en el vault) es que cuando dos retos comparten nombre base, hay que verificar la build actual antes de reciclar la técnica. La variante "Revenge" era ese reto con la mitigación del backend agregada. Esta versión, sin el apellido, es la original: el mate directo funciona.

Flag: `THM{cl13nt_s1d3_ch3ckm4t3}`