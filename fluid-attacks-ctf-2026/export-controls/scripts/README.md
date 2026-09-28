# Scripts

## `export_controls_csv_dump.sh`
Compara la vista JSON (whitelist `EmployeePublic`) contra el export CSV (`?download=1` / `Accept: text/csv`) del mismo recurso, donde el redactado no se reaplica y aparecen campos sensibles + la flag. Reutilizable para endpoints con rutas paralelas de serialización (export/report/pdf/xlsx).
