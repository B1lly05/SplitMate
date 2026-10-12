// CAPA DE COMUNICACIÓN: es la única que habla con el servidor.
// No conoce la interfaz ni toca la pantalla.

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

function mensajeDeError(datos, estado) {
  if (datos && datos.error) return datos.error;
  if (estado === 422) return "Faltan datos o no son válidos.";
  return "Ha ocurrido un error inesperado.";
}

async function peticion(metodo, ruta, cuerpo) {
  const opciones = { method: metodo, credentials: "same-origin", headers: {} };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw new ErrorApi("No se pudo conectar con el servidor. Inténtalo de nuevo.", 0);
  }

  if (respuesta.status === 204) return null;

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    // respuesta sin cuerpo JSON
  }
  if (!respuesta.ok) {
    throw new ErrorApi(mensajeDeError(datos, respuesta.status), respuesta.status);
  }
  return datos;
}

export const registrar = (email, password) =>
  peticion("POST", "/usuarios", { email, password });

export const iniciarSesion = (email, password) =>
  peticion("POST", "/auth/login", { email, password });

export const cerrarSesion = () => peticion("POST", "/auth/logout");

export const sesionActual = () => peticion("GET", "/auth/sesion");

export const listarUsuarios = () => peticion("GET", "/usuarios");

export const usuarioActivo = (id) => peticion("GET", `/usuarios/${id}/activo`);

export const eliminarUsuario = (id) => peticion("DELETE", `/usuarios/${id}`);