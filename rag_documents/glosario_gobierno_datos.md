# Glosario de gobierno y calidad de datos (complemento del equipo)

> COMPLEMENTO DEL EQUIPO: definiciones generales en español, con palabras propias, para que el agente use un vocabulario consistente. No son definiciones oficiales de Banamex. Donde aplica, se indica la fuente legal del corpus.

## Roles
Data Owner (dueño del dato): persona o dirección de negocio que responde por un dato, aprueba su definición, su clasificación y sus usos. En el catálogo del proyecto, por ejemplo, la Dirección de Finanzas es dueña de saldo_mes.
Data Steward (custodio de calidad): persona que vigila la calidad de un dato, ejecuta reglas de calidad, documenta hallazgos y propone remediación al Data Owner.
Data Custodian (custodio técnico): área de TI que opera la infraestructura, los respaldos y los controles de acceso.
Oficial de seguridad: figura que el Anexo 52 de la CUB pide para servicios de apoyo tecnológico; es independiente de operación, auditoría y sistemas y autoriza los accesos según la necesidad de conocer.

## Conceptos de datos
Catálogo de datos: inventario de campos y tablas con su descripción, tipo, clasificación, dueño, steward, retención y regla de calidad.
Fuente oficial (golden source): sistema o tabla que prevalece cuando dos fuentes discrepan. En el proyecto, dim_producto.cve_dominio es la fuente oficial del dominio del producto.
Linaje de datos (lineage): recorrido de un dato desde su origen, pasando por sus transformaciones, hasta su uso en un reporte.
Dimensión de calidad: criterio para medir la calidad. Las seis del Government Data Quality Framework son completitud, unicidad, consistencia, oportunidad, validez y exactitud.
Conciliación: comparar dos fuentes o cálculos del mismo dato para comprobar que coinciden dentro de una tolerancia; la regla DQ-11 concilia el saldo de cierre con el saldo de apertura más los movimientos.
Severidad: gravedad de un hallazgo de calidad (alta o media en la política sintética), que define el plazo de escalamiento.
Remediación: acción para corregir un hallazgo y evitar que se repita; en la política sintética, por ejemplo, homologar el dominio al catálogo oficial.

## Privacidad y seguridad
Dato personal: información que permite identificar a una persona, directa o indirectamente (LFPDPPP 2025).
Dato sensible: dato íntimo cuyo mal uso puede causar discriminación o un riesgo grave, como salud, genética, origen étnico, creencias, opiniones políticas o preferencia sexual (LFPDPPP 2025). No todo dato personal es sensible.
Titular: persona a quien corresponden los datos personales.
Responsable: quien decide sobre el tratamiento de los datos personales.
Aviso de privacidad: documento que informa al titular qué datos se tratan, para qué finalidades y cómo ejercer sus derechos.
Derechos ARCO: acceso, rectificación, cancelación y oposición.
Clasificación de la información: nivel de protección asignado a un dato. En la política sintética: Restringida, Confidencial e Interna.
Mínimo privilegio: cada persona o agente recibe solo el acceso que necesita. En el proyecto, el rol usuario no puede leer fec_nac ni genero_cte.
Enmascaramiento: ocultar o sustituir valores personales (por ejemplo con ***) para poder mostrar datos sin exponerlos.
Bitácora de auditoría: registro de quién accedió a qué y cuándo.
Confidencialidad, integridad y disponibilidad: los tres objetivos de la seguridad de la información que las disposiciones de la CNBV sobre prevención de fraude piden asegurar, incluida la infraestructura de terceros.

## Términos bancarios
Captación: dinero del cliente que está en el banco (cuentas de cheques, ahorro); es un pasivo del banco.
Colocación: dinero que el banco presta al cliente (crédito personal, tarjeta de crédito); es cartera, un activo del banco.
Saldo de cierre y saldo de apertura: saldo de la cuenta al final y al inicio del mes.
KYC (conocimiento del cliente): obligación de identificar y conocer al cliente, prevista en el artículo 115 de la LIC.
PLD (prevención de lavado de dinero): conjunto de medidas para detectar y reportar operaciones con recursos de procedencia ilícita, previstas en el artículo 115 de la LIC.
MTU (Monto Transaccional del Usuario): referencia del monto habitual de operaciones de un usuario, usada para detectar operaciones atípicas según las disposiciones de la CNBV sobre prevención de fraude.
CNBV: Comisión Nacional Bancaria y de Valores, supervisora de los bancos en México.
CUB: Circular Única de Bancos, disposiciones generales de la CNBV aplicables a instituciones de crédito.
LIC: Ley de Instituciones de Crédito.
