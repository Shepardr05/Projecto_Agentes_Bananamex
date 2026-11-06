/*
Script: 000_crear_esquema_cfg.sql  (aporte del equipo, NO es del socio formador)

Por qué existe: el script 002 del socio hace CREATE TABLE cfg.fact_sdos_captacoloca_m,
pero el 001 solo crea el esquema "dim". Sin este script, el 002 falla con
'schema "cfg" does not exist'. Se ejecuta ANTES que el 001.
*/
CREATE SCHEMA IF NOT EXISTS cfg;
