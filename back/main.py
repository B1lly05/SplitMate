from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from back.api import auth, confirmacion, dependencias, grupos, oauth, usuarios
from back.api.errores import registrar_manejadores
from back.logs import configurar_logging
FRONT = Path(__file__).resolve().parent.parent / "front"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    configurar_logging()
    dependencias.preparar()  # conecta con la base de datos al arrancar
    yield


app = FastAPI(lifespan=ciclo_de_vida)
registrar_manejadores(app)
app.include_router(usuarios.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(confirmacion.router)
app.include_router(grupos.router)
app.mount("/front", StaticFiles(directory=FRONT), name="front")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONT / "gui" / "index.html")