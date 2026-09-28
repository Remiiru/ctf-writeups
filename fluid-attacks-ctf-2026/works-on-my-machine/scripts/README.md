# Scripts

## `vite_fs_deny_bypass.sh`
Cadena completa de lectura arbitraria de archivos contra un Vite dev server expuesto: dot-trailing (`--request-target /.env/.`, GHSA-859w-5945-r5v3) para archivos denegados bajo el root, y `/@fs/<abs>?import&raw??` (query trailing doble, GHSA-v2wj-q39q-566r / CVE-2025-30208) para archivos fuera de `fs.allow`. ⚠️ El loop de bypass fue lo que disparó el gate anti-abuso de la plataforma: correr acotado, sin barridos.
