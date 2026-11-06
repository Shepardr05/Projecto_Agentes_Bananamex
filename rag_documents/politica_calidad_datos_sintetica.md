# Política interna de calidad y gobierno de datos (DOCUMENTO SINTÉTICO DE EJEMPLO)

> Elaborado por el equipo como política de ejemplo para el laboratorio. No es una política
> oficial de Banamex. Reemplazar por los documentos reales del socio formador cuando estén disponibles.

## 1. Roles y responsabilidades
- **Data Owner**: dirección de negocio dueña del dato; aprueba definiciones, clasificación y usos.
- **Data Steward**: custodia la calidad del dato, ejecuta las reglas de calidad, documenta
  hallazgos y propone remediación al Data Owner.
- **Data Custodian (TI)**: opera la infraestructura, respalda y aplica los controles de acceso.
- Todo hallazgo de severidad Alta debe escalarse al Data Owner en un máximo de 2 días hábiles.

## 2. Clasificación de la información
- **Restringida**: datos personales sensibles (fecha de nacimiento, género). Acceso solo con
  justificación y registro; prohibido exponerlos en herramientas de IA sin enmascarar.
- **Confidencial**: identificadores de cliente/cuenta y saldos o importes. Acceso por perfil.
- **Interna**: catálogos y atributos de negocio sin datos personales.
- Los agentes de IA solo pueden consultar datos con un rol de **solo lectura** y no pueden
  modificar, borrar ni crear objetos en las bases de datos.

## 3. Dimensiones de calidad aplicables
Se adoptan las seis dimensiones del Government Data Quality Framework: completitud, unicidad,
consistencia, oportunidad (timeliness), validez y exactitud.

## 4. Reglas de calidad y severidad
| Regla | Dimensión | Severidad | Descripción |
|---|---|---|---|
| DQ-01 | Unicidad | Alta | Una cuenta no puede tener dos saldos para el mismo mes. |
| DQ-02 | Completitud | Alta | Los saldos de apertura y cierre no pueden ser nulos. |
| DQ-03 | Validez | Alta | El saldo de cierre no puede ser negativo. |
| DQ-04 | Validez | Alta | El importe de una transacción debe ser mayor que cero. |
| DQ-05 | Consistencia | Alta | Toda cuenta debe pertenecer a un cliente existente en dim_cliente. |
| DQ-06 | Consistencia | Media | Toda transacción debe existir en el catálogo dim_txn (producto + clave). |
| DQ-07 | Consistencia | Media | Un producto debe usar un único valor de dominio en todos los meses. |
| DQ-08 | Consistencia | Media | El dominio de los saldos debe coincidir con dim_producto.cve_dominio, que es la fuente oficial. |
| DQ-09 | Validez | Alta | Los clientes persona física deben ser mayores de 18 años. |
| DQ-10 | Completitud | Media | Territorio, sucursal y promotor del cliente deben estar informados. |
| DQ-11 | Exactitud | Alta | El saldo de cierre debe conciliar con apertura más movimientos con tolerancia de 0.01. |

## 5. Remediación recomendada
- **Inconsistencia de dominio (DQ-07/DQ-08)**: homologar al catálogo oficial dim_producto.cve_dominio
  (DEPOSITS, LENDING, TDC). Registrar el cambio, no sobrescribir sin respaldo y notificar a los
  consumidores del dato. Mientras tanto, los reportes deben unir con dim_producto en vez de
  filtrar por la columna dominio.
- **Atributos organizacionales vacíos (DQ-10)**: el Data Owner de Red Comercial debe proveer la
  fuente de territorio, sucursal y promotor; hasta entonces, los reportes por región o sucursal
  no son confiables y deben advertirlo.
- **Conciliación (DQ-11)**: investigar primero las cuentas con diferencia; no ajustar saldos
  manualmente sin aprobación del Data Owner de Finanzas.

## 6. Retención y uso de datos
- Saldos y transacciones: 10 años. Clientes: vida del cliente más 10 años.
- Datos sintéticos: sin restricción regulatoria, pero se tratan con los mismos controles
  para ensayar el proceso.

## 7. Oportunidad
- Los saldos mensuales deben estar disponibles a más tardar 5 días hábiles después del cierre de mes.
