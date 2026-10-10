from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from back.api import usuarios
from back.api.errores import registrar_manejadores

app = FastAPI()
registrar_manejadores(app)
app.include_router(usuarios.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def inicio():
    return "<h1>SplitMate</h1><p>Reparte gastos con tus amigos. En construcción.</p>"