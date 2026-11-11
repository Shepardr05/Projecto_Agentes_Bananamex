# Respuestas del agente a las 15 preguntas

Fecha: 2026-11-09 18:36

## P10 · Analítica

**Pregunta:** ¿Cuánto dinero se movió en retiros y depósitos en mayo, producto por producto?

**Tools:** postgres_run_sql_query

**Respuesta:**

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
