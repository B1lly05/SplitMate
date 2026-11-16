"""Grupos de gasto compartido: reglas de negocio. Todos los permisos se comprueban aquí,
en el servidor: ser miembro del grupo es lo que da acceso a verlo y a tocarlo."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from back.logica.errores import (
    DatosInvalidos, GrupoNoEncontrado, NoAutorizado, UsuarioNoEncontrado, YaEsMiembro,
)
from back.logica.modelos import Estado, Gasto, Grupo, Liquidacion, Usuario
from back.logica.repositorio_grupos import RepositorioGrupos
from back.logica.saldos import calcular_saldos, simplificar
from back.logica.servicio import ServicioUsuarios

log = logging.getLogger("splitmate.grupos")

MAX_NOMBRE = 60
MAX_CONCEPTO = 80
MAX_IMPORTE = 100_000_000      # 1.000.000 € en céntimos
MAX_MIEMBROS = 30
MAX_GRUPOS_POR_USUARIO = 50
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


class ServicioGrupos:
    def __init__(self, grupos: RepositorioGrupos, usuarios: ServicioUsuarios,
                 reloj: Callable[[], datetime] = _ahora):
        self.grupos = grupos
        self.usuarios = usuarios
        self.reloj = reloj

    # --- acceso ---------------------------------------------------------------
    def _grupo_de_miembro(self, usuario: Usuario, grupo_id: int) -> Grupo:
        grupo = self.grupos.obtener_grupo(grupo_id)
        # Mismo error si no existe o si no eres miembro: no se revela qué grupos hay
        if grupo is None or usuario.id not in grupo.miembros:
            raise GrupoNoEncontrado(MENSAJE_NO_ENCONTRADO)
        return grupo

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
        log.info("Grupo creado id=%s por usuario id=%s", grupo.id, usuario.id)
        return grupo

    def listar_grupos(self, usuario: Usuario) -> list[Grupo]:
        return self.grupos.listar_grupos_de(usuario.id)

    def anadir_miembro(self, usuario: Usuario, grupo_id: int, email: str) -> Grupo:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        nuevo = self.usuarios.repositorio.obtener_por_email((email or "").strip().lower())
        if nuevo is None or nuevo.estado != Estado.ACTIVO:
            raise UsuarioNoEncontrado("No hay ningún usuario activo con ese email")
        if nuevo.id in grupo.miembros:
            raise YaEsMiembro("Esa persona ya está en el grupo")
        if len(grupo.miembros) >= MAX_MIEMBROS:
            raise DatosInvalidos(f"Un grupo no puede tener más de {MAX_MIEMBROS} miembros")
        self.grupos.anadir_miembro(grupo.id, nuevo.id)
        log.info("Miembro id=%s añadido al grupo id=%s", nuevo.id, grupo.id)
        return self.grupos.obtener_grupo(grupo.id)

    # --- gastos ---------------------------------------------------------------
    def registrar_gasto(self, usuario: Usuario, grupo_id: int, concepto: str, importe: int,
                        pagador_id: int, participantes: list[int]) -> Gasto:
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
        gasto = self.grupos.crear_gasto(grupo.id, concepto, importe, pagador_id,
                                        sorted(participantes), usuario.id,
                                        self.reloj().isoformat())
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
        log.info("Pago registrado id=%s en el grupo id=%s", pago.id, grupo.id)
        return pago

    # --- vista del grupo ------------------------------------------------------
    def detalle(self, usuario: Usuario, grupo_id: int) -> DetalleGrupo:
        grupo = self._grupo_de_miembro(usuario, grupo_id)
        miembros = [u for u in (self.usuarios.repositorio.obtener_por_id(i)
                                for i in grupo.miembros) if u is not None]
        gastos = sorted(self.grupos.listar_gastos(grupo.id), key=lambda g: g.id, reverse=True)
        liquidaciones = sorted(self.grupos.listar_liquidaciones(grupo.id),
                               key=lambda p: p.id, reverse=True)
        saldos = calcular_saldos(gastos, liquidaciones)
        for uid in grupo.miembros:
            saldos.setdefault(uid, 0)
        return DetalleGrupo(grupo, miembros, gastos, liquidaciones, saldos, simplificar(saldos))
