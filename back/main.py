from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def inicio():
    return "<h1>SplitMate</h1><p>Reparte gastos con tus amigos. En construcción.</p>"