"""Comprueba automáticamente las fronteras entre capas (apartado 3.2)."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IMPORTACION = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE)


def _archivos(carpeta, extension):
    return [p for p in (RAIZ / carpeta).rglob(f"*{extension}")]


def _importaciones_python(archivo):
    return IMPORTACION.findall(archivo.read_text(encoding="utf-8"))


def test_la_logica_no_depende_de_la_api_ni_de_los_datos_ni_del_framework():
    prohibidos = ("fastapi", "starlette", "pymongo", "back.api", "back.datos")
    for archivo in _archivos("back/logica", ".py"):
        for modulo in _importaciones_python(archivo):
            assert not modulo.startswith(prohibidos), f"{archivo.name} importa {modulo}"


def test_la_api_solo_toca_los_datos_al_ensamblar_en_dependencias():
    for archivo in _archivos("back/api", ".py"):
        if archivo.name == "dependencias.py":
            continue
        for modulo in _importaciones_python(archivo):
            assert not modulo.startswith("back.datos"), f"{archivo.name} importa {modulo}"


def test_la_gui_no_se_comunica_con_el_servidor_ni_conoce_otras_capas():
    for archivo in _archivos("front/gui", ".js"):
        texto = archivo.read_text(encoding="utf-8")
        assert "fetch(" not in texto, archivo.name
        assert "/com/" not in texto and "/controlador/" not in texto, archivo.name


def test_el_controlador_no_toca_la_pantalla_ni_hace_peticiones():
    for archivo in _archivos("front/controlador", ".js"):
        texto = archivo.read_text(encoding="utf-8")
        assert "document." not in texto, archivo.name
        assert "fetch(" not in texto, archivo.name


def test_la_comunicacion_no_toca_la_pantalla_ni_conoce_la_interfaz():
    for archivo in _archivos("front/com", ".js"):
        texto = archivo.read_text(encoding="utf-8")
        assert "document." not in texto, archivo.name
        assert "/gui/" not in texto and "/controlador/" not in texto, archivo.name