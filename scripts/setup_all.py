"""
setup_all.py -- Deja TODO listo en un solo paso (lo llama setup.ps1 / setup.sh):
  1) .env  2) base de datos sintetica  3) modelos de Ollama  4) indice y RAG en Pinecone
  5) diagnostico final.
Cada paso informa su resultado; si uno falla, sigue con los demas y al final resume.
"""
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

results: list[tuple[str, bool, str]] = []


def step(name: str):
    def deco(fn):
        print(f"\n{'=' * 70}\n>> {name}\n{'=' * 70}", flush=True)
        try:
            msg = fn() or ""
            results.append((name, True, msg))
        except SystemExit as e:
            results.append((name, False, str(e)))
            print("   !!", e)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return deco


@step("1/5 Archivo .env")
def _env():
    env, example = ROOT / ".env", ROOT / ".env.example"
    if not env.exists():
        shutil.copy(example, env)
        print("   Se creo .env desde .env.example")
    from dotenv import load_dotenv

    load_dotenv(env, override=True)
    bad = [k for k in ("PINECONE_API_KEY", "INDEX_NAME") if not os.getenv(k) or "PEGA" in os.getenv(k, "")]
    if bad:
        raise SystemExit(f"Edita {env} y pon tus claves: {bad}. Luego vuelve a ejecutar el setup.")


@step("2/5 Base de datos sintetica (PostgreSQL embebido, sin Docker)")
def _db():
    import load_db

    load_db.main()


@step("3/5 Modelos de Ollama")
def _ollama():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    if not shutil.which("ollama"):
        raise SystemExit("Ollama no esta instalado. Descargalo en https://ollama.com/download , abrelo y vuelve a correr el setup.")
    models = [os.getenv("EMBEDDING_MODEL", "bge-m3")]
    if os.getenv("LLM_PROVIDER", "ollama") == "ollama":
        models.append(os.getenv("LLM_MODEL", "llama3.1:latest"))
    for m in models:
        print(f"   ollama pull {m}", flush=True)
        if subprocess.run(["ollama", "pull", m]).returncode != 0:
            raise SystemExit(f"Fallo 'ollama pull {m}'. Abre la app de Ollama y reintenta.")


@step("4/5 RAG de gobernanza (indice Pinecone + ingesta)")
def _rag():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    import ingest_governance

    ingest_governance.main(["--reset"])


@step("5/5 Diagnostico final")
def _check():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_setup.py")])


print(f"\n{'#' * 70}\nRESUMEN\n{'#' * 70}")
for name, ok, msg in results:
    print(("[ OK ] " if ok else "[FALLA] ") + name + (f" -> {msg}" if msg and not ok else ""))
if all(ok for _, ok, _ in results):
    print("\nTodo listo. Prueba:  .\\run.ps1 demo   (Windows)   |   ./run.sh demo   (Mac/Linux)")
else:
    print("\nArregla lo que marca [FALLA] y vuelve a ejecutar el setup (es seguro repetirlo).")
