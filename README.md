# SplitMate

Aplicación web tipo SaaS para repartir gastos compartidos entre amigos. Este Sprint 1 entrega la base: gestión de usuarios con registro, confirmación por correo, inicio de sesión local y con GitHub, roles y administración, organizada en capas.

Proyecto individual de *Procesos de Ingeniería del Software* (curso 2026-2027).

- **URL pública:** https://splitmate-731709189293.europe-west1.run.app (Google Cloud Run). La primera carga tras un rato de inactividad puede tardar unos segundos (arranque en frío de la capa gratuita).
- **Repositorio:** https://github.com/B1lly05/SplitMate

## Tecnologías

| Tecnología | Por qué se ha elegido |
|---|---|
| Python 3.14 + FastAPI | Lenguaje legible y framework ligero que permite separar API, lógica y datos y servir el frontend desde el mismo origen. |
| JavaScript sin framework (módulos ES) | Frontend pequeño que separa interfaz, controlador y cliente de comunicación sin dependencias. |
| MongoDB Atlas (M0) | Base de datos real con capa gratuita permanente; la misma cadena de conexión sirve en local y en producción, y un índice único garantiza el email único. |
| argon2-cffi | Hash seguro para las contraseñas; nunca se guardan en claro. |
| httpx | Cliente HTTP para hablar con GitHub (OAuth) y con Brevo (correo). |
| Brevo (API de correo transaccional) | Capa gratuita de envío; se usa su API por HTTPS porque el SMTP directo suele estar bloqueado en nubes gratuitas. |
| pytest + mongomock | Pruebas automáticas rápidas sin necesidad de una base de datos real. |
| Docker + Google Cloud Run | Contenedor con capa gratuita y URL pública. |
| Cloud Build | Despliegue continuo automático cada vez que cambia `main`. |
| GitHub + GitHub Actions | Control de versiones, pull requests e integración continua. |

## Arquitectura

```
back/
  main.py          aplicación FastAPI, routers y archivos estáticos
  api/             capa API: endpoints, sesión, traducción de errores a HTTP
  logica/          capa de lógica: reglas de negocio y contratos (interfaces)
  datos/           capa de acceso a datos: memoria y MongoDB
  externos/        servicios externos: GitHub (OAuth) y Brevo (correo)
front/
  gui/             capa de presentación (HTML, CSS y vista)
  controlador/     une la interfaz con el cliente
  com/             cliente de comunicación: el único que hace `fetch`
tests/             pruebas automáticas
```

El backend sirve el frontend desde el mismo origen. El cliente no accede a la base de datos ni ejecuta lógica de negocio: solo se comunica con la API.

Recorrido de una petición: `GUI → controlador → com → API → lógica → datos → MongoDB`. La lógica define interfaces (repositorios, enviador de correo) y las capas de datos y servicios externos las implementan, de modo que cambiar de base de datos o de proveedor de correo no toca la lógica. `back/api/dependencias.py` es el único sitio que decide qué implementación se usa. `tests/test_arquitectura.py` comprueba las fronteras entre capas automáticamente.

## Funcionalidad

- Registro local con confirmación por correo: la cuenta queda *pendiente* hasta pulsar el enlace (caduca en 24 h, vale una vez) y una cuenta pendiente no puede iniciar sesión. Se puede reenviar el correo.
- Inicio de sesión local y con GitHub. Cierre de sesión que invalida la sesión en el servidor. La sesión se mantiene entre recargas.
- Roles de usuario y administrador, aplicados siempre en el servidor.
- El administrador puede listar usuarios (email, rol, estado) y comprobar si uno está activo. Activo significa confirmado por correo o creado por OAuth, y no eliminado.
- Un administrador puede eliminar a cualquier usuario y un usuario normal solo su propia cuenta. Una cuenta eliminada no puede volver a entrar.
- **Grupos de gasto compartido:** cualquier usuario crea grupos y añade a otros usuarios activos por su email. Solo los miembros ven y modifican un grupo (comprobado en el servidor).
- **Gastos y saldos:** se registra quién pagó, cuánto y entre quiénes se reparte a partes iguales. La aplicación calcula el balance de cada persona y propone el mínimo de pagos para saldar cuentas. Los pagos realizados se registran y actualizan los saldos. Los importes se guardan en céntimos enteros para evitar errores de redondeo.
- Registro (log) de la actividad y manejo de errores con mensajes claros: toda respuesta de error tiene el formato `{"error": "mensaje"}` y los fallos internos no exponen detalles.

## Ejecutar en local

Requisitos: Python 3.14 y una base de datos MongoDB (por ejemplo, un clúster gratuito de Atlas).

```bash
git clone https://github.com/B1lly05/SplitMate.git
cd SplitMate
python -m venv .venv
.venv\Scripts\activate          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Windows (Mac/Linux: cp .env.example .env) y rellenar los valores
uvicorn back.main:app --reload
```

La aplicación queda en http://127.0.0.1:8000 (usa `127.0.0.1`, no `localhost`, para que la cookie del inicio de sesión con GitHub funcione). La documentación automática de la API está en `/docs`.

Notas para el entorno local:

- Sin `MONGODB_URI` la aplicación arranca con almacenamiento en memoria (los datos se pierden al reiniciar) y lo avisa en el log.
- Usa una base de datos distinta a la de producción (`MONGODB_DB`) para no mezclar datos.
- Sin `BREVO_API_KEY` y `MAIL_REMITENTE` no se envían correos. Para probar sin correo se puede poner `CONFIRMAR_AUTOMATICAMENTE=true`, que activa las cuentas al registrarse (no usar en producción).
- Para probar el acceso con GitHub hay que crear una *OAuth App* en GitHub (Settings → Developer settings → OAuth Apps) con la URL de retorno `http://127.0.0.1:8000/auth/github/callback`. Para producción se necesita otra app con la URL pública, porque GitHub admite una sola URL de retorno por aplicación.

## Ejecutar las pruebas

Con el entorno virtual activo:

```bash
pytest
```

Las pruebas no tocan ninguna base de datos ni servicio externo reales: `tests/conftest.py` vacía las variables de conexión y los servicios externos se sustituyen por versiones simuladas. Es el mismo comando que ejecuta la integración continua.

## Variables de entorno

Solo se indican los nombres; los valores van en `.env` (ignorado por Git) y, en producción, en las variables del servicio de Cloud Run. Ver `.env.example`.

| Variable | Para qué sirve |
|---|---|
| `MONGODB_URI` | Cadena de conexión de MongoDB Atlas (secreta). |
| `MONGODB_DB` | Nombre de la base de datos. |
| `CONFIRMAR_AUTOMATICAMENTE` | Si es `true`, las cuentas se activan sin correo (solo para desarrollo). |
| `COOKIE_SEGURA` | `true` en producción (https) para marcar la cookie de sesión como `Secure`. |
| `ADMIN_EMAIL` | Correo del primer administrador. |
| `ADMIN_PASSWORD` | Contraseña del primer administrador (secreta). |
| `LOG_LEVEL` | Nivel del registro de actividad (opcional). |
| `BASE_URL` | URL base de la aplicación, sin barra final; se usa en los enlaces del correo y en el retorno de GitHub. |
| `GITHUB_CLIENT_ID` | Identificador de la OAuth App de GitHub. |
| `GITHUB_CLIENT_SECRET` | Secreto de la OAuth App de GitHub (secreto). |
| `BREVO_API_KEY` | Clave de la API de Brevo (secreta). |
| `MAIL_REMITENTE` | Correo remitente verificado en Brevo. |
| `MAIL_NOMBRE` | Nombre que aparece como remitente. |

## Acceso como administrador

El primer administrador se crea automáticamente al arrancar la aplicación a partir de `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Se hace así para que sea reproducible y no dependa de editar la base de datos a mano. La operación es idempotente y nunca promociona una cuenta ya existente. La contraseña se guarda con hash.

Las credenciales del administrador de la instancia desplegada no están en el repositorio: se envían aparte junto con la entrega. Para acceder, inicia sesión con ese correo y contraseña; el panel de administración aparece en la pantalla de la cuenta.

## Flujo de trabajo y despliegue

GitHub Flow: una rama por cambio, pruebas en local, pull request a `main` y CI en verde antes de integrar. GitHub Actions ejecuta `pytest` en cada pull request y en cada cambio en `main`. Cada cambio que llega a `main` se despliega automáticamente en Cloud Run mediante Cloud Build. El último commit de cada hito está etiquetado (`hito-1`, `hito-2`, `hito-3`, `hito-4`).

## Limitaciones conocidas

- No hay límite de intentos de inicio de sesión (fuerza bruta).
- No hay token anti-CSRF; la protección se apoya en `SameSite=Lax` y en que la API solo acepta JSON.
- La sesión dura 8 horas y no se renueva.
- Atlas permite conexiones desde cualquier IP, porque Cloud Run no tiene IP fija; se compensa con un usuario de base de datos de contraseña larga y la cadena solo en variables de entorno. Brevo se usa sin restricción de IP por el mismo motivo.
- Los correos de confirmación pueden caer en la carpeta de spam al enviarse sin un dominio propio autenticado. El reenvío (con una espera mínima de 60 s) mitiga el problema; no hay un límite global de envíos.
- La contraseña del administrador inicial vive en una variable de entorno.
- Los registros guardan el email en los inicios de sesión fallidos.
- `mongomock` no es idéntico a un MongoDB real.
- No se ha implementado comunicación por WebSocket (`api-ws`): la especificación solo exige una API.
- Los gastos solo se pueden repartir a partes iguales y no se pueden editar (solo borrar y volver a crear).
- Una cuenta eliminada sigue figurando en los grupos donde estaba, para que los saldos sigan cuadrando.
- Para añadir a alguien a un grupo basta su email: cualquier usuario con sesión puede comprobar si un correo está registrado.
