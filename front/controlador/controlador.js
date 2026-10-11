// CONTROLADOR: decide qué hacer cuando la persona actúa. Une la interfaz (gui)
// con la comunicación (com). No pinta directamente ni hace peticiones por su cuenta.

import * as api from "../com/clienteApi.js";
import * as vista from "../gui/vista.js";

async function alIniciarSesion(email, password) {
  vista.ocupado(true);
  try {
    const usuario = await api.iniciarSesion(email, password);
    vista.limpiarContrasenas();
    vista.mostrarCuenta(usuario);
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

async function iniciar() {
  vista.enlazar({ alIniciarSesion, alRegistrar, alCerrarSesion });
  try {
    // Mantiene la sesión entre recargas: si la cookie sigue siendo válida, entra directo
    const usuario = await api.sesionActual();
    vista.mostrarCuenta(usuario);
  } catch (error) {
    // Sin sesión válida se redirige a la pantalla de login
    vista.mostrar("login");
    if (error.estado !== 401) {
      vista.mostrarMensaje("login", error.message);
    }
  }
}

iniciar();