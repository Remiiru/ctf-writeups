# Fluid Attacks CTF 2026 (ctf.ae)

Writeups de los retos que resolví en el CTF de [Fluid Attacks](https://ctf.ae) de septiembre de 2026
(26 y 27 de septiembre). Fue un evento estilo *jeopardy* con foco fuerte en web y API, más algunos
de mobile, pwn y reversing.

Cada carpeta tiene el writeup (idea del bug, cómo lo identifiqué, la explotación paso a paso, qué
**no** funcionó y las implicaciones para pentesting/bug bounty) y, cuando aplica, un PoC reproducible
en `scripts/`. Los PoCs están pensados como plantilla: los valores concretos (endpoints, offsets,
nombres de campos) se ajustan a cada instancia.

## Retos

| Reto | Categoría | Técnica |
|---|---|---|
| [Nothing To Sign Here](./nothing-to-sign-here/) | Web | JWT `kid` confusion a clave HMAC vacía |
| [Works On My Machine](./works-on-my-machine/) | Web | Vite `fs.deny` bypass (CVE-2025-30208) |
| [Time Served](./time-served/) | Web | Token de reset UUIDv1 predecible |
| [Tenant Improvement](./tenant-improvement/) | Web | Cross-tenant `signed_id` en Active Storage |
| [The Scenic Route](./the-scenic-route/) | Web | SSRF + open-redirect |
| [Render Unto Caesar](./render-unto-caesar/) | Web | HTML-render → LFI → SSRF a chromedriver |
| [Warning Signs](./warning-signs/) | Web | `max_input_vars` rompe CSP → XSS reflejado |
| [Scope Creep](./scope-creep/) | Web | Escalada de scope OAuth2 vía `refresh_token` |
| [Export Controls](./export-controls/) | API | Excessive data exposure vía export CSV |
| [Under The Score](./under-the-score/) | API | Header spoofing underscore/dash (nginx + gunicorn) |
| [Reserved Seating](./reserved-seating/) | API | Protobuf reserved-field revival |
| [Signed Sincerely](./signed-sincerely/) | Mobile | HMAC hardcodeada en APK |
| [Over The Air](./over-the-air/) | Pwn | Stack overflow → function pointer (parser OTA) |
| [Off The Menu](./off-the-menu/) | Reversing | Protocolo binario propietario + opcode oculto |

> Nota: las flags y los datos de las instancias corresponden al evento; los PoCs se comparten con fin
> educativo y de referencia metodológica.
