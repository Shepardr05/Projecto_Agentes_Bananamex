# rag_documents/: corpus de gobernanza

Este README no se ingesta (el cargador ignora `README.md`). Describe qué hay, de dónde sale y qué falta. Fecha de la investigación: 10 de noviembre de 2026.

## Documentos del corpus

| Archivo | Tipo | Origen |
|---|---|---|
| The Government Data Quality Framework - GOV.UK.pdf | Oficial (inglés) | GOV.UK |
| The Government Data Quality Framework_ guidance - GOV.UK.pdf | Oficial (inglés) | GOV.UK |
| onsdataqualitypolicy.pdf | Oficial (inglés) | ONS |
| politica_calidad_datos_sintetica.md | **Sintético** | Equipo |
| catalogo_datos_sintetico.csv | **Sintético** | Equipo |
| banamex_contexto_publico.md | Síntesis de fuentes públicas | Citi, Reuters, Xataka, avisos de Fomento Banamex |
| marco_regulatorio_datos_bancarios_mx.md | Síntesis de fuentes públicas | LIC, Código de Comercio, LFPDPPP, CNBV, CUB, BBVA Research |
| bcbs239_principios_resumen.md | Síntesis de fuente pública | Comité de Basilea (vía resumen) |
| trazabilidad_politica_vs_marco_regulatorio.md | **Complemento del equipo** | Análisis propio |
| glosario_gobierno_datos.md | **Complemento del equipo** | Definiciones propias |

## Lo que no se encontró (importante)
Banamex no publica su política interna de gobierno de datos, así que **no hay un documento oficial de Banamex** sobre dueños de datos, clasificación, retención o reglas de calidad. Tampoco se pudieron leer el aviso de privacidad del sitio principal de Banamex (contenido dinámico) ni el Informe Integrado Banamex 2024 (el sitio bloquea la descarga automática). El corpus lo dice de forma explícita para que el agente no invente.

## Fuentes consultadas (10 de noviembre de 2026)
- Citi, comunicado del 23 de febrero de 2026: https://www.citigroup.com/global/news/press-release/2026/citi-announces-agreements-with-investors-for-commitments-to-purchase-an-aggregate-24-equity-stake-in-banamex
- Reuters vía KFGO, 20 de octubre de 2026: https://kfgo.com/2026/10/20/citi-mexico-sees-new-opportunities-with-banks-after-banamex-split/
- Xataka México, explicación de la separación: https://www.xataka.com.mx/otros-1/separacion-citi-banamex-mexico-explicada-que-significa-que-sucede-sus-clientes-productos
- Aviso de privacidad de Fomento Cultural y Social Banamex (julio 2025): https://www.banamex.com/compromiso-social/avisos.html
- LIC art. 115 (transcripción): https://mley.mx/LIC/articulo/115/
- Código de Comercio art. 46 (secundaria): https://sdv.com.mx/compendio/codigo-comercio/articulo-46/
- LFPDPPP 2025, resumen de Garrigues: https://www.garrigues.com/es_ES/noticia/mexico-nueva-ley-federal-proteccion-datos-personales-posesion-particulares-introduce
- Prevención de fraude CNBV, presentación de Deloitte: https://www.deloitte.com/content/dam/assets-zone4/latam/es/docs/services/financial-advisory/2025/folleto_nvs_disps_prevencion_fraude_final.pdf
- CUB Anexo 52 (ABM): https://www.abm.org.mx/legislacion-y-regulacion/juridico/anexoscub/CUB_Anexo52.pdf
- Cumplimiento CNBV de un proveedor de nube (secundaria): https://cloud.google.com/security/compliance/cnbv-mexico?hl=es
- BBVA Research, Regulación Financiera, octubre 2026: https://www.bbvaresearch.com/wp-content/uploads/2026/10/20261015_MexicoRegFinOct2026-1.pdf
- BCBS 239, resumen: https://en.wikipedia.org/wiki/BCBS_239

## Para completar a mano (el equipo debe descargarlos)
El entorno de trabajo no pudo descargar PDFs. Estos textos oficiales mejorarían mucho el corpus; puedes colocarlos en esta carpeta y volver a ingestar:
1. Ley de Instituciones de Crédito: https://www.diputados.gob.mx/LeyesBiblio/pdf/LIC.pdf
2. LFPDPPP 2025: https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf
3. BCBS 239 (original): https://www.bis.org/publ/bcbs239.pdf
4. Circular Única de Bancos (completa, para los artículos de control interno y seguridad de la información): https://www.abm.org.mx/legislacion-y-regulacion/juridico/cnbv/CircularUnicadeBancos.pdf
5. Informe Integrado Banamex 2024: https://www.banamex.com/resources/pdf/es/personas/compromiso-social/informes-transparencia/Informe-Integrado-Banamex-2024.pdf
6. Aviso de privacidad del sitio de Banamex (copiar el texto a un .md): https://www.banamex.com/privacidad-portal

Nota: la LIC y la CUB son archivos muy grandes; la ingesta tarda más y conviene subir `RAG_TOP_K` o filtrar por fuente.

## Cómo re-ingestar
`python src/ingest_governance.py --reset`
