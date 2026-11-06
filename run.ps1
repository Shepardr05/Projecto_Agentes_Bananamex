# run.ps1 -- Atajos para usar el proyecto sin activar el entorno virtual.
#   .\run.ps1 demo                      demo con 6 preguntas
#   .\run.ps1 ask "tu pregunta"         una pregunta
#   .\run.ps1 chat                      chat interactivo
#   .\run.ps1 tests                     10 casos de prueba -> docs\RESULTADOS_PRUEBAS.md
#   .\run.ps1 pytest                    pruebas deterministas del servidor MCP de SQL
#   .\run.ps1 check                     diagnostico del entorno
#   .\run.ps1 raw                       MCP sin LLM (plan B de la demo)
#   .\run.ps1 reload-db                regenera la base desde cero
#   .\run.ps1 stop-db                   detiene PostgreSQL embebido
param([Parameter(Position = 0)][string]$cmd = "demo",
      [Parameter(ValueFromRemainingArguments = $true)]$rest)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$py = Join-Path $env:LOCALAPPDATA "data-steward\venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Primero ejecuta: powershell -ExecutionPolicy Bypass -File .\setup.ps1"; exit 1 }
switch ($cmd) {
    "demo"    { & $py src\agent.py --demo }
    "ask"     { & $py src\agent.py @rest }
    "chat"    { & $py src\agent.py -i }
    "tests"   { & $py src\run_test_cases.py @rest }
    "pytest"  { & $py -m pytest -q }
    "check"   { & $py scripts\check_setup.py }
    "raw"     { & $py src\mcp_raw_client.py }
    "reload-db" { & $py scripts\load_db.py --force }
    "stop-db" { & $py scripts\stop_db.py }
    default   { Write-Host "Comando desconocido: $cmd (demo, ask, chat, tests, pytest, check, raw, reload-db, stop-db)" }
}
