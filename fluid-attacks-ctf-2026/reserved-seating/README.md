# Reserved Seating: revivir un campo protobuf `reserved` por desajuste de revisión

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae). Categoría Web/API/Mobile.*

**Concepto.** En el wire, Protobuf **no lleva nombres de campo, solo el número de tag**. Marcar un campo como `reserved N` en una revisión nueva del `.proto` no impide que un server que corre una revisión **vieja** interprete ese tag con su significado original. Es un fallo de inicialización/config insegura (CWE-1188) que habilita escalada de privilegios (CWE-266).

**Identificación.**
- `GET /api/v1/schema` reporta que el server corre **rev11**.
- En `legacy/*.proto` (rev11) el campo 4 era `bool is_depot_supervisor`.
- En rev12 ese campo pasó a `reserved 4` — pero el binario en producción sigue en rev11 y "lo toma at face value".

**Explotación.**
1. Sesión con las creds demo hardcodeadas.
2. `GET /api/v1/profile` (respuesta protobuf) → tomar el mensaje serializado.
3. **Anexar `\x20\x01`** al mensaje: tag `(4<<3)|0 = 0x20` (field 4, wire type varint) + varint `1` (true).
4. `POST /api/v1/profile/sync` con `Content-Type: application/x-protobuf` y el mensaje modificado → el rol pasa a `depot_supervisor`.
5. `GET /api/v1/rota/supervisor` (antes `403`) → `payroll_export_key` / flag.

```
FLAG{628c0260556f750c}
```

**Herramientas.** `curl`, construcción manual del byte de tag protobuf, `protoc`/decodificador para leer el mensaje base.

## Implicaciones para pentesting/bug bounty
Ante cualquier API binaria protobuf/gRPC: pedir el schema (`/schema`, reflection gRPC) y comparar la revisión activa contra `.proto` viejos o `reserved`. Campos removidos o reservados siguen siendo inyectables por número de tag si el server no valida contra la revisión declarada. Es el equivalente protobuf del mass-assignment: campos que el cliente "no debería" mandar pero que el server acepta. Revisar también campos `deprecated` y oneof mal manejados. Mapea a OWASP API6/API3.
