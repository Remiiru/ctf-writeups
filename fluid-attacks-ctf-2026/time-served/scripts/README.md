# Scripts

## `uuidv1_reset_predict.py`
Reconstruye el token de reset UUIDv1 de la víctima (admin) a partir de un token UUIDv1 propio (fija `node`+`clockseq`) y el timestamp del evento de reset tomado de un endpoint de auditoría público. Sondea `/recover/<token>` con candidatos en ms exactos, **espaciado** para no disparar la protección anti-abuso de la plataforma. Reutilizable para cualquier token de seguridad generado con UUIDv1/tiempo/`Math.random`.
