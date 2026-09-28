# Scripts

## `warning_signs_csp_xss.py`
Rompe la CSP mandando >1000 vars GET (warning `max_input_vars` → "headers already sent") e inyecta un XSS reflejado partiendo el `<` entre parámetros (`zone`=`%3` + `sign`=`c…`) con doble-encoding de `"`/`&`/`>`; el `svg/onload` lee `localStorage.duty_key` y exfiltra al sink same-origin `/ledger`. Ajustar el nombre del parámetro reflejado (`ref`) y el sink a la instancia. Reutilizable ante CSP servida por la app (frágil a cualquier output previo) y filtros que decodifican después de sanitizar.
