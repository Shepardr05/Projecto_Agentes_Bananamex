#!/usr/bin/env bash
# setup.sh -- Instalacion completa (Mac/Linux). Uso:  bash setup.sh
set -e
cd "$(dirname "$0")"
VENV="${DATA_STEWARD_VENV:-$HOME/.data-steward/venv}"
if [ ! -f .env ]; then cp .env.example .env; echo ">> Se creo .env: pega tus claves de Pinecone y Tavily y vuelve a correr bash setup.sh"; exit 0; fi
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt
"$VENV/bin/python" scripts/setup_all.py
