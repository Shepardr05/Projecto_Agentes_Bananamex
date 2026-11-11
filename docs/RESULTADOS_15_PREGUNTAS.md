# Las 15 preguntas: esperado vs. respuesta del agente (generado automáticamente)

Fecha: 2026-11-09 17:25 · **8/15 coinciden con lo esperado**

Heurística automática: revisa a mano las respuestas marcadas ❌. Las preguntas de gobernanza y de documentos se comparan contra la política y el catálogo **sintéticos** del equipo.

| # | Tipo | Pregunta | Resultado | Motivo |
|---|---|---|---|---|
| 1 | Gobernanza | ¿Quién es el dueño del dato del saldo de cierre de mes de las cuentas y quién es el steward responsable? | ✅ | - |
| 2 | Gobernanza | ¿Qué campos de la información de clientes son datos personales y cómo están clasificados? | ❌ | falta 'fec_nac' |
| 3 | Gobernanza | ¿De dónde viene el dominio del producto y cuál de las dos fuentes debo considerar la oficial? | ✅ | - |
| 4 | Gobernanza | ¿Quién es responsable de que la sucursal y el promotor del cliente estén informados? | ❌ | falta 'Red Comercial' |
| 5 | Gobernanza | ¿Qué clasificación tienen los importes de las transacciones y quién puede acceder a ellos? | ❌ | falta 'acceso por perfil' |
| 6 | Analítica | ¿Cuál es el saldo total de cada producto al cierre de junio de 2026? | ❌ | saldo AHORRO esperado 26,888,911.50; saldo C_PERSONAL esperado 378,894,263.38; saldo CHEQUES esperado 53,152,566.17; saldo TDC esperado 364,536,305.62 |
| 7 | Analítica | ¿Cuánto creció en promedio el saldo de las tarjetas de crédito de enero a febrero? | ✅ | - |
| 8 | Analítica | Para un cliente en particular, ¿cómo se compone el saldo de su tarjeta de crédito en marzo: saldo inicial, compras, disposiciones, pagos y saldo final? | ❌ | ninguna cifra de la respuesta corresponde a un saldo real de TDC en marzo |
| 9 | Analítica | ¿Qué segmento de clientes concentra el mayor saldo en cheques al cierre de junio? | ✅ | - |
| 10 | Analítica | ¿Cuánto dinero se movió en retiros y depósitos en mayo, producto por producto? | ✅ | - |
| 11 | Documentos | ¿Cuánto tiempo debemos conservar los saldos y las transacciones, según la política? | ✅ | - |
| 12 | Documentos | ¿En cuánto tiempo debo escalar un hallazgo de calidad de severidad alta y a quién? | ❌ | falta '2 días hábiles'; falta 'Data Owner' |
| 13 | Documentos | ¿Qué dice la política sobre cómo corregir que el dominio de los saldos no coincida con el catálogo de productos? | ✅ | - |
| 14 | Documentos | ¿Cuáles son las seis dimensiones de calidad de datos del marco de gobierno del Reino Unido y a cuál pertenece que un saldo no pueda ser negativo? | ✅ | - |
| 15 | Documentos | ¿Cuántos días después del cierre de mes deben estar disponibles los saldos mensuales? | ❌ | no uso la tool 'governance'; falta '5 días hábiles' |

## Verdad en tu base (calculada en vivo)

**P6 · saldo por producto al 30-jun-2026**

- AHORRO: 26,888,911.50
- C_PERSONAL: 378,894,263.38
- CHEQUES: 53,152,566.17
- TDC: 364,536,305.62

**P9 · saldo de CHEQUES por segmento (junio)**

- MASIVO: 39,792,237.95
- PREFERENTE: 10,691,376.81
- PREMIUM: 2,668,951.41

**P10 · movimientos de mayo**

- AHORRO DEPOSITO: 1,581,547.01
- AHORRO RETIRO: 1,317,956.11
- CHEQUES DEPOSITO: 3,126,316.38
- CHEQUES RETIRO: 2,605,263.70

**P8 · ejemplo: primera cuenta TDC en marzo**

- cliente 1, cuenta 300000: apertura 36,542.16 + compras 730.84 + disposiciones 730.84 − pagos 657.75 = saldo final 37,346.09

## Detalle

### P1 · Gobernanza

**Pregunta:** ¿Quién es el dueño del dato del saldo de cierre de mes de las cuentas y quién es el steward responsable?

**Esperado:** Data Owner: Dirección de Finanzas. Data Steward: Steward de Saldos (campo saldo_mes, catálogo).

- `governance_search_governance_knowledge(query='dueño del dato del saldo de cierre de mes de las cuentas y steward responsable')`

**Respuesta del agente:**

> El dueño del dato del saldo de cierre de mes de las cuentas es la Dirección de Finanzas y el steward responsable es el Steward de Saldos.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 25
> - catalogo_datos_sintetico.csv, row 24
> - catalogo_datos_sintetico.csv, row 20
> - catalogo_datos_sintetico.csv, row 19
> - catalogo_datos_sintetico.csv, row 22
> - catalogo_datos_sintetico.csv, row 21
> - catalogo_datos_sintetico.csv, row 28
> - catalogo_datos_sintetico.csv, row 23

**Veredicto:** ✅

### P2 · Gobernanza

**Pregunta:** ¿Qué campos de la información de clientes son datos personales y cómo están clasificados?

**Esperado:** fec_nac (fecha de nacimiento) y genero_cte (género): clasificación Restringida.

- `governance_search_governance_knowledge(query='campos de información de clientes datos personales clasificación')`

**Respuesta del agente:**

> Los campos de la información de clientes que son datos personales son:
> 
> * tipo_persona (Tipo de persona: PF (persona fisica) o PM (persona moral))
> * genero_cte (Genero del cliente; NO APLICA para personas morales)
> * num_cte (Identificador unico del cliente)
> 
> Estos campos están clasificados como:
> 
> * tipo_persona: Restringida
> * genero_cte: Restringida
> * num_cte: Confidencial
> 
> La clasificación de estos campos se basa en el catalogo_datos_sintetico.csv, que es un archivo de configuración de la base de datos que contiene información sobre la clasificación y retención de los datos.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 5
> - catalogo_datos_sintetico.csv, row 6
> - catalogo_datos_sintetico.csv, row 7
> - catalogo_datos_sintetico.csv, row 2
> - catalogo_datos_sintetico.csv, row 16
> - catalogo_datos_sintetico.csv, row 10
> - catalogo_datos_sintetico.csv, row 12
> - catalogo_datos_sintetico.csv, row 9

**Veredicto:** ❌ falta 'fec_nac'

### P3 · Gobernanza

**Pregunta:** ¿De dónde viene el dominio del producto y cuál de las dos fuentes debo considerar la oficial?

**Esperado:** Hay dos fuentes: dim_producto.cve_dominio (DEPOSITS/LENDING/TDC) y la columna dominio de la tabla de saldos (inconsistente). La oficial es dim_producto.cve_dominio.

- `governance_search_governance_knowledge(query='dominio del producto')`

**Respuesta del agente:**

> La fuente oficial del dominio del producto es `dim.dim_producto.cve_dominio` (DEPOSITS / LENDING / TDC). La columna `dominio` en `cfg.fact_txn_captacoloca_d` coincide con esta fuente, por lo que es la fuente oficial a considerar.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 15
> - catalogo_datos_sintetico.csv, row 37
> - catalogo_datos_sintetico.csv, row 16
> - catalogo_datos_sintetico.csv, row 27
> - politica_calidad_datos_sintetica.md
> - catalogo_datos_sintetico.csv, row 14
> - catalogo_datos_sintetico.csv, row 7

**Veredicto:** ✅

### P4 · Gobernanza

**Pregunta:** ¿Quién es responsable de que la sucursal y el promotor del cliente estén informados?

**Esperado:** Data Owner: Dirección de Red Comercial; Steward de Estructura Comercial (regla DQ-10).

- `governance_search_governance_knowledge(query='responsable de sucursal y promotor del cliente')`

**Respuesta del agente:**

> El responsable de que la sucursal y el promotor del cliente estén informados es el Steward de Estructura Comercial.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 13
> - catalogo_datos_sintetico.csv, row 12

**Veredicto:** ❌ falta 'Red Comercial'

### P5 · Gobernanza

**Pregunta:** ¿Qué clasificación tienen los importes de las transacciones y quién puede acceder a ellos?

**Esperado:** saldo_txn: Confidencial; acceso por perfil (política). Owner: Dirección de Finanzas.

- `governance_search_governance_knowledge(query='clasificación de importes de transacciones')`

**Respuesta del agente:**

> Los importes de las transacciones están clasificados como "Confidencial" y pertenecen a la Dirección de Finanzas. El Steward de Transacciones es responsable de su calidad y retención. La clasificación de los importes de las transacciones es "Confidencial" y su dueño es la Dirección de Finanzas.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 28
> - catalogo_datos_sintetico.csv, row 35
> - catalogo_datos_sintetico.csv, row 34
> - catalogo_datos_sintetico.csv, row 32
> - catalogo_datos_sintetico.csv, row 30
> - catalogo_datos_sintetico.csv, row 31
> - catalogo_datos_sintetico.csv, row 17
> - catalogo_datos_sintetico.csv, row 33

**Veredicto:** ❌ falta 'acceso por perfil'

### P6 · Analítica

**Pregunta:** ¿Cuál es el saldo total de cada producto al cierre de junio de 2026?

**Esperado:** Suma de saldo_mes con fec_informacion=20260630 por producto (cifras en tu base: ver sección 'Verdad en tu base').

- `postgres_run_sql_query(max_rows='100', sql='SELECT cve_producto, ROUND(SUM(saldo_mes),2) AS saldo_total FROM cfg.fact_sdos_captacoloca_m WHERE fec_informacion = 20260630 GROUP BY cve_producto ORDER BY cve_producto')`

**Respuesta del agente:**

> La respuesta se obtuvo mediante la ejecución de la siguiente consulta SQL:
> 
> ```sql
> SELECT cve_producto, ROUND(SUM(saldo_mes),2) AS saldo_total 
> FROM cfg.fact_sdos_captacoloca_m 
> WHERE fec_informacion = 20260630 
> GROUP BY cve_producto 
> ORDER BY cve_producto;
> ```
> 
> Esta consulta selecciona el saldo total de cada producto al cierre de junio de 2026, agrupando los resultados por producto y ordenando por producto.

**Veredicto:** ❌ saldo AHORRO esperado 26,888,911.50; saldo C_PERSONAL esperado 378,894,263.38; saldo CHEQUES esperado 53,152,566.17; saldo TDC esperado 364,536,305.62

### P7 · Analítica

**Pregunta:** ¿Cuánto creció en promedio el saldo de las tarjetas de crédito de enero a febrero?

**Esperado:** ≈ 3% (promedio del crecimiento por cuenta TDC, saldo_mes de 20260131 a 20260228).

- `postgres_run_sql_query(max_rows='100', sql="SELECT ROUND(AVG(100.0 * (f.saldo_mes - e.saldo_mes) / e.saldo_mes), 2) AS crecimiento_pct FROM cfg.fact_sdos_captacoloca_m f JOIN cfg.fact_sdos_captacoloca_m e ON e.num_cta = f.num_cta AND e.fec_informacion = 20260131 WHERE f.cve_producto = 'C_PERSONAL' AND f.fec_informacion = 20260228")`

**Respuesta del agente:**

> La respuesta es 3.0%.

**Veredicto:** ✅

### P8 · Analítica

**Pregunta:** Para un cliente en particular, ¿cómo se compone el saldo de su tarjeta de crédito en marzo: saldo inicial, compras, disposiciones, pagos y saldo final?

**Esperado:** Saldo final = saldo inicial + compras (400) + disposiciones (450) − pagos (300). El agente debe elegir/pedir un cliente y mostrar los cinco componentes con cifras reales.

- `postgres_run_sql_query(max_rows='100', sql="SELECT cve_producto, saldo_apertura, SUM(CASE WHEN cve_txn = 400 THEN saldo_txn ELSE 0 END) AS compras, SUM(CASE WHEN cve_txn = 450 THEN saldo_txn ELSE 0 END) AS disposiciones, SUM(CASE WHEN cve_txn = 300 THEN saldo_txn ELSE 0 END) AS pagos, saldo_mes FROM cfg.fact_txn_captacoloca_d WHERE cve_producto = 'C_PERSONAL' AND fec_txn <= '2023-03-15' GROUP BY cve_producto, saldo_apertura, saldo_mes")`

**Respuesta del agente:**

> Lo siento, pero no puedo continuar con la respuesta anterior debido a la inconsistencia en la columna "saldo_apertura" que no existe en la tabla cfg.fact_txn_captacoloca_d.
> 
> Sin embargo, puedo ayudarte a encontrar la respuesta correcta. Para calcular el saldo de la tarjeta de crédito de un cliente en marzo, debemos considerar las transacciones de ese mes. Podemos hacer una consulta a la tabla cfg.fact_txn_captacoloca_d para obtener las transacciones de marzo y luego calcular el saldo inicial, compras, disposiciones, pagos y saldo final.
> 
> Aquí te dejo una posible consulta SQL:
> 
> ```sql
> SELECT 
>   cve_producto, 
>   SUM(CASE WHEN cve_txn = 400 THEN saldo_txn ELSE 0 END) AS compras, 
>   SUM(CASE WHEN cve_txn = 450 THEN saldo_txn ELSE 0 END) AS disposiciones, 
>   SUM(CASE WHEN cve_txn = 300 THEN saldo_txn ELSE 0 END) AS pagos, 
>   saldo_mes AS saldo_final
> FROM 
>   cfg.fact_txn_captacoloca_d
> WHERE 
>   cve_producto = 'C_PERSONAL' AND 
>   fec_txn <= '2023-03-15' AND 
>   fec_informacion = 20260331
> GROUP BY 
>   cve_producto, 
>   saldo_mes;
> ```
> 
> Esta consulta calcula las transacciones de marzo para la tarjeta de crédito del cliente y devuelve el saldo final. Recuerda que debes reemplazar 'C_PERSONAL' con el código de producto real del cliente y '2023-03-15' con la fecha real de corte de marzo.
> 
> Espero que esto te ayude a encontrar la respuesta correcta.

**Veredicto:** ❌ ninguna cifra de la respuesta corresponde a un saldo real de TDC en marzo

### P9 · Analítica

**Pregunta:** ¿Qué segmento de clientes concentra el mayor saldo en cheques al cierre de junio?

**Esperado:** El segmento con mayor suma de saldo_mes de CHEQUES (join con dim_cliente) a 20260630.

- `postgres_run_sql_query(sql="SELECT c.segmento_cte, ROUND(SUM(s.saldo_mes),2) AS saldo_total FROM cfg.fact_sdos_captacoloca_m s JOIN dim.dim_cliente c ON c.num_cte = s.num_cte WHERE s.cve_producto = 'CHEQUES' AND s.fec_informacion = 20260630 GROUP BY c.segmento_cte ORDER BY saldo_total DESC LIMIT 1")`

**Respuesta del agente:**

> El segmento de clientes que concentra el mayor saldo en cheques al cierre de junio es el MASIVO, con un saldo total de 39,792,237.95.

**Veredicto:** ✅

### P10 · Analítica

**Pregunta:** ¿Cuánto dinero se movió en retiros y depósitos en mayo, producto por producto?

**Esperado:** Solo CHEQUES y AHORRO tienen depósitos (100) y retiros (200); suma de saldo_txn en 20260531. TDC y C_PERSONAL no tienen retiros/depósitos (tienen pagos, compras y disposiciones).

- `postgres_run_sql_query(max_rows='100', sql='SELECT cve_producto, ROUND(SUM(CASE WHEN cve_txn = 200 THEN saldo_txn ELSE 0 END),2) AS retiros, ROUND(SUM(CASE WHEN cve_txn = 100 THEN saldo_txn ELSE 0 END),2) AS depositos FROM cfg.fact_txn_captacoloca_d WHERE cve_mes_txn = 202605 GROUP BY cve_producto ORDER BY cve_producto')`

**Respuesta del agente:**

> La respuesta es que en mayo, se movieron:
> 
> * En AHORRO: $1,317,956.11 en retiros y $1,581,547.01 en depósitos.
> * En C_PERSONAL: $0 en retiros y $0 en depósitos.
> * En CHEQUES: $2,605,263.70 en retiros y $3,126,316.38 en depósitos.
> * En TDC: $0 en retiros y $0 en depósitos.
> 
> Estos resultados se obtuvieron mediante la ejecución de la siguiente consulta SQL:
> 
> ```sql
> SELECT 
>   cve_producto, 
>   ROUND(SUM(CASE WHEN cve_txn = 200 THEN saldo_txn ELSE 0 END),2) AS retiros, 
>   ROUND(SUM(CASE WHEN cve_txn = 100 THEN saldo_txn ELSE 0 END),2) AS depositos 
> FROM 
>   cfg.fact_txn_captacoloca_d 
> WHERE 
>   cve_mes_txn = 202605 
> GROUP BY 
>   cve_producto 
> ORDER BY 
>   cve_producto;
> ```

**Veredicto:** ✅

### P11 · Documentos

**Pregunta:** ¿Cuánto tiempo debemos conservar los saldos y las transacciones, según la política?

**Esperado:** 10 años (política, sección 6).

- `governance_search_governance_knowledge(query='retencion de saldos y transacciones')`

**Respuesta del agente:**

> Según la política, los saldos y las transacciones deben conservarse durante 10 años.
> 
> Fuentes consultadas:
> - catalogo_datos_sintetico.csv, row 25
> - catalogo_datos_sintetico.csv, row 33
> - catalogo_datos_sintetico.csv, row 28
> - catalogo_datos_sintetico.csv, row 24
> - catalogo_datos_sintetico.csv, row 19
> - catalogo_datos_sintetico.csv, row 22
> - politica_calidad_datos_sintetica.md
> - catalogo_datos_sintetico.csv, row 35

**Veredicto:** ✅

### P12 · Documentos

**Pregunta:** ¿En cuánto tiempo debo escalar un hallazgo de calidad de severidad alta y a quién?

**Esperado:** Máximo 2 días hábiles, al Data Owner (política, sección 1).

- `governance_search_governance_knowledge(query='escalado de hallazgos de calidad de severidad alta')`

**Respuesta del agente:**

> Lo siento, pero no hay información disponible en los documentos de gobernanza sobre el escalado de hallazgos de calidad de severidad alta.

**Veredicto:** ❌ falta '2 días hábiles'; falta 'Data Owner'

### P13 · Documentos

**Pregunta:** ¿Qué dice la política sobre cómo corregir que el dominio de los saldos no coincida con el catálogo de productos?

**Esperado:** Homologar al catálogo oficial dim_producto.cve_dominio (DEPOSITS, LENDING, TDC); registrar el cambio, no sobrescribir sin respaldo, notificar a los consumidores; mientras tanto unir con dim_producto (política, sección 5).

- `governance_search_governance_knowledge(query='corregir dominio saldos no coincide con catálogo de productos')`

**Respuesta del agente:**

> Basado en la información proporcionada, puedo responder a las preguntas relacionadas con la remediación recomendada, retención y uso de datos, y oportunidad.
> 
> **Remediación recomendada**
> 
> La remediación recomendada es la siguiente:
> 
> * Inconsistencia de dominio (DQ-07/DQ-08): homologar al catálogo oficial dim_producto.cve_dominio (DEPOSITS, LENDING, TDC). Registrar el cambio, no sobrescribir sin respaldo y notificar a los consumidores del dato. Mientras tanto, los reportes deben unir con dim_producto en vez de filtrar por la columna dominio.
> * Atributos organizacionales vacíos (DQ-10): el Data Owner de Red Comercial debe proveer la fuente de territorio, sucursal y promotor; hasta entonces, los reportes por región o sucursal no son confiables y deben advertirlo.
> * Conciliación (DQ-11): investigar primero las cuentas con diferencia; no ajustar saldos manualmente sin aprobación del Data Owner de Finanzas.
> 
> **Retención y uso de datos**
> 
> La retención y uso de datos es la siguiente:
> 
> * Saldos y transacciones: 10 años.
> * Clientes: vida del cliente más 10 años.
> * Datos sintéticos: sin restricción regulatoria, pero se tratan con los mismos controles para ensayar el proceso.
> 
> **Oportunidad**
> 
> La oportunidad es la siguiente:
> 
> * Los saldos mensuales deben estar disponibles a más tardar 5 días hábiles después del cierre de mes.
> 
> Espero que esta información sea útil. Si tienes alguna pregunta o necesitas más información, no dudes en preguntar.
> 
> Fuentes consultadas:
> - politica_calidad_datos_sintetica.md
> - catalogo_datos_sintetico.csv, row 27
> - catalogo_datos_sintetico.csv, row 37
> - catalogo_datos_sintetico.csv, row 15
> - catalogo_datos_sintetico.csv, row 25

**Veredicto:** ✅

### P14 · Documentos

**Pregunta:** ¿Cuáles son las seis dimensiones de calidad de datos del marco de gobierno del Reino Unido y a cuál pertenece que un saldo no pueda ser negativo?

**Esperado:** Completeness, Uniqueness, Consistency, Timeliness, Validity, Accuracy. Saldo no negativo = Validez (DQ-03, política).

- `governance_search_governance_knowledge(query='six dimensions of data quality')`

**Respuesta del agente:**

> Based on the provided sources, the six core data quality dimensions as defined by DAMA UK are:
> 
> 1. **Completeness**: The data set includes all the expected records and no records are missing important data.
> 2. **Uniqueness**: Each record is unique and can be distinguished from others.
> 3. **Consistency**: The data is consistent in terms of format, structure, and content.
> 4. **Timeliness** (Oportunidad): The data is available when needed and is up-to-date.
> 5. **Validity** (Validez): The data is accurate and reflects the real-world situation.
> 6. **Accuracy** (Exactitud): The data is precise and free from errors.
> 
> These dimensions can be used to assess and improve the quality of data, and can be applied to various contexts and organizations.
> 
> Additionally, the Government Data Quality Framework provides guidance on practical tools and techniques for assessing, communicating, and improving data quality, including:
> 
> * Data quality action plans
> * Root cause analysis
> * Metadata guidance
> * Communicating quality guidance
> 
> It also emphasizes the importance of continuous improvement, focusing on building capability in assessing, improving, and communicating data quality, and prioritizing efforts on the data that is most critical.
> 
> In terms of implementation, the framework suggests that organizations should:
> 
> * Dedicate time and resource to building capability in assessing, improving, and communicating data quality
> * Include best practice in data quality management as part of training materials
> * Benchmark and regularly assess levels of data quality over time to track changes in quality
> * Prioritize and iterate effective improvements to achieve fit for purpose data
> * Use data quality action plans to identify and define where efforts should be prioritized
> 
> Overall, the Government Data Quality Framework provides a comprehensive approach to data quality management, emphasizing the importance of understanding user needs, building capability, and prioritizing efforts to achieve fit for purpose data.
> 
> Fuentes consultadas:
> - The Government Data Quality Framework - GOV.UK.pdf, page 18
> - The Government Data Quality Framework_ guidance - GOV.UK.pdf, page 16
> - The Government Data Quality Framework_ guidance - GOV.UK.pdf, page 22
> - The Government Data Quality Framework - GOV.UK.pdf, page 6
> - The Government Data Quality Framework_ guidance - GOV.UK.pdf, page 3
> - politica_calidad_datos_sintetica.md
> - The Government Data Quality Framework - GOV.UK.pdf, page 8

**Veredicto:** ✅

### P15 · Documentos

**Pregunta:** ¿Cuántos días después del cierre de mes deben estar disponibles los saldos mensuales?

**Esperado:** 5 días hábiles después del cierre (política, sección 7).

- `postgres_get_data_model_guide()`

**Respuesta del agente:**

> ¡Hola! Me alegra poder ayudarte con tus preguntas sobre el modelo de datos. ¿En qué puedo ayudarte hoy?

**Veredicto:** ❌ no uso la tool 'governance'; falta '5 días hábiles'
