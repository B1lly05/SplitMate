// CAPA DE PRESENTACIÓN (GUI): pinta pantallas y recoge lo que escribe la persona.
// No sabe nada del servidor ni de la comunicación: avisa al controlador mediante
// las funciones que éste le entrega en enlazar().

const $ = (id) => document.getElementById(id);
const PANTALLAS = ["login", "registro", "cuenta"];

export function mostrar(pantalla) {
  for (const nombre of PANTALLAS) {
    $(`pantalla-${nombre}`).hidden = nombre !== pantalla;
  }
  for (const zona of ["login", "registro"]) {
    mostrarMensaje(zona, "");
  }
}

export function mostrarMensaje(zona, texto, tipo = "error") {
  const elemento = $(`mensaje-${zona}`);
  elemento.textContent = texto; // textContent: nunca se inserta HTML
  elemento.className = texto ? `mensaje ${tipo}` : "mensaje";
}

export function mostrarCuenta(usuario) {
  $("cuenta-email").textContent = usuario.email;
  $("cuenta-rol").textContent = usuario.rol;
  $("cuenta-estado").textContent = usuario.estado;
  mostrar("cuenta");
}

export function ocupado(estaOcupado) {
  for (const boton of document.querySelectorAll("button")) {
    boton.disabled = estaOcupado;
  }
}

export function enlazar({ alIniciarSesion, alRegistrar, alCerrarSesion }) {
  $("form-login").addEventListener("submit", (evento) => {
    evento.preventDefault();
    alIniciarSesion($("login-email").value, $("login-password").value);
  });

  $("form-registro").addEventListener("submit", (evento) => {
    evento.preventDefault();
    alRegistrar($("registro-email").value, $("registro-password").value);
  });

  $("boton-logout").addEventListener("click", () => alCerrarSesion());

  $("ir-registro").addEventListener("click", (evento) => {
    evento.preventDefault();
    mostrar("registro");
  });
  $("ir-login").addEventListener("click", (evento) => {
    evento.preventDefault();
    mostrar("login");
  });
}

export function limpiarContrasenas() {
  $("login-password").value = "";
  $("registro-password").value = "";
}