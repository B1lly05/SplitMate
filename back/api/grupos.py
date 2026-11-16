"""Endpoints de grupos, gastos y pagos. La API solo traduce HTTP: las reglas y los
permisos están en la capa de lógica."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from back.api.dependencias import get_grupos, usuario_de_sesion
from back.logica.grupos import DetalleGrupo, ServicioGrupos
from back.logica.modelos import Usuario

router = APIRouter(prefix="/grupos", tags=["grupos"])


class GrupoEntrada(BaseModel):
    nombre: str


class MiembroEntrada(BaseModel):
    email: str


class GastoEntrada(BaseModel):
    concepto: str
    importe: int            # céntimos
    pagador_id: int
    participantes: list[int]


class LiquidacionEntrada(BaseModel):
    de_id: int
    a_id: int
    importe: int            # céntimos


def _detalle_a_json(d: DetalleGrupo) -> dict:
    return {
        "id": d.grupo.id,
        "nombre": d.grupo.nombre,
        "creador_id": d.grupo.creador_id,
        "miembros": [{"id": u.id, "email": u.email} for u in d.miembros],
        "gastos": [
            {"id": g.id, "concepto": g.concepto, "importe": g.importe,
             "pagador_id": g.pagador_id, "participantes": g.participantes,
             "creado_por": g.creado_por, "fecha": g.fecha}
            for g in d.gastos
        ],
        "liquidaciones": [
            {"id": p.id, "de_id": p.de_id, "a_id": p.a_id, "importe": p.importe,
             "fecha": p.fecha}
            for p in d.liquidaciones
        ],
        "saldos": [{"usuario_id": uid, "saldo": s} for uid, s in sorted(d.saldos.items())],
        "transferencias": [{"de_id": de, "a_id": a, "importe": i}
                           for de, a, i in d.transferencias],
    }


def _resumen(grupo) -> dict:
    return {"id": grupo.id, "nombre": grupo.nombre, "miembros": len(grupo.miembros)}


@router.post("", status_code=201)
def crear(datos: GrupoEntrada, usuario: Usuario = Depends(usuario_de_sesion),
          servicio: ServicioGrupos = Depends(get_grupos)):
    return _resumen(servicio.crear_grupo(usuario, datos.nombre))


@router.get("")
def listar(usuario: Usuario = Depends(usuario_de_sesion),
           servicio: ServicioGrupos = Depends(get_grupos)):
    return [_resumen(g) for g in servicio.listar_grupos(usuario)]


@router.get("/{grupo_id}")
def detalle(grupo_id: int, usuario: Usuario = Depends(usuario_de_sesion),
            servicio: ServicioGrupos = Depends(get_grupos)):
    return _detalle_a_json(servicio.detalle(usuario, grupo_id))


@router.post("/{grupo_id}/miembros", status_code=201)
def anadir_miembro(grupo_id: int, datos: MiembroEntrada,
                   usuario: Usuario = Depends(usuario_de_sesion),
                   servicio: ServicioGrupos = Depends(get_grupos)):
    return _resumen(servicio.anadir_miembro(usuario, grupo_id, datos.email))


@router.post("/{grupo_id}/gastos", status_code=201)
def crear_gasto(grupo_id: int, datos: GastoEntrada,
                usuario: Usuario = Depends(usuario_de_sesion),
                servicio: ServicioGrupos = Depends(get_grupos)):
    gasto = servicio.registrar_gasto(usuario, grupo_id, datos.concepto, datos.importe,
                                     datos.pagador_id, datos.participantes)
    return {"id": gasto.id}


@router.delete("/{grupo_id}/gastos/{gasto_id}", status_code=204)
def eliminar_gasto(grupo_id: int, gasto_id: int,
                   usuario: Usuario = Depends(usuario_de_sesion),
                   servicio: ServicioGrupos = Depends(get_grupos)):
    servicio.eliminar_gasto(usuario, grupo_id, gasto_id)
    return Response(status_code=204)


@router.post("/{grupo_id}/liquidaciones", status_code=201)
def crear_liquidacion(grupo_id: int, datos: LiquidacionEntrada,
                      usuario: Usuario = Depends(usuario_de_sesion),
                      servicio: ServicioGrupos = Depends(get_grupos)):
    pago = servicio.registrar_liquidacion(usuario, grupo_id, datos.de_id, datos.a_id,
                                          datos.importe)
    return {"id": pago.id}
