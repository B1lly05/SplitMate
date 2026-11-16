from typing import Optional

from back.logica.modelos import Gasto, Grupo, Liquidacion
from back.logica.repositorio_grupos import RepositorioGrupos


class RepositorioGruposMemoria(RepositorioGrupos):
    def __init__(self):
        self._grupos: dict[int, Grupo] = {}
        self._gastos: dict[int, Gasto] = {}
        self._liquidaciones: dict[int, Liquidacion] = {}
        self._ids = {"grupos": 0, "gastos": 0, "liquidaciones": 0}

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
                    creado_por, fecha):
        gasto = Gasto(self._siguiente("gastos"), grupo_id, concepto, importe, pagador_id,
                      list(participantes), creado_por, fecha)
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
