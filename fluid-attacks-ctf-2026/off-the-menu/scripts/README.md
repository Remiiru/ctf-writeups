# Scripts

## `qf_protocol_client.py`
Reimplementación completa del códec del protocolo binario "QF" de la app Android FleetLink (magic+opcode+len+payload XOR keystream LCG + CRC-16/CCITT-FALSE), sobre TLS/SNI. Hace handshake (OP_01→OP_81), auth (OP_02) y dispara el opcode oculto **OP_0x7F (FieldDiagnostics)** que el server atiende aunque el cliente lo tenga gateado por `BuildConfig` → devuelve `environment` con el `SUPPORT_TOKEN`. Ajustar creds/estructura de payload a lo que muestre el decompilado. Reutilizable como plantilla para reimplementar cualquier protocolo binario propietario de mobile/IoT.
