# Header spoofing por conflation guion/guion_bajo (nginx ↔ gunicorn)

*Resuelto el 2026-09-26 en Fluid Attacks CTF (ctf.ae) — reto «Under The Score» (API, Medium; el nombre es el pun: under**score** = guion bajo `_`).*

**Concepto.** nginx pisa un header de confianza (`proxy_set_header X-Internal-Role ""`) para neutralizar el valor del cliente, pero solo el nombre **con guiones**. Con `underscores_in_headers on`, el cliente manda el mismo nombre con **guion bajo** (`X_Internal_Role`) y nginx lo reenvía intacto. Gunicorn (con `--header-map dangerous`) normaliza guiones y guiones bajos al mismo `HTTP_X_INTERNAL_ROLE` en el entorno WSGI, así que Flask lee el valor inyectado por el atacante como si fuera el header de confianza (CWE-444 interpretation conflict → CWE-290 auth bypass).

**Explotación.**
1. Leer `nginx.conf`: identificar el header de confianza (`X-Internal-Role`) que el gateway blanquea en el vhost público y fuerza en el de auditoría.
2. Notar las pistas de config: `underscores_in_headers on` + `--header-map dangerous`.
3. Confirmar en el código Flask que la autorización depende SOLO de ese header.
4. Enviar el header con guion bajo al vhost público:
```
curl -H "X_Internal_Role: auditor" https://<host>/...
-> "restricted_note":"Judicial disclosure key: FLAG{2f2759ef838ad231}"
```
El header con guiones normal se pisa; el de guion bajo no.

```
FLAG{2f2759ef838ad231}
```

**Qué NO funcionó.** Intentar alcanzar el vhost de auditoría (`:8081`, "solo VPN") — no está publicado; el camino es colar el header por el vhost público. Referencia: gunicorn issue #2799.

**Herramientas.** `curl`.

## Implicaciones para pentesting/bug bounty
Siempre probar la variante con guion bajo de cualquier header de confianza (`X_Forwarded_For`, `X_Real_IP`, `X_Internal_*`, `X_Admin`) cuando hay un proxy delante: nginx con `underscores_in_headers on` los reenvía y el backend (gunicorn/uwsgi/PHP `getallheaders`) puede conflarlos con la versión de guiones. Es un bypass de trusted-header y una primitiva de request smuggling ligero. Mapea a OWASP A01/A05.
