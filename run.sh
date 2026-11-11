#!/usr/bin/env bash
# run.sh -- demo | ask "pregunta" | chat | tests | pytest | check | raw | stop-db
cd "$(dirname "$0")"
PY="${DATA_STEWARD_VENV:-$HOME/.data-steward/venv}/bin/python"
cmd="${1:-demo}"; shift || true
case "$cmd" in
  demo) "$PY" src/agent.py --demo;; ask) "$PY" src/agent.py "$@";; chat) "$PY" src/agent.py -i;;
  tests) "$PY" src/run_test_cases.py "$@";; preguntas) "$PY" src/run_preguntas.py "$@";; respuestas) "$PY" src/respuestas_15.py "$@";; lote) "$PY" src/responder_lote.py "$@";; langsmith) "$PY" src/evaluar_langsmith.py "$@";; pytest) "$PY" -m pytest -q;; check) "$PY" scripts/check_setup.py;;
  raw) "$PY" src/mcp_raw_client.py;; reload-db) "$PY" scripts/load_db.py --force;; stop-db) "$PY" scripts/stop_db.py;; *) echo "comando desconocido: $cmd";;
esac