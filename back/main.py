from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from back.api import auth, usuarios
from back.api.errores import registrar_manejadores

FRONT = Path(__file__).resolve().parent.parent / "front"

app = FastAPI()
registrar_manejadores(app)
app.include_router(usuarios.router)
app.include_router(auth.router)
app.mount("/front", StaticFiles(directory=FRONT), name="front")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(FRONT / "gui" / "index.html")