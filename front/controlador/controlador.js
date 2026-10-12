// CONTROLADOR: decide qué hacer cuando la persona actúa. Une la interfaz (gui)
// con la comunicación (com). No pinta directamente ni hace peticiones por su cuenta.

import * as api from "../com/clienteApi.js";
import * as vista from "../gui/vista.js";

let usuarioActual = null;

async function cargarPanel() {
  try {
    const usuarios = await api.listarUsuarios();
    vista.mostrarUsuarios(usuarios, usuarioActual.id);
  } catch (error) {
    vista.mostrarMensaje("admin", error.message);
  }
}

async function entrar(usuario) {
  usuarioActual = usuario;
  vista.mostrarCuenta(usuario);
  if (usuario.rol === "admin") {
    await cargarPanel();
  }
}

async function alIniciarSesion(email, password) {
  vista.ocupado(true);
  try {
    const usuario = await api.iniciarSesion(email, password);
    vista.limpiarContrasenas();
    await entrar(usuario);
  } catch (error) {
    vista.mostrarMensaje("login", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function alRegistrar(email, password) {
  vista.ocupado(true);
  try {
    const usuario = await api.registrar(email, password);
    vista.limpiarContrasenas();
    vista.mostrar("login");
    const texto = usuario.estado === "pendiente"
      ? "Cuenta creada. Confirma tu correo antes de iniciar sesión."
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
    vista.mostrar("login");
    vista.mostrarMensaje("login", "Tu cuenta ha sido eliminada.", "ok");
  } catch (error) {
    vista.mostrarMensaje("cuenta", error.message);
  } finally {
    vista.ocupado(false);
  }
}

async function iniciar() {
  vista.enlazar({
    alIniciarSesion, alRegistrar, alCerrarSesion,
    alComprobarActivo, alEliminarUsuario, alEliminarMiCuenta,
  });
  try {
    // Mantiene la sesión entre recargas: si la cookie sigue siendo válida, entra directo
    const usuario = await api.sesionActual();
    await entrar(usuario);
  } catch (error) {
    // Sin sesión válida se redirige a la pantalla de login
    vista.mostrar("login");
    if (error.estado !== 401) {
      vista.mostrarMensaje("login", error.message);
    }
  }
}

iniciar();