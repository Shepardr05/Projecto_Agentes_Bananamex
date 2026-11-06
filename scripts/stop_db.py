"""Detiene el PostgreSQL embebido (no borra datos). Se vuelve a iniciar solo al usar el agente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import db_config  # noqa: E402

db_config.stop_db()
print("PostgreSQL embebido detenido.")
