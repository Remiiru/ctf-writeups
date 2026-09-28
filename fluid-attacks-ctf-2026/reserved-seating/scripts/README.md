# Scripts

## `protobuf_reserved_field.py`
Revive el campo protobuf `reserved 4` (`bool is_depot_supervisor` en la revisión vieja que corre el server) anexando su tag+valor (`0x20 0x01`) al profile serializado, sin necesidad del `.proto`. Reutilizable para APIs protobuf/gRPC donde el server corre una revisión de schema distinta a la publicada: inyectar campos removidos/reservados por número de tag.
