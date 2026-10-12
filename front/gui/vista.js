// CAPA DE PRESENTACIÓN (GUI): pinta pantallas y recoge lo que escribe la persona.
// No sabe nada del servidor ni de la comunicación: avisa al controlador mediante
// las funciones que éste le entrega en enlazar().

const $ = (id) => document.getElementById(id);
const PANTALLAS = ["login", "registro", "cuenta"];
const ZONAS_DE_MENSAJE = ["login", "registro", "cuenta", "admin"];

export function mostrar(pantalla) {
  for (const nombre of PANTALLAS) {
    $(`pantalla-${nombre}`).hidden = nombre !== pantalla;
  }
  for (const zona of ZONAS_DE_MENSAJE) {
    mostrarMensaje(zona, "");
  }
  if (pantalla !== "cuenta") {
    limpiarPanel(); // no se dejan datos de administración en pantalla
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
  // Solo es apariencia: el servidor es quien impide el acceso a quien no es administrador
  $("panel-admin").hidden = usuario.rol !== "admin";
}

export function confirmar(texto) {
  return window.confirm(texto);
}

export function ocupado(estaOcupado) {
  for (const boton of document.querySelectorAll("button")) {
    if (boton.dataset.bloqueado) continue; // los botones desactivados a propósito siguen así
    boton.disabled = estaOcupado;
  }
}

function crearBoton(texto, accion, usuario) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.textContent = texto;
  boton.dataset.accion = accion;
  boton.dataset.id = String(usuario.id);
  boton.dataset.email = usuario.email;
  return boton;
}

export function mostrarUsuarios(usuarios, idActual) {
  const cuerpo = $("tabla-usuarios-cuerpo");
  cuerpo.replaceChildren();
  for (const usuario of usuarios) {
    const fila = document.createElement("tr");
    for (const texto of [usuario.email, usuario.rol, usuario.estado]) {
      const celda = document.createElement("td");
      celda.textContent = texto;
      fila.appendChild(celda);
    }

    const acciones = document.createElement("td");
    acciones.appendChild(crearBoton("¿Activo?", "activo", usuario));

    const eliminar = crearBoton("Eliminar", "eliminar", usuario);
    const esYo = usuario.id === idActual;
    if (usuario.estado === "eliminado" || esYo) {
      eliminar.disabled = true;
      eliminar.dataset.bloqueado = "si";
    }
    if (esYo) {
      eliminar.title = "Para borrar tu cuenta usa «Eliminar mi cuenta»";
    }
    acciones.appendChild(eliminar);

    fila.appendChild(acciones);
    cuerpo.appendChild(fila);
  }
}

function limpiarPanel() {
  $("tabla-usuarios-cuerpo").replaceChildren();
  $("panel-admin").hidden = true;
}

export function enlazar({
  alIniciarSesion, alRegistrar, alCerrarSesion,
  alComprobarActivo, alEliminarUsuario, alEliminarMiCuenta,
}) {
  $("form-login").addEventListener("submit", (evento) => {
    evento.preventDefault();
    alIniciarSesion($("login-email").value, $("login-password").value);
  });

  $("form-registro").addEventListener("submit", (evento) => {
    evento.preventDefault();
    alRegistrar($("registro-email").value, $("registro-password").value);
  });

  $("boton-logout").addEventListener("click", () => alCerrarSesion());
  $("boton-eliminar-cuenta").addEventListener("click", () => alEliminarMiCuenta());

  // Un solo escuchador para todos los botones de la tabla
  $("tabla-usuarios-cuerpo").addEventListener("click", (evento) => {
    const boton = evento.target.closest("button[data-accion]");
    if (!boton || boton.disabled) return;
    const id = Number(boton.dataset.id);
    const email = boton.dataset.email;
    if (boton.dataset.accion === "activo") {
      alComprobarActivo(id, email);
    } else if (boton.dataset.accion === "eliminar") {
      alEliminarUsuario(id, email);
    }
  });

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