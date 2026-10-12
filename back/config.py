"""Configuración leída de variables de entorno (nunca de valores escritos en el código)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Lee el archivo .env si existe (solo desarrollo local). No pisa las variables que
# ya estén definidas en el entorno, como las de Cloud Run.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", encoding="utf-8-sig")

def _activado(nombre: str) -> bool:
    return os.getenv(nombre, "").strip().lower() in ("1", "true", "si", "sí")


MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB = os.getenv("MONGODB_DB", "").strip() or "splitmate"
# Primer administrador: se crea al arrancar si todavía no existe (ver dependencias.preparar)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# TEMPORAL hasta el Hito 4 (confirmación por correo)
CONFIRMAR_AUTOMATICAMENTE = _activado("CONFIRMAR_AUTOMATICAMENTE")
COOKIE_SEGURA = _activado("COOKIE_SEGURA")  # true en producción (https)