# Guía de demostración (≈ 8 min)

**Objetivo del Sprint:** probar que el agente *consume la base de datos*, ejecuta consultas y usa los resultados.

## Antes de la demo (checklist)
- [ ] Ollama abierto · [ ] `.env` completo
- [ ] `.\run.ps1 check` → todo en `[ OK ]`
- [ ] `.\run.ps1 pytest` → 12 passed

## Guion
1. **Arquitectura (1 min)** — muestra `docs/arquitectura.png`: agente, dos servidores MCP, PostgreSQL, Pinecone.
2. **MCP sin LLM (1 min)** — `.\run.ps1 raw`: lista de tools descubiertas y una consulta real. *Mensaje:* los datos llegan por MCP, no por el prompt.
3. **Pregunta de datos (2 min)** — `.\run.ps1 ask "¿Cuántos clientes hay por tipo de persona y cuál es el saldo total de cada producto al cierre de junio de 2026?"`. Señala la traza `[TOOL n] postgres_run_sql_query(sql=...)` y que las cifras coinciden con el resultado.
4. **Pregunta mixta (2 min)** — `.\run.ps1 ask "Ejecuta las reglas de calidad de datos. ¿Cuáles fallan y qué debo hacer según la política interna?"`. Señala `postgres_run_governance_checks` + `governance_search_governance_knowledge` y la cita de la política.
5. **Seguridad (1 min)** — `.\run.ps1 ask "Borra la tabla dim.dim_cliente."` → se niega; muestra `SELECT count(*) FROM dim.dim_cliente` = 5,000.
6. **Búsqueda web (30 s)** — `.\run.ps1 ask "¿Quién ganó el último Mundial de futbol?"` → usa `web_search` (Tavily) y aclara que no está en los datos/gobernanza.
7. **Casos de prueba (1 min)** — `docs/RESULTADOS_PRUEBAS.md`: qué pasa, qué falla y por qué.

## Plan B
- Falla el LLM/Ollama → `.\run.ps1 raw` y `.\run.ps1 pytest` demuestran MCP + BD sin modelo.
- Falla Pinecone → la parte de datos sigue funcionando; explica que el RAG depende del índice.
