# Roles: usuario y admin

El agente exige login (`--user NOMBRE` + contraseña). El rol decide qué herramientas existen y qué columnas de la base puede leer.

## Qué puede hacer cada rol

| | `usuario` (analista de negocio) | `admin` (data steward) |
|---|---|---|
| Consultar saldos, transacciones y clientes (SQL de solo lectura) | Sí | Sí |
| Columnas personales `fec_nac`, `genero_cte` (clasificación *Restringida*) | **No**: la base lo rechaza | Sí, solo agregados; queda en auditoría |
| `list_tables`, `get_data_model_guide` | Sí | Sí |
| `search_governance_knowledge` (política, catálogo, GOV.UK/ONS) y `web_search` | Sí | Sí |
| `run_governance_checks` (reglas DQ-01..11) | No | Sí |
| `data_quality_profile` | No | Sí (valores personales enmascarados) |
| `describe_table` | No | Sí (muestra con datos personales enmascarados) |
| `get_audit_log` | No | Sí |

## Cómo se aplica (tres capas)

1. **Agente** (`src/agent.py`): filtra las tools según el rol (`auth.can`) y le dice al LLM cuál es el rol del usuario.
2. **Servidores MCP** (`@auth.guarded` en `src/auth.py`): cada tool vuelve a validar el rol, responde `ACCESO DENEGADO` y registra el intento. Sin rol definido o con un rol inválido se asume `usuario`.
3. **PostgreSQL** (`scripts/load_db.py`): dos roles de solo lectura.
   - `steward_ro` (admin): `SELECT` sobre todo.
   - `steward_usuario` (usuario): `SELECT` por columna, sin `fec_nac` ni `genero_cte`. Falla incluso `SELECT *`, `WHERE genero_cte = ...` y `GROUP BY genero_cte`.

## Usuarios

```
python src/auth.py add lalo admin
python src/auth.py add analista usuario
```

Se guardan en `users.json` (ignorado por git) con contraseña hasheada con scrypt. Para scripts, la contraseña puede venir en la variable `STEWARD_PASSWORD`.

Si la base ya estaba cargada antes de los roles, corre una vez `.\run.ps1 load-db` (no borra datos) para crear `steward_usuario`.

## Auditoría

Cada llamada a una tool (permitida o denegada) se agrega a `logs/audit.jsonl` (ignorado por git): hora, usuario, rol, tool, si se permitió y argumentos (con el SQL). El admin la consulta con la tool `get_audit_log`.

## Límites (decirlos en la presentación)

- Es control de acceso de **aplicación**. Con PostgreSQL embebido todo corre en la misma máquina: quien tenga terminal puede lanzar un servidor MCP con `STEWARD_ROLE=admin` y el Postgres embebido no usa contraseñas. La protección real requiere un PostgreSQL externo (`USE_EMBEDDED_DB=0` con `PGUSER`/`PGPASSWORD` y `PGUSER_USUARIO`/`PGPASSWORD_USUARIO`).
- El admin puede leer columnas personales fila por fila con SQL libre: lo frenan el prompt (solo agregados) y la auditoría, no la base.
- Los casos R1 a R4 de `run_test_cases.py` dependen de que el LLM obedezca; los roles en sí se prueban sin LLM con `pytest`.
