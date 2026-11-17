// CONTROLADOR: decide qué hacer cuando la persona actúa. Une la interfaz (gui)
// con la comunicación (com). No pinta directamente ni hace peticiones por su cuenta.

import * as api from "../com/clienteApi.js";
import * as vista from "../gui/vista.js";
import { eurosACentimos } from "./dinero.js";

let usuarioActual = null;
let grupoActual = null; // detalle del grupo que se está viendo

// Textos fijos para los códigos de error del inicio de sesión con GitHub.
// Un código desconocido nunca se muestra tal cual: se usa el mensaje genérico.
const MENSAJES_OAUTH = {
  oauth_cancelado: "Has cancelado el acceso con GitHub.",
  oauth_fallo: "No se pudo iniciar sesión con GitHub. Inténtalo de nuevo.",
  oauth_sin_email: "Tu cuenta de GitHub no tiene ningún correo verificado.",
  cuenta_eliminada: "La cuenta ha sido eliminada.",
  oauth_no_configurado: "El acceso con GitHub no está disponible ahora mismo.",
};
const MENSAJE_OAUTH_GENERICO = "No se pudo iniciar sesión con GitHub.";

// Ejecuta una acción con los botones bloqueados y enseña el error en la zona indicada.
async function conOcupado(zona, accion) {
  vista.ocupado(true);
  try {
    await accion();
  } catch (error) {
    vista.mostrarMensaje(zona, error.message);
  } finally {
    vista.ocupado(false);
  }
}

// ---------- sesión ----------
async function entrar(usuario) {
  usuarioActual = usuario;
  vista.mostrarSesion(usuario);
  await irAGrupos();
}

const alIniciarSesion = (email, password) => conOcupado("login", async () => {
  const usuario = await api.iniciarSesion(email, password);
  vista.limpiarContrasenas();
  await entrar(usuario);
});

async function alRegistrar(email, password) {
  vista.ocupado(true);
  try {
    const usuario = await api.registrar(email, password);
    vista.limpiarContrasenas();
    vista.mostrar("login");
    const texto = usuario.estado === "pendiente"
      ? "Cuenta creada. Te hemos enviado un correo para confirmarla (revisa también la carpeta de spam)."
      : "Cuenta creada. Ya puedes iniciar sesión.";
    vista.mostrarMensaje("login", texto, "ok");
  } catch (error) {
    vista.mostrarMensaje("registro", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function alCerrarSesion() {
  vista.ocupado(true);
  usuarioActual = null;
  grupoActual = null;
  try {
    await api.cerrarSesion();
    vista.mostrar("login");
  } catch (error) {
    vista.mostrar("login");
    vista.mostrarMensaje("login", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function alReenviarConfirmacion(email) {
  if (!email.trim()) {
    vista.mostrarMensaje("login", "Escribe tu email en el formulario y pulsa de nuevo «Reenviar».");
    return;
  }
  vista.ocupado(true);
  try {
    const respuesta = await api.reenviarConfirmacion(email);
    vista.mostrarMensaje("login", respuesta.mensaje, "ok");
  } catch (error) {
    vista.mostrarMensaje("login", error.message);
  } finally {
    vista.ocupado(false);
  }
}

// Confirma la cuenta con el token del enlace del correo. Devuelve el aviso a mostrar.
async function confirmarCuenta(token) {
  try {
    await api.confirmarCuenta(token);
    return { texto: "Cuenta confirmada. Ya puedes iniciar sesión.", tipo: "ok" };
  } catch (error) {
    return { texto: error.message, tipo: "error" };
  }
}

// ---------- navegación ----------
async function irAGrupos() {
  vista.mostrar("grupos");
  try {
    vista.mostrarGrupos(await api.listarGrupos());
  } catch (error) {
    vista.mostrarMensaje("grupos", error.message);
  }
}

async function cargarPanel() {
  try {
    vista.mostrarUsuarios(await api.listarUsuarios(), usuarioActual.id);
  } catch (error) {
    vista.mostrarMensaje("admin", error.message);
  }
}

async function alNavegar(destino) {
  if (destino === "grupos") {
    await irAGrupos();
  } else if (destino === "cuenta") {
    vista.mostrarCuenta(usuarioActual);
  } else if (destino === "admin") {
    vista.mostrar("admin");
    await cargarPanel();
  }
}

// ---------- grupos ----------
async function abrirGrupo(id, aviso) {
  grupoActual = await api.obtenerGrupo(id);
  vista.mostrarGrupo(grupoActual, usuarioActual.id);
  if (aviso) vista.mostrarMensaje("grupo", aviso, "ok");
}

const alCrearGrupo = (nombre) => conOcupado("grupos", async () => {
  const grupo = await api.crearGrupo(nombre);
  await abrirGrupo(grupo.id, "Grupo creado. Añade a tus amigos en la pestaña Miembros.");
});

const alAbrirGrupo = (id) => conOcupado("grupos", () => abrirGrupo(id));

const alAnadirMiembro = (email) => conOcupado("grupo", async () => {
  const respuesta = await api.anadirMiembro(grupoActual.id, email);
  await abrirGrupo(
    grupoActual.id,
    respuesta.resultado === "invitado"
      ? "Esa persona aún no tiene cuenta: le hemos enviado una invitación por correo."
      : "Miembro añadido.",
  );
});

function alNuevoGasto() {
  vista.abrirDialogoGasto(grupoActual.miembros, usuarioActual.id);
}

async function alGuardarGasto({ concepto, importe, pagadorId, participantes, pesos }) {
  const centimos = eurosACentimos(importe);
  if (centimos === null) {
    vista.mostrarMensaje("gasto", "Escribe un importe válido, por ejemplo 12,50.");
    return;
  }
  vista.ocupado(true);
  try {
    await api.crearGasto(grupoActual.id, {
      concepto, importe: centimos, pagador_id: pagadorId, participantes, pesos,
    });
    vista.cerrarDialogoGasto();
    await abrirGrupo(grupoActual.id, "Gasto añadido.");
  } catch (error) {
    vista.mostrarMensaje("gasto", error.message); // el error se ve dentro de la ventana
  } finally {
    vista.ocupado(false);
  }
}

const alEliminarGasto = (gastoId) => conOcupado("grupo", async () => {
  if (!vista.confirmar("¿Eliminar este gasto? Los saldos se recalcularán.")) return;
  await api.eliminarGasto(grupoActual.id, gastoId);
  await abrirGrupo(grupoActual.id, "Gasto eliminado.");
});

const alMarcarPagado = (deId, aId, importe) => conOcupado("grupo", async () => {
  if (!vista.confirmar("¿Confirmas que este pago ya se ha realizado?")) return;
  await api.crearLiquidacion(grupoActual.id, { de_id: deId, a_id: aId, importe });
  await abrirGrupo(grupoActual.id, "Pago registrado.");
});

const alRecordar = (deudorId) => conOcupado("grupo", async () => {
  const { importe } = await api.recordarPago(grupoActual.id, deudorId);
  const euros = (importe / 100).toFixed(2).replace(".", ",");
  await abrirGrupo(grupoActual.id, `Recordatorio enviado por correo (${euros} €).`);
});

// ---------- administración y cuenta ----------
async function alComprobarActivo(id, email) {
  vista.ocupado(true);
  try {
    const resultado = await api.usuarioActivo(id);
    const texto = resultado.activo ? "cuenta activa" : "cuenta no activa";
    vista.mostrarMensaje("admin", `${email}: ${texto}`, "ok");
  } catch (error) {
    vista.mostrarMensaje("admin", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function alEliminarUsuario(id, email) {
  if (!vista.confirmar(`¿Eliminar la cuenta de ${email}?`)) return;
  vista.ocupado(true);
  try {
    await api.eliminarUsuario(id);
    await cargarPanel();
    vista.mostrarMensaje("admin", `Cuenta de ${email} eliminada.`, "ok");
  } catch (error) {
    vista.mostrarMensaje("admin", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function alEliminarMiCuenta() {
  if (!vista.confirmar("¿Seguro que quieres eliminar tu cuenta? No podrás volver a entrar.")) return;
  vista.ocupado(true);
  try {
    await api.eliminarUsuario(usuarioActual.id);
    try {
      await api.cerrarSesion();
    } catch {
      // la cuenta ya está eliminada: si falla el cierre, la sesión deja de valer igualmente
    }
    usuarioActual = null;
    grupoActual = null;
    vista.mostrar("login");
    vista.mostrarMensaje("login", "Tu cuenta ha sido eliminada.", "ok");
  } catch (error) {
    vista.mostrarMensaje("cuenta", error.message);
  } finally {
    vista.ocupado(false);
  }
}

// ---------- arranque ----------
async function iniciar() {
  const codigoError = vista.leerErrorDeUrl(); // se leen antes de pintar nada
  const tokenConfirmacion = vista.leerTokenConfirmacion();
  vista.enlazar({
    alIniciarSesion, alRegistrar, alCerrarSesion, alReenviarConfirmacion, alNavegar,
    alCrearGrupo, alAbrirGrupo, alAnadirMiembro, alNuevoGasto, alGuardarGasto,
    alEliminarGasto, alMarcarPagado, alRecordar, alComprobarActivo, alEliminarUsuario,
    alEliminarMiCuenta,
  });
  const aviso = tokenConfirmacion !== null ? await confirmarCuenta(tokenConfirmacion) : null;
  try {
    // Mantiene la sesión entre recargas: si la cookie sigue siendo válida, entra directo
    const usuario = await api.sesionActual();
    await entrar(usuario);
  } catch (error) {
    // Sin sesión válida se redirige a la pantalla de login
    vista.mostrar("login");
    if (aviso !== null) {
      vista.mostrarMensaje("login", aviso.texto, aviso.tipo);
    } else if (codigoError !== null) {
      vista.mostrarMensaje("login", MENSAJES_OAUTH[codigoError] ?? MENSAJE_OAUTH_GENERICO);
    } else if (error.estado !== 401) {
      vista.mostrarMensaje("login", error.message);
    }
  }
}

iniciar();
