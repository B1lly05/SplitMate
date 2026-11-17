from typing import Optional

from back.logica.modelos import Actividad, Gasto, Grupo, Invitacion, Liquidacion
from back.logica.repositorio_grupos import RepositorioGrupos


class RepositorioGruposMemoria(RepositorioGrupos):
    def __init__(self):
        self._grupos: dict[int, Grupo] = {}
        self._gastos: dict[int, Gasto] = {}
        self._liquidaciones: dict[int, Liquidacion] = {}
        self._actividad: list[Actividad] = []
        self._invitaciones: dict[int, Invitacion] = {}
        self._ids = {"grupos": 0, "gastos": 0, "liquidaciones": 0, "actividad": 0,
                     "invitaciones": 0}

    def _siguiente(self, tipo: str) -> int:
        self._ids[tipo] += 1
        return self._ids[tipo]

    def crear_grupo(self, nombre, creador_id):
        grupo = Grupo(self._siguiente("grupos"), nombre, creador_id, [creador_id])
        self._grupos[grupo.id] = grupo
        return grupo

    def obtener_grupo(self, id) -> Optional[Grupo]:
        return self._grupos.get(id)

    def listar_grupos_de(self, usuario_id):
        return [g for g in self._grupos.values() if usuario_id in g.miembros]

    def anadir_miembro(self, grupo_id, usuario_id):
        grupo = self._grupos[grupo_id]
        if usuario_id not in grupo.miembros:
            grupo.miembros.append(usuario_id)

    def crear_gasto(self, grupo_id, concepto, importe, pagador_id, participantes,
                    creado_por, fecha, pesos=None):
        gasto = Gasto(self._siguiente("gastos"), grupo_id, concepto, importe, pagador_id,
                      list(participantes), creado_por, fecha, dict(pesos or {}))
        self._gastos[gasto.id] = gasto
        return gasto

    def obtener_gasto(self, id) -> Optional[Gasto]:
        return self._gastos.get(id)

    def listar_gastos(self, grupo_id):
        return [g for g in self._gastos.values() if g.grupo_id == grupo_id]

    def eliminar_gasto(self, id):
        self._gastos.pop(id, None)

    def crear_liquidacion(self, grupo_id, de_id, a_id, importe, fecha):
        pago = Liquidacion(self._siguiente("liquidaciones"), grupo_id, de_id, a_id,
                           importe, fecha)
        self._liquidaciones[pago.id] = pago
        return pago

    def listar_liquidaciones(self, grupo_id):
        return [p for p in self._liquidaciones.values() if p.grupo_id == grupo_id]

    def registrar_actividad(self, grupo_id, usuario_id, tipo, datos, fecha):
        entrada = Actividad(self._siguiente("actividad"), grupo_id, usuario_id, tipo,
                            dict(datos), fecha)
        self._actividad.append(entrada)
        return entrada

    def listar_actividad(self, grupo_id, limite):
        propias = [a for a in self._actividad if a.grupo_id == grupo_id]
        return list(reversed(propias))[:limite]

    def crear_invitacion(self, grupo_id, email, invitado_por, creada_en, expira_en):
        inv = Invitacion(self._siguiente("invitaciones"), grupo_id, email, invitado_por,
                         creada_en, expira_en)
        self._invitaciones[inv.id] = inv
        return inv

    def listar_invitaciones_de_grupo(self, grupo_id):
        return [i for i in self._invitaciones.values() if i.grupo_id == grupo_id]

    def listar_invitaciones_para(self, email):
        return [i for i in self._invitaciones.values() if i.email == email]

    def eliminar_invitacion(self, id):
        self._invitaciones.pop(id, None)
