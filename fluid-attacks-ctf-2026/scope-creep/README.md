# Scope Creep: escalada de scope OAuth2 vía refresh_token grant que no re-valida el registro

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae).*

**Concepto.** RFC 6749 §6 exige que al refrescar un token el scope solicitado sea **igual o un subconjunto** del scope original. El servidor validaba el scope en el `password` grant pero se olvidó de re-validarlo en el `refresh_token` grant, así que un refresh puede pedir un scope más amplio del que jamás se autorizó (privilege escalation, CWE-266).

**Identificación.** El endpoint de metadata estándar lo delata:

```
GET /.well-known/oauth-authorization-server
-> grant_types_supported: [password, refresh_token]
-> scopes_supported: [..., reports:read, reports:admin]
```

Pedir directo `reports:admin` en el `password` grant se rechaza con `400 invalid_scope` (esa validación sí existe).

**Explotación.**
1. `password` grant con creds válidas y un scope permitido (`reports:read`) → access_token + **refresh_token**.
2. `refresh_token` grant pidiendo `scope=reports:admin`. El server **no** re-valida contra el registro y emite un access_token elevado.
3. Con el token elevado: `GET /api/reports/rpt-0007` → flag.

```
FLAG{c5cc0a6e9205e91a}
```

**Qué NO funcionó.** Pedir `reports:admin` directamente en el `password` grant (rechazado). La escalada solo aparece al pasar por el refresh.

**Herramientas.** `curl`, lectura del `/.well-known/oauth-authorization-server`.

## Implicaciones para pentesting/bug bounty
En cualquier auth server propio o basado en librería mal configurada, probar el ciclo completo: conseguir un refresh_token con scope mínimo y luego refrescar pidiendo scopes administrativos/adicionales. La misma falla aparece en el `client_credentials` grant, en audience (`resource`/`aud`) que no se re-valida, y en downgrade de `token_type`. Siempre leer `/.well-known/oauth-authorization-server` y `/.well-known/openid-configuration` primero: revelan grants, scopes y endpoints. Mapea a OWASP API5 (Broken Function Level Authorization) y A01 (Broken Access Control).
