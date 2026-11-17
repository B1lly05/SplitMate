// CAPA DE PRESENTACIÓN (GUI): pinta pantallas y recoge lo que escribe la persona.
// No sabe nada del servidor ni de la comunicación: avisa al controlador mediante
// las funciones que éste le entrega en enlazar().

const $ = (id) => document.getElementById(id);
const PANTALLAS = ["login", "registro", "grupos", "grupo", "cuenta", "admin"];
const PANTALLAS_DE_ACCESO = ["login", "registro"];
const ZONAS_DE_MENSAJE = ["login", "registro", "grupos", "grupo", "gasto", "cuenta", "admin"];
const LISTAS_PRIVADAS = [
  "lista-grupos", "lista-gastos", "lista-saldos", "lista-transferencias",
  "lista-liquidaciones", "lista-miembros", "lista-invitaciones", "lista-actividad",
  "grupo-chips", "tabla-usuarios-cuerpo",
];

const formatoEuros = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });
const euros = (centimos) => formatoEuros.format(centimos / 100);
const nombreCorto = (usuario) => usuario.email.split("@")[0];
const fechaCorta = (iso) =>
  new Date(iso).toLocaleDateString("es-ES", { day: "numeric", month: "short" });

const fechaYHora = (iso) =>
  new Date(iso).toLocaleString("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

let grupoMostrado = null;

// textContent en todo: nunca se inserta HTML que venga del servidor ni de otra persona
function el(etiqueta, clase, texto) {
  const elemento = document.createElement(etiqueta);
  if (clase) elemento.className = clase;
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function avatar(usuario, clase = "") {
  const a = el("span", `avatar ${clase}`.trim(), (usuario.email[0] || "?").toUpperCase());
  a.style.setProperty("--tono", String((usuario.id * 67) % 360));
  a.setAttribute("aria-hidden", "true");
  return a;
}

function limpiarDatosPrivados() {
  for (const id of LISTAS_PRIVADAS) $(id).replaceChildren();
  grupoMostrado = null;
}

// ---------- navegación ----------
export function mostrar(pantalla) {
  for (const nombre of PANTALLAS) {
    $(`pantalla-${nombre}`).hidden = nombre !== pantalla;
  }
  const esAcceso = PANTALLAS_DE_ACCESO.includes(pantalla);
  $("barra").hidden = esAcceso;
  const activa = pantalla === "grupo" ? "grupos" : pantalla;
  for (const boton of document.querySelectorAll("[data-nav]")) {
    boton.classList.toggle("activa", boton.dataset.nav === activa);
  }
  for (const zona of ZONAS_DE_MENSAJE) mostrarMensaje(zona, "");
  if (esAcceso) {
    limpiarDatosPrivados(); // al cerrar sesión no se deja nada de la cuenta en pantalla
    $("nav-admin").hidden = true;
  }
}

export function mostrarMensaje(zona, texto, tipo = "error") {
  const elemento = $(`mensaje-${zona}`);
  elemento.textContent = texto;
  elemento.className = texto ? `mensaje ${tipo}` : "mensaje";
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

// ---------- sesión y cuenta ----------
export function mostrarSesion(usuario) {
  const pequeno = $("barra-avatar");
  pequeno.textContent = (usuario.email[0] || "?").toUpperCase();
  pequeno.style.setProperty("--tono", String((usuario.id * 67) % 360));
  // Solo es apariencia: el servidor es quien impide el acceso a quien no es administrador
  $("nav-admin").hidden = usuario.rol !== "admin";
}

export function mostrarCuenta(usuario) {
  const grande = $("cuenta-avatar");
  grande.textContent = (usuario.email[0] || "?").toUpperCase();
  grande.style.setProperty("--tono", String((usuario.id * 67) % 360));
  $("cuenta-email").textContent = usuario.email;
  $("cuenta-rol").textContent = usuario.rol;
  $("cuenta-estado").textContent = usuario.estado;
  mostrar("cuenta");
}

// ---------- grupos ----------
export function mostrarGrupos(grupos) {
  const lista = $("lista-grupos");
  lista.replaceChildren();
  for (const grupo of grupos) {
    const item = el("li");
    const boton = el("button", "tarjeta-grupo");
    boton.type = "button";
    boton.dataset.grupoId = String(grupo.id);
    boton.append(
      avatar({ id: grupo.id, email: grupo.nombre }),
      (() => {
        const texto = el("div");
        texto.append(
          el("strong", "", grupo.nombre),
          el("span", "meta", grupo.miembros === 1 ? "1 miembro" : `${grupo.miembros} miembros`),
        );
        return texto;
      })(),
    );
    item.appendChild(boton);
    lista.appendChild(item);
  }
  $("vacio-grupos").hidden = grupos.length > 0;
  $("grupo-nombre").value = "";
}

function seleccionarPestana(nombre) {
  for (const pestana of document.querySelectorAll("[data-pestana]")) {
    const activa = pestana.dataset.pestana === nombre;
    pestana.classList.toggle("activa", activa);
    pestana.setAttribute("aria-selected", String(activa));
  }
  for (const panel of document.querySelectorAll("[data-panel]")) {
    panel.hidden = panel.dataset.panel !== nombre;
  }
}

function fila(...hijos) {
  const item = el("li", "fila");
  item.append(...hijos);
  return item;
}

function textoFila(titulo, detalle) {
  const caja = el("div", "fila-texto");
  caja.append(el("strong", "", titulo), el("small", "", detalle));
  return caja;
}

export function mostrarGrupo(detalle, idActual) {
  mostrar("grupo");
  if (grupoMostrado !== detalle.id) seleccionarPestana("gastos"); // al cambiar de grupo
  grupoMostrado = detalle.id;

  const porId = new Map(detalle.miembros.map((m) => [m.id, m]));
  const quien = (id) => (id === idActual ? "Tú" : porId.has(id) ? nombreCorto(porId.get(id)) : "Alguien");

  $("grupo-titulo").textContent = detalle.nombre;
  const chips = $("grupo-chips");
  chips.replaceChildren();
  for (const miembro of detalle.miembros) {
    const chip = el("span", "chip");
    chip.append(avatar(miembro, "pequeno"), el("span", "", quien(miembro.id)));
    chip.title = miembro.email;
    chips.appendChild(chip);
  }

  // resumen
  const miSaldo = detalle.saldos.find((s) => s.usuario_id === idActual)?.saldo ?? 0;
  const balance = $("resumen-balance");
  balance.textContent = euros(Math.abs(miSaldo));
  balance.className = `dato-valor ${miSaldo > 0 ? "positivo" : miSaldo < 0 ? "negativo" : ""}`.trim();
  $("resumen-balance-texto").textContent =
    miSaldo > 0 ? "Te deben" : miSaldo < 0 ? "Debes" : "Estás al día";
  $("resumen-total").textContent = euros(detalle.gastos.reduce((t, g) => t + g.importe, 0));
  $("resumen-gastos-n").textContent =
    detalle.gastos.length === 1 ? "1 gasto" : `${detalle.gastos.length} gastos`;

  // gastos
  const gastos = $("lista-gastos");
  gastos.replaceChildren();
  for (const gasto of detalle.gastos) {
    const pagador = porId.get(gasto.pagador_id) ?? { id: gasto.pagador_id, email: "?" };
    const entre = gasto.participantes.length === 1 ? "1 persona" : `${gasto.participantes.length} personas`;
    const conPartes = Object.keys(gasto.pesos ?? {}).length > 0 ? " (por partes)" : "";
    const item = fila(
      avatar(pagador),
      textoFila(gasto.concepto, `Pagó ${quien(gasto.pagador_id)} · entre ${entre}${conPartes} · ${fechaCorta(gasto.fecha)}`),
      el("span", "fila-importe", euros(gasto.importe)),
    );
    if (gasto.creado_por === idActual || detalle.creador_id === idActual) {
      const borrar = el("button", "icono", "Borrar");
      borrar.type = "button";
      borrar.dataset.accion = "borrar-gasto";
      borrar.dataset.id = String(gasto.id);
      borrar.title = "Eliminar este gasto";
      item.appendChild(borrar);
    }
    gastos.appendChild(item);
  }
  $("vacio-gastos").hidden = detalle.gastos.length > 0;

  // saldos
  const saldos = $("lista-saldos");
  saldos.replaceChildren();
  for (const { usuario_id: id, saldo } of detalle.saldos) {
    const miembro = porId.get(id) ?? { id, email: "?" };
    const texto = saldo > 0 ? `+${euros(saldo)}` : saldo < 0 ? `−${euros(-saldo)}` : euros(0);
    saldos.appendChild(fila(
      avatar(miembro),
      textoFila(quien(id), saldo > 0 ? "Le deben" : saldo < 0 ? "Debe" : "Al día"),
      el("span", `fila-importe ${saldo > 0 ? "positivo" : saldo < 0 ? "negativo" : ""}`.trim(), texto),
    ));
  }

  const transferencias = $("lista-transferencias");
  transferencias.replaceChildren();
  for (const t of detalle.transferencias) {
    const item = fila(
      textoFila(`${quien(t.de_id)} paga a ${quien(t.a_id)}`, "Pago sugerido para saldar"),
      el("span", "fila-importe", euros(t.importe)),
    );
    if (t.a_id === idActual) {
      const recordar = el("button", "accion", "Recordar");
      recordar.type = "button";
      recordar.dataset.accion = "recordar";
      recordar.dataset.de = String(t.de_id);
      recordar.title = "Enviarle un correo con un recordatorio";
      item.appendChild(recordar);
    }
    if (t.de_id === idActual || t.a_id === idActual) {
      const hecho = el("button", "accion", "Marcar como pagado");
      hecho.type = "button";
      hecho.dataset.accion = "pagar";
      hecho.dataset.de = String(t.de_id);
      hecho.dataset.a = String(t.a_id);
      hecho.dataset.importe = String(t.importe);
      item.appendChild(hecho);
    }
    transferencias.appendChild(item);
  }
  $("vacio-transferencias").hidden = detalle.transferencias.length > 0;

  const pagos = $("lista-liquidaciones");
  pagos.replaceChildren();
  for (const pago of detalle.liquidaciones) {
    pagos.appendChild(fila(
      textoFila(`${quien(pago.de_id)} pagó a ${quien(pago.a_id)}`, fechaCorta(pago.fecha)),
      el("span", "fila-importe", euros(pago.importe)),
    ));
  }
  $("vacio-liquidaciones").hidden = detalle.liquidaciones.length > 0;

  // miembros
  const miembros = $("lista-miembros");
  miembros.replaceChildren();
  for (const miembro of detalle.miembros) {
    miembros.appendChild(fila(
      avatar(miembro),
      textoFila(quien(miembro.id), miembro.email),
      ...(miembro.id === detalle.creador_id ? [el("span", "insignia", "creador")] : []),
    ));
  }
  $("miembro-email").value = "";

  // invitaciones pendientes
  const invitaciones = $("lista-invitaciones");
  invitaciones.replaceChildren();
  for (const inv of detalle.invitaciones ?? []) {
    invitaciones.appendChild(fila(
      textoFila(inv.email, `Invitado por ${quien(inv.invitado_por)} · caduca el ${fechaCorta(inv.expira_en)}`),
      el("span", "insignia pendiente", "pendiente"),
    ));
  }
  $("bloque-invitaciones").hidden = (detalle.invitaciones ?? []).length === 0;

  // línea de actividad
  const actividad = $("lista-actividad");
  actividad.replaceChildren();
  for (const entrada of detalle.actividad ?? []) {
    const [icono, texto] = describirActividad(entrada, quien);
    const item = el("li", "fila actividad");
    item.append(el("span", "punto", icono), textoFila(texto, fechaYHora(entrada.fecha)));
    actividad.appendChild(item);
  }
  $("vacio-actividad").hidden = (detalle.actividad ?? []).length > 0;
}

// Convierte una entrada del historial en un icono y una frase. Un tipo desconocido
// (por ejemplo de una versión más nueva) se muestra con un texto neutro.
function describirActividad(entrada, quien) {
  const d = entrada.datos ?? {};
  const autor = quien(entrada.usuario_id);
  switch (entrada.tipo) {
    case "grupo_creado": return ["★", `${autor} creó el grupo`];
    case "miembro_anadido": return ["+", `${autor} añadió a ${quien(d.miembro_id)}`];
    case "invitacion_enviada": return ["✉", `${autor} invitó a ${d.email}`];
    case "invitacion_aceptada": return ["✓", `${autor} se unió al grupo`];
    case "gasto_creado": return ["€", `${autor} añadió «${d.concepto}» (${euros(d.importe)})`];
    case "gasto_eliminado": return ["×", `${autor} eliminó «${d.concepto}» (${euros(d.importe)})`];
    case "pago_registrado": return ["↔", `${quien(d.de_id)} pagó ${euros(d.importe)} a ${quien(d.a_id)}`];
    case "recordatorio_enviado": return ["!", `${autor} recordó a ${quien(d.deudor_id)} su pago de ${euros(d.importe)}`];
    default: return ["·", `${autor} hizo un cambio`];
  }
}

// ---------- ventana de nuevo gasto ----------
export function abrirDialogoGasto(miembros, idActual) {
  $("gasto-concepto").value = "";
  $("gasto-importe").value = "";
  mostrarMensaje("gasto", "");

  const pagador = $("gasto-pagador");
  pagador.replaceChildren();
  for (const miembro of miembros) {
    const opcion = el("option", "", miembro.id === idActual ? "Tú" : nombreCorto(miembro));
    opcion.value = String(miembro.id);
    opcion.selected = miembro.id === idActual;
    pagador.appendChild(opcion);
  }

  const participantes = $("gasto-participantes");
  participantes.replaceChildren();
  for (const miembro of miembros) {
    const fila = el("div", "participante");
    const etiqueta = el("label", "participante-etiqueta");
    const casilla = el("input");
    casilla.type = "checkbox";
    casilla.value = String(miembro.id);
    casilla.checked = true;
    etiqueta.append(casilla, avatar(miembro, "pequeno"),
      el("span", "", miembro.id === idActual ? "Tú" : nombreCorto(miembro)));
    const partes = el("input", "peso");
    partes.type = "number";
    partes.min = "1";
    partes.max = "10";
    partes.step = "1";
    partes.value = "1";
    partes.setAttribute("aria-label", `Partes de ${nombreCorto(miembro)}`);
    fila.append(etiqueta, partes, el("span", "partes", "partes"));
    participantes.appendChild(fila);
  }
  $("dialogo-gasto").showModal();
  $("gasto-concepto").focus();
}

export function cerrarDialogoGasto() {
  $("dialogo-gasto").close();
}

// ---------- administración ----------
function crearBoton(texto, accion, usuario) {
  const boton = el("button", "", texto);
  boton.type = "button";
  boton.dataset.accion = accion;
  boton.dataset.id = String(usuario.id);
  boton.dataset.email = usuario.email;
  return boton;
}

export function mostrarUsuarios(usuarios, idActual) {
  const cuerpo = $("tabla-usuarios-cuerpo");
  cuerpo.replaceChildren();
  for (const usuario of usuarios) {
    const fila = el("tr");
    for (const texto of [usuario.email, usuario.rol, usuario.estado]) {
      fila.appendChild(el("td", "", texto));
    }
    const acciones = el("td");
    acciones.appendChild(crearBoton("¿Activo?", "activo", usuario));

    const eliminar = crearBoton("Eliminar", "eliminar", usuario);
    const esYo = usuario.id === idActual;
    if (usuario.estado === "eliminado" || esYo) {
      eliminar.disabled = true;
      eliminar.dataset.bloqueado = "si";
    }
    if (esYo) eliminar.title = "Para borrar tu cuenta usa «Eliminar mi cuenta»";
    acciones.appendChild(eliminar);

    fila.appendChild(acciones);
    cuerpo.appendChild(fila);
  }
}

// ---------- eventos ----------
export function enlazar(controlador) {
  const {
    alIniciarSesion, alRegistrar, alCerrarSesion, alReenviarConfirmacion, alNavegar,
    alCrearGrupo, alAbrirGrupo, alAnadirMiembro, alNuevoGasto, alGuardarGasto,
    alEliminarGasto, alMarcarPagado, alRecordar, alComprobarActivo, alEliminarUsuario,
    alEliminarMiCuenta,
  } = controlador;

  const alEnviar = (idFormulario, accion) =>
    $(idFormulario).addEventListener("submit", (evento) => {
      evento.preventDefault();
      accion();
    });

  alEnviar("form-login", () => alIniciarSesion($("login-email").value, $("login-password").value));
  alEnviar("form-registro", () => alRegistrar($("registro-email").value, $("registro-password").value));
  alEnviar("form-grupo", () => alCrearGrupo($("grupo-nombre").value));
  alEnviar("form-miembro", () => alAnadirMiembro($("miembro-email").value));
  alEnviar("form-gasto", () => {
    const participantes = [];
    const pesos = {};
    for (const fila of document.querySelectorAll("#gasto-participantes .participante")) {
      const casilla = fila.querySelector("input[type=checkbox]");
      if (!casilla.checked) continue;
      const id = Number(casilla.value);
      participantes.push(id);
      pesos[id] = Number(fila.querySelector(".peso").value);
    }
    alGuardarGasto({
      concepto: $("gasto-concepto").value,
      importe: $("gasto-importe").value,
      pagadorId: Number($("gasto-pagador").value),
      participantes,
      pesos,
    });
  });

  // navegación
  for (const boton of document.querySelectorAll("[data-nav]")) {
    boton.addEventListener("click", () => alNavegar(boton.dataset.nav));
  }
  $("ir-inicio").addEventListener("click", (evento) => {
    evento.preventDefault();
    alNavegar("grupos");
  });
  $("volver-grupos").addEventListener("click", () => alNavegar("grupos"));
  for (const pestana of document.querySelectorAll("[data-pestana]")) {
    pestana.addEventListener("click", () => seleccionarPestana(pestana.dataset.pestana));
  }

  // listas: un solo escuchador por lista
  $("lista-grupos").addEventListener("click", (evento) => {
    const boton = evento.target.closest("button[data-grupo-id]");
    if (boton && !boton.disabled) alAbrirGrupo(Number(boton.dataset.grupoId));
  });
  $("lista-gastos").addEventListener("click", (evento) => {
    const boton = evento.target.closest("button[data-accion='borrar-gasto']");
    if (boton && !boton.disabled) alEliminarGasto(Number(boton.dataset.id));
  });
  $("lista-transferencias").addEventListener("click", (evento) => {
    const boton = evento.target.closest("button[data-accion]");
    if (!boton || boton.disabled) return;
    if (boton.dataset.accion === "pagar") {
      alMarcarPagado(Number(boton.dataset.de), Number(boton.dataset.a), Number(boton.dataset.importe));
    } else if (boton.dataset.accion === "recordar") {
      alRecordar(Number(boton.dataset.de));
    }
  });
  $("tabla-usuarios-cuerpo").addEventListener("click", (evento) => {
    const boton = evento.target.closest("button[data-accion]");
    if (!boton || boton.disabled) return;
    const id = Number(boton.dataset.id);
    if (boton.dataset.accion === "activo") alComprobarActivo(id, boton.dataset.email);
    else if (boton.dataset.accion === "eliminar") alEliminarUsuario(id, boton.dataset.email);
  });

  $("boton-nuevo-gasto").addEventListener("click", () => alNuevoGasto());
  $("cancelar-gasto").addEventListener("click", () => cerrarDialogoGasto());
  $("boton-logout").addEventListener("click", () => alCerrarSesion());
  $("boton-eliminar-cuenta").addEventListener("click", () => alEliminarMiCuenta());

  $("reenviar-confirmacion").addEventListener("click", (evento) => {
    evento.preventDefault();
    alReenviarConfirmacion($("login-email").value);
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

// Lee un parámetro de la URL (?error=..., ?confirmar=...) y lo quita de la barra de
// direcciones para que no reaparezca al recargar ni se quede el token a la vista.
function leerYQuitarParametro(nombre) {
  const url = new URL(window.location.href);
  const valor = url.searchParams.get(nombre);
  if (valor !== null) {
    url.searchParams.delete(nombre);
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  }
  return valor;
}

// Código de error con el que el servidor nos devuelve tras un fallo de OAuth, o null.
export const leerErrorDeUrl = () => leerYQuitarParametro("error");

// Token del enlace del correo de confirmación, o null.
export const leerTokenConfirmacion = () => leerYQuitarParametro("confirmar");
