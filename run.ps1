# run.ps1 -- Atajos para usar el proyecto sin activar el entorno virtual.
#   .\run.ps1 demo                      demo con 6 preguntas
#   .\run.ps1 ask "tu pregunta"         una pregunta
#   .\run.ps1 chat                      chat interactivo
#   .\run.ps1 tests                     10 casos de prueba -> docs\RESULTADOS_PRUEBAS.md
#   .\run.ps1 preguntas                 las 15 preguntas + revision -> docs\RESULTADOS_15_PREGUNTAS.md
#   .\run.ps1 langsmith                evalua las 15 preguntas en LangSmith (requiere LANGSMITH_API_KEY)
#   .\run.ps1 lote archivo.txt         preguntas de un archivo (una por linea) -> docs\RESPUESTAS_<archivo>.md
#   .\run.ps1 respuestas                las 15 preguntas con su respuesta -> docs\RESPUESTAS_15.md
#   .\run.ps1 pytest                    pruebas deterministas del servidor MCP de SQL
#   .\run.ps1 check                     diagnostico del entorno
#   .\run.ps1 raw                       MCP sin LLM (plan B de la demo)
#   .\run.ps1 load-db                  crea/actualiza roles y datos si faltan (idempotente)
#   .\run.ps1 reload-db                regenera la base desde cero
#   .\run.ps1 stop-db                   detiene PostgreSQL embebido
param([Parameter(Position = 0)][string]$cmd = "demo",
      [Parameter(ValueFromRemainingArguments = $true)]$rest)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$py = Join-Path $env:LOCALAPPDATA "data-steward\venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Primero ejecuta: powershell -ExecutionPolicy Bypass -File .\setup.ps1"; exit 1 }
switch ($cmd) {
    "demo"    { & $py src\agent.py --demo @rest }
    "ask"     { & $py src\agent.py @rest }
    "chat"    { & $py src\agent.py -i @rest }
    "tests"   { & $py src\run_test_cases.py @rest }
    "preguntas" { & $py src\run_preguntas.py @rest }
    "respuestas" { & $py src\respuestas_15.py @rest }
    "langsmith" { & $py src\evaluar_langsmith.py @rest }
    "lote"    { & $py src\responder_lote.py @rest }
    "pytest"  { & $py -m pytest -q }
    "check"   { & $py scripts\check_setup.py }
    "raw"     { & $py src\mcp_raw_client.py @rest }
    "load-db" { & $py scripts\load_db.py }
    "reload-db" { & $py scripts\load_db.py --force }
    "stop-db" { & $py scripts\stop_db.py }
    default   { Write-Host "Comando desconocido: $cmd (demo, ask, chat, tests, preguntas, respuestas, lote, langsmith, pytest, check, raw, load-db, reload-db, stop-db)" }
}
