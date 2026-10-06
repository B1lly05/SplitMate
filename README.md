# SplitMate

Aplicación web tipo SaaS para repartir gastos compartidos entre amigos, con gestión de usuarios y roles.
Proyecto individual de *Procesos de Ingeniería del Software* (curso 2026-2027) — Sprint 1.

> Estado: en desarrollo (Hito 1). Este README se completa a medida que avanza el proyecto.

## URL pública

_Pendiente de desplegar (Google Cloud Run)._

## Tecnologías

| Tecnología | Justificación |
|---|---|
| Python 3.12 | Lenguaje legible y con buen ecosistema para web, pruebas y autenticación. |
| FastAPI | Framework web ligero que permite separar API, lógica y datos y servir el frontend desde el mismo origen. |
| pytest | Framework de pruebas sencillo para automatizar las pruebas de la capa lógica. |
| PostgreSQL (servicio gratuito externo, por decidir) | Base de datos real, de modo que los datos sobreviven a reinicios. |
| GitHub Actions | CI integrado en el repositorio: ejecuta las pruebas en cada PR y en `main`. |
| Google Cloud Run | Despliegue continuo con capa gratuita y URL pública. |

## Arquitectura

```
back/
  api/        capa API (endpoints)
  logica/     capa de lógica de negocio
  datos/      capa de acceso a datos
front/
  gui/          capa de presentación (interfaz)
  controlador/  conecta la interfaz con el cliente
  com/          cliente de comunicación con la API
tests/        pruebas automatizadas
```

## Ejecutar en local

```bash
git clone <URL-del-repositorio>
cd splitmate
python -m venv .venv
.venv\Scripts\activate          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env            # y rellenar los valores
uvicorn back.main:app --reload
```

La aplicación queda en http://127.0.0.1:8000.

## Ejecutar las pruebas

```bash
pytest
```

## Variables de entorno

Solo nombres; los valores van en `.env` (no se sube al repositorio). Ver `.env.example`.

- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `OAUTH_CLIENT_ID`
- `OAUTH_CLIENT_SECRET`
- `MAIL_API_KEY`

_Lista provisional: se ajustará según las tecnologías finales._

## Acceso como administrador

_Pendiente de definir (Hito 3). Las credenciales de prueba se envían junto con la entrega, nunca en el repositorio._

## Flujo de trabajo

GitHub Flow: una rama por cambio, pruebas en local, pull request a `main` y CI en verde antes de integrar.
Cada cambio que llega a `main` se despliega automáticamente.
