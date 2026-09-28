# Scripts

## `scenic_route_ssrf.sh`
SSRF con filtro de IP interna evadido por open-redirect (`/go?next=`) + descubrimiento de servicios Docker por nombre (leyendo los estados de conexión como oráculo) hasta el control plane interno. ajustar `PROBE`/`REDIR`/nombres a la instancia. Reutilizable: inventariar todos los open-redirect del scope como munición de bypass de allow-lists SSRF.
