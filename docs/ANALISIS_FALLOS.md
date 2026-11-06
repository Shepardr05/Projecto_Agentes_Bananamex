# Análisis de fallos (Sprint 2)

Modelo: `llama3.1` (Ollama, local): **7/10 pasan** (T2, T3, T4, T5, T7, T9, T10). Respuestas completas en `RESULTADOS_PRUEBAS.md`.

**Patrón común:** en los tres fallos el agente llama a la tool correcta (o al menos a la primera), pero el modelo de 8B no usa bien el resultado al redactar. Es una hipótesis: falta compararla corriendo los tests con otro modelo.

| Caso | Qué pasó                                                                                                                                                                   | Causa                                                                     |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| T1   | El SQL es correcto, pero la respuesta final solo repite la consulta, sin los saldos. Falló igual en las dos corridas.                                                      | Modelo ignora el resultado de la tool                                     |
| T6   | Corrió las reglas de calidad, no consultó la política y respondió "no puedo continuar". En la corrida anterior sí buscó la política, pero respondió consejos genéricos.    | Modelo: no sigue el paso siguiente que indica la tool ni usa su resultado |
| T8   | Usó `cve_sucursal` en la tabla de hechos (está en `dim_cliente`), la consulta falló y no advirtió que esa columna está 100% vacía. Respuesta idéntica en las dos corridas. | Modelo no se recupera del error                                           |

**Variabilidad:** T9 y T10 fallaron en la primera corrida y pasaron en la segunda con las mismas llamadas a las tools. La búsqueda en Pinecone sí devuelve el catálogo, así que el fallo de T9 era del modelo y no del umbral `MIN_SCORE`. Los resultados cambian entre corridas.

**Límites de la evaluación automática**

- T5 solo comprueba que aparezcan las seis dimensiones; el modelo definió mal _Validity_.
- T10 solo comprueba que use `web_search` y cite una URL. La respuesta es excesivamente larga y se contradice ("hasta 2022" y lista 2026); su contenido proviene de la fuente web y no se verificó.

**Mejoras posibles:** modelo más grande (`LLM_PROVIDER=google|anthropic`) y respuestas más cortas de las tools.
