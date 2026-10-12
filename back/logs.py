"""Configuración del registro (log) de actividad."""
import logging
import sys

from back import config


def configurar_logging() -> None:
    """Escribe en la salida estándar, que es lo que Cloud Run recoge en sus registros.
    El nivel se controla con la variable LOG_LEVEL (por defecto INFO)."""
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    nivel = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logging.getLogger("splitmate").setLevel(nivel)