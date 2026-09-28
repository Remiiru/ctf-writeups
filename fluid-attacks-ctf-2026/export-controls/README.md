# Excessive data exposure en export CSV: el JSON aplica whitelist, el CSV vuelca el modelo completo

*Resuelto en Fluid Attacks CTF (ctf.ae) — reto «Export Controls» (API, Easy; payroll SaaS «Sueldara»).*

Recon real: sin `/docs`, pero `/openapi.json` seguía servido y el spec lo decía casi literal — `/api/employees/{employee_id}` → *"Send `Accept: text/csv` (or `?download=1`) to receive the reconciliation export row instead of JSON"*. El JSON devuelve el schema `EmployeePublic` (nombre/título/departamento/email); el CSV es una **rama de código distinta** (patrón FastAPI: dos `Response` para la misma ruta) donde no se reaplica el filtro `EmployeePublic`.

**Concepto.** La misma entidad (`employee`) se serializa por dos caminos distintos y solo uno de ellos aplica una whitelist de campos. La representación JSON del endpoint (`GET /api/employees/1`) devuelve una vista recortada (nombre, cargo, departamento), pero la ruta de exportación reutiliza el modelo ORM completo y lo vuelca campo por campo sin filtrar. Es CWE-213 (exposición intencional de información por un canal que se olvidó de aplicar el control del canal principal).

**Identificación.** Al pedir el mismo recurso pero forzando el formato de exportación aparecen campos que el JBSON nunca mostró. Dos disparadores equivalentes:
- `GET /api/employees/1?download=1`
- `GET /api/employees/1` con header `Accept: text/csv`

**Explotación.** El CSV resultante trae `national_id`, `bank_account`, `annual_salary` y un campo `compensation_note` que contenía la flag:

```
FLAG{d817e059988199db}
```

No hubo que romper autenticación ni autorización: el mismo usuario que ve la vista recortada obtiene el volcado completo cambiando el formato de salida.

**Herramientas.** `curl` (probar `?download=1` y `Accept: text/csv`), comparación campo a campo entre la respuesta JSON y la CSV.

## Implicaciones para pentesting/bug bounty
En engagements reales este patrón vive en cualquier ruta paralela de serialización: `export`, `report`, generación de PDF/xlsx, endpoints "download", feeds RSS/CSV, webhooks. La vista JSON de la API suele estar bien recortada porque es la que revisa todo el mundo; el generador de reportes reutiliza el modelo entero (`Model.objects.values()`, `to_dict()`, `DataFrame.to_csv()`) y se salta el serializador con whitelist. **Checklist:** por cada recurso con vista "resumida", buscar variantes `?format=`, `?download=`, `Accept:` alternativos y rutas `/export` / `/report`, y diffear los campos contra la vista principal. Mapea a OWASP API3:2023 (Broken Object Property Level Authorization / excessive data exposure).
