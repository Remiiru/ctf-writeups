# Off The Menu: reversing de protocolo binario propietario (app Android FleetLink)

*Resuelto el 2026-09-27 en Fluid Attacks CTF (ctf.ae). Categoría Reversing / protocolo embebido.*

**Concepto.** Una app Android en Kotlin (FleetLink) habla un protocolo binario propietario "QF". Hay que reimplementar el códec en Python (el reto avisa: *"nc will get you nowhere"*) y descubrir un **opcode oculto de diagnóstico** que el servidor sigue atendiendo aunque el cliente lo tenga desactivado por flag de build (functionality no documentada expuesta — CWE-441).

**Formato del frame QF.**
```
magic(2) | opcode(1) | len(2 BE) | payload(XOR keystream) | CRC-16/CCITT-FALSE
```
- El `magic` queda **fuera** del CRC.
- **Keystream** por LCG: `state = (state*1664525 + 1013904223) & 0xFFFFFFFF`, byte `= (state>>16) & 0xFF`.
- **Seed**: `seed = (nonce ^ (opcode*0x01010101)) & 0xFFFFFFFF`, con `nonce=0` hasta completar el handshake.

**Reversing.** Decompilando el APK se recupera el códec y las constantes. El opcode oculto es **`OP_0x7F` (FieldDiagnostics)**, detrás de `BuildConfig.FIELD_DIAG=off` en el cliente — pero el server igual responde y devuelve un bundle con las variables de entorno (`environment`).

**Flujo de explotación.**
1. Handshake: `OP_01` → `OP_81` (el server devuelve el `nonce`).
2. Auth: `OP_02` con las creds demo de `fleetlink_config.json` → `OP_82`.
3. `OP_7F` → `environment.SUPPORT_TOKEN` (la flag).

**Transporte.** El `fleetlink_config.json` decía `:9410` en cleartext, pero solo `:443` estaba abierto → el transporte real va por **TLS/SNI** (envolver el socket en TLS con `server_hostname=host`).

```
FLAG{faaaf60896d3fd7b}
```

**Qué NO funcionó.** Conectar a `:9410` (filtrado) y en cleartext. Asumir que el config refleja el transporte real.

**Herramientas.** jadx/apktool (decompilar), `python3` (`socket`, `ssl`, `struct`, implementación del LCG y CRC-16/CCITT-FALSE).

## Implicaciones para pentesting/bug bounty
Para apps móviles/IoT con protocolo propietario: la respuesta casi siempre está en **decompilar el cliente y reimplementar el códec**, no en fuzzear a ciegas. Buscar opcodes/comandos gateados solo por `BuildConfig`/flags del cliente — el servidor rara vez los aplica su lado (functionality oculta = superficie real). Y nunca confiar en el puerto/transporte del config: escanear qué está realmente abierto y probar TLS aunque el config diga cleartext. Complementa la metodología de (distinguir cripto real de lógica de protocolo).
