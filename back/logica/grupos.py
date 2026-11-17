"""Grupos de gasto compartido: reglas de negocio. Todos los permisos se comprueban aquí,
en el servidor: ser miembro del grupo es lo que da acceso a verlo y a tocarlo."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from back.logica.correo import EnviadorCorreo, ErrorEnvio
from back.logica.errores import (
    CorreoNoEnviado, DatosInvalidos, GrupoNoEncontrado, NoAutorizado, UsuarioNoEncontrado,
    YaEsMiembro,
)
from back.logica.modelos import (
    Actividad, Estado, Gasto, Grupo, Invitacion, Liquidacion, Usuario,
)
from back.logica.repositorio_grupos import RepositorioGrupos
from back.logica.saldos import calcular_saldos, simplificar
from back.logica.servicio import PATRON_EMAIL, ServicioUsuarios

log = logging.getLogger("splitmate.grupos")

MAX_NOMBRE = 60
MAX_CONCEPTO = 80
MAX_IMPORTE = 100_000_000      # 1.000.000 € en céntimos
MAX_PESO = 10
MAX_MIEMBROS = 30
MAX_GRUPOS_POR_USUARIO = 50
MAX_INVITACIONES_PENDIENTES = 10   # por grupo: evita usar la app para enviar correo masivo
LIMITE_ACTIVIDAD = 50
DURACION_INVITACION = timedelta(days=14)
ESPERA_RECORDATORIO = timedelta(hours=24)
MENSAJE_NO_ENCONTRADO = "El grupo no existe o no eres miembro"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetalleGrupo:
    grupo: Grupo
    miembros: list[Usuario]
    gastos: list[Gasto]
    liquidaciones: list[Liquidacion]
    saldos: dict[int, int]
    transferencias: list[tuple[int, int, int]]
    actividad: list[Actividad]
    invitaciones: list[Invitacion]


class ServicioGrupos:
    def __init__(self, grupos: RepositorioGrupos, usuarios: ServicioUsuarios,
                 enviador: EnviadorCorreo, base_url: str,
                 reloj: Callable[[], datetime] = _ahora):
        self.grupos = grupos
        self.usuarios = usuarios
        self.enviador = enviador
        self.base_url = base_url.rstrip("/")
        self.reloj = reloj

    # --- utilidades -----------------------------------------------------------
    def _grupo_de_miembro(self, usuario: Usuario, grupo_id: int) -> Grupo:
        grupo = self.grupos.obtener_grupo(grupo_id)
        # Mismo error si no existe o si no eres miembro: no se revela qué grupos hay
        if grupo is None or usuario.id not in grupo.miembros:
            raise GrupoNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return grupo

    def _anotar(self, grupo_id: int, usuario_id: int, tipo: str, **datos) -> None:
        """Añade una línea a la actividad del grupo. Solo ids, importes y conceptos."""
        self.grupos.registrar_actividad(grupo_id, usuario_id, tipo, datos, self.reloj().isoformat())

    def _saldos(self, grupo: Grupo):
        gastos = sorted(self.grupos.listar_gastos(grupo.id), key=lambda g: g.id, reverse=True)
        liquidaciones = sorted(self.grupos.listar_liquidaciones(grupo.id),
                               key=lambda p: p.id, reverse=True)
        saldos = calcular_saldos(gastos, liquidaciones)
        for uid in grupo.miembros:
            saldos.setdefault(uid, 0)
        return gastos, liquidaciones, saldos, simplificar(saldos)

    def _invitaciones_vigentes(self, grupo_id: int) -> list[Invitacion]:
        ahora = self.reloj()
        return [i for i in self.grupos.listar_invitaciones_de_grupo(grupo_id)
                if datetime.fromisoformat(i.expira_en) > ahora]

    # --- grupos ---------------------------------------------------------------
    def crear_grupo(self, usuario: Usuario, nombre: str) -> Grupo:
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInvalidos("El grupo necesita un nombre")
        if len(nombre) > MAX_NOMBRE:
            raise DatosInvalidos(f"El nombre no puede pasar de {MAX_NOMBRE} caracteres")
        if len(self.grupos.listar_grupos_de(usuario.id)) >= MAX_GRUPOS_POR_USUARIO:
            raise DatosInvalidos(f"No puedes estar en más de {MAX_GRUPOS_POR_USUARIO} grupos")
        grupo = self.grupos.crear_grupo(nombre, usuario.id)
        self._anotar(grupo.id, usuario.id, "grupo_creado")
        log.info("Grupo creado id=%s por usuario id=%s", grupo.id, usuario.id)
        return grupo

    def listar_grupos(self, usuario: Usuario) -> list[Grupo]:
        self._aceptar_invitaciones(usuario)
        return self.grupos.listar_grupos_de(usuario.id)

    def _aceptar_invitaciones(self, usuario: Usuario) -> None:
        """Las invitaciones se atan al email: quien entra con una cuenta activa de ese
        email (confirmado por correo, o verificado por GitHub) demuestra que es suyo."""
        ahora = self.reloj()
        for inv in self.grupos.listar_invitaciones_para(usuario.email):
            if datetime.fromisoformat(inv.expira_en) <= ahora:
                self.grupos.eliminar_invitacion(inv.id)
                continue
            grupo = self.grupos.obtener_grupo(inv.grupo_id)
            if (grupo is not None and usuario.id not in grupo.miembros
                    and len(grupo.miembros) < MAX_MIEMBROS):
                self.grupos.anadir_miembro(grupo.id, usuario.id)
                self._anotar(grupo.id, usuario.id, "invitacion_aceptada",
                             invitado_por=inv.invitado_por)
                log.info("Invitación aceptada: usuario id=%s en el grupo id=%s", usuario.id, grupo.id)
            self.grupos.eliminar_invitacion(inv.id)

    def anadir_miembro(self, usuario: Usuario, grupo_id: int, email: str) -> tuple[Grupo, str]:
        """Añade a alguien con cuenta activa, o le invita por correo si no la tiene.
        Devuelve el grupo y 'anadido' o 'invitado'."""
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        email = (email or "").strip().lower()
        if not PATRON_EMAIL.match(email):
            raise DatosInvalidos("El email no tiene un formato válido")
        existente = self.usuarios.repositorio.obtener_por_email(email)
        if existente is not None and existente.estado == Estado.ELIMINADO:
            raise UsuarioNoEncontrado("No se puede añadir a esa persona")

        if existente is not None and existente.estado == Estado.ACTIVO:
            if existente.id in grupo.miembros:
                raise YaEsMiembro("Esa persona ya está en el grupo")
            if len(grupo.miembros) >= MAX_MIEMBROS:
                raise DatosInvalidos(f"Un grupo no puede tener más de {MAX_MIEMBROS} miembros")
            self.grupos.anadir_miembro(grupo.id, existente.id)
            self._anotar(grupo.id, usuario.id, "miembro_anadido", miembro_id=existente.id)
            log.info("Miembro id=%s añadido al grupo id=%s", existente.id, grupo.id)
            return self.grupos.obtener_grupo(grupo.id), "anadido"

        # Sin cuenta (o con la cuenta sin activar todavía): se le invita por correo
        vigentes = self._invitaciones_vigentes(grupo.id)
        if any(i.email == email for i in vigentes):
            raise DatosInvalidos("Ya has invitado a esa persona. Se unirá cuando se registre")
        if len(vigentes) >= MAX_INVITACIONES_PENDIENTES:
            raise DatosInvalidos(
                f"Hay demasiadas invitaciones pendientes (máximo {MAX_INVITACIONES_PENDIENTES})")
        try:
            self.enviador.enviar_invitacion(email, usuario.email, grupo.nombre, self.base_url)
        except ErrorEnvio:
            log.error("No se pudo enviar la invitación del grupo id=%s", grupo.id)
            raise CorreoNoEnviado("No se pudo enviar el correo de invitación. Inténtalo más tarde")
        ahora = self.reloj()
        self.grupos.crear_invitacion(grupo.id, email, usuario.id, ahora.isoformat(),
                                     (ahora + DURACION_INVITACION).isoformat())
        self._anotar(grupo.id, usuario.id, "invitacion_enviada", email=email)
        log.info("Invitación enviada para el grupo id=%s", grupo.id)
        return grupo, "invitado"

    # --- gastos ---------------------------------------------------------------
    def registrar_gasto(self, usuario: Usuario, grupo_id: int, concepto: str, importe: int,
                        pagador_id: int, participantes: list[int],
                        pesos: dict[int, int] | None = None) -> Gasto:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        concepto = (concepto or "").strip()
        if not concepto:
            raise DatosInvalidos("El gasto necesita un concepto")
        if len(concepto) > MAX_CONCEPTO:
            raise DatosInvalidos(f"El concepto no puede pasar de {MAX_CONCEPTO} caracteres")
        if importe <= 0:
            raise DatosInvalidos("El importe debe ser mayor que 0")
        if importe > MAX_IMPORTE:
            raise DatosInvalidos("El importe es demasiado grande")
        if pagador_id not in grupo.miembros:
            raise DatosInvalidos("Quien paga debe ser miembro del grupo")
        if not participantes:
            raise DatosInvalidos("Elige al menos una persona entre quienes se reparte")
        if len(set(participantes)) != len(participantes):
            raise DatosInvalidos("Hay participantes repetidos")
        if any(p not in grupo.miembros for p in participantes):
            raise DatosInvalidos("Todos los participantes deben ser miembros del grupo")
        pesos = pesos or {}
        if any(uid not in participantes for uid in pesos):
            raise DatosInvalidos("Solo pueden tener partes quienes participan en el gasto")
        if any(not 1 <= peso <= MAX_PESO for peso in pesos.values()):
            raise DatosInvalidos(f"Las partes de cada persona deben estar entre 1 y {MAX_PESO}")
        # Solo se guardan los pesos distintos de 1: un gasto sin pesos es un reparto igual
        pesos = {uid: p for uid, p in pesos.items() if p != 1}
        gasto = self.grupos.crear_gasto(grupo.id, concepto, importe, pagador_id,
                                        sorted(participantes), usuario.id,
                                        self.reloj().isoformat(), pesos)
        self._anotar(grupo.id, usuario.id, "gasto_creado", concepto=concepto, importe=importe)
        log.info("Gasto creado id=%s en el grupo id=%s", gasto.id, grupo.id)
        return gasto

    def eliminar_gasto(self, usuario: Usuario, grupo_id: int, gasto_id: int) -> None:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        gasto = self.grupos.obtener_gasto(gasto_id)
        if gasto is None or gasto.grupo_id != grupo.id:
            raise DatosInvalidos("El gasto no existe en este grupo")
        # Solo quien lo registró o quien creó el grupo puede borrarlo
        if usuario.id not in (gasto.creado_por, grupo.creador_id):
            log.warning("Borrado de gasto no permitido id=%s por usuario id=%s", gasto_id, usuario.id)
            raise NoAutorizado("Solo quien registró el gasto o creó el grupo puede eliminarlo")
        self.grupos.eliminar_gasto(gasto.id)
        self._anotar(grupo.id, usuario.id, "gasto_eliminado",
                     concepto=gasto.concepto, importe=gasto.importe)
        log.info("Gasto eliminado id=%s del grupo id=%s", gasto.id, grupo.id)

    # --- pagos entre miembros -------------------------------------------------
    def registrar_liquidacion(self, usuario: Usuario, grupo_id: int, de_id: int, a_id: int,
                              importe: int) -> Liquidacion:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        if de_id == a_id:
            raise DatosInvalidos("Un pago necesita dos personas distintas")
        if de_id not in grupo.miembros or a_id not in grupo.miembros:
            raise DatosInvalidos("Los dos deben ser miembros del grupo")
        if importe <= 0 or importe > MAX_IMPORTE:
            raise DatosInvalidos("El importe del pago no es válido")
        if usuario.id not in (de_id, a_id):
            raise NoAutorizado("Solo quien paga o quien cobra puede registrar el pago")
        pago = self.grupos.crear_liquidacion(grupo.id, de_id, a_id, importe,
                                             self.reloj().isoformat())
        self._anotar(grupo.id, usuario.id, "pago_registrado", de_id=de_id, a_id=a_id,
                     importe=importe)
        log.info("Pago registrado id=%s en el grupo id=%s", pago.id, grupo.id)
        return pago

    # --- recordatorios ----------------------------------------------------------
    def recordar(self, usuario: Usuario, grupo_id: int, deudor_id: int) -> int:
        """Envía por correo un recordatorio a alguien que te debe dinero. Devuelve el
        importe (en céntimos) que se le ha recordado."""
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        if deudor_id not in grupo.miembros:
            raise DatosInvalidos("Esa persona no es miembro del grupo")
        *_, transferencias = self._saldos(grupo)
        importe = sum(i for de, a, i in transferencias if de == deudor_id and a == usuario.id)
        if importe <= 0:
            raise DatosInvalidos("Esa persona no te debe nada ahora mismo")
        deudor = self.usuarios.repositorio.obtener_por_id(deudor_id)
        if deudor is None or deudor.estado != Estado.ACTIVO:
            raise DatosInvalidos("Esa cuenta ya no está disponible")
        # Máximo un recordatorio al día por persona: la propia actividad sirve de registro
        desde = self.reloj() - ESPERA_RECORDATORIO
        for entrada in self.grupos.listar_actividad(grupo.id, 200):
            if (entrada.tipo == "recordatorio_enviado" and entrada.usuario_id == usuario.id
                    and entrada.datos.get("deudor_id") == deudor_id
                    and datetime.fromisoformat(entrada.fecha) > desde):
                raise DatosInvalidos("Ya le has enviado un recordatorio hoy. Espera a mañana")
        try:
            self.enviador.enviar_recordatorio(deudor.email, usuario.email, grupo.nombre,
                                              importe, self.base_url)
        except ErrorEnvio:
            log.error("No se pudo enviar el recordatorio del grupo id=%s", grupo.id)
            raise CorreoNoEnviado("No se pudo enviar el recordatorio. Inténtalo más tarde")
        self._anotar(grupo.id, usuario.id, "recordatorio_enviado", deudor_id=deudor_id,
                     importe=importe)
        log.info("Recordatorio enviado en el grupo id=%s", grupo.id)
        return importe

    # --- vista del grupo ------------------------------------------------------
    def detalle(self, usuario: Usuario, grupo_id: int) -> DetalleGrupo:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        miembros = [u for u in (self.usuarios.repositorio.obtener_por_id(i)
                                for i in grupo.miembros) if u is not None]
        gastos, liquidaciones, saldos, transferencias = self._saldos(grupo)
        return DetalleGrupo(grupo, miembros, gastos, liquidaciones, saldos, transferencias,
                            self.grupos.listar_actividad(grupo.id, LIMITE_ACTIVIDAD),
                            self._invitaciones_vigentes(grupo.id))
