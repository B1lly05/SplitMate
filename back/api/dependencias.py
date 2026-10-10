from fastapi import Depends, Header

from back.datos.memoria import RepositorioMemoria
from back.logica.modelos import Usuario
from back.logica.servicio import ServicioUsuarios

# Aquí se montan las piezas. En el Hito 3 se cambiará RepositorioMemoria
# por el de base de datos sin tocar la lógica.
_servicio = ServicioUsuarios(RepositorioMemoria())


def get_servicio() -> ServicioUsuarios:
    return _servicio


def solicitante_actual(
    x_usuario_id: int | None = Header(default=None),
    servicio: ServicioUsuarios = Depends(get_servicio),
) -> Usuario:
    # PROVISIONAL: se sustituirá por la sesión real (Hito 2)
    return servicio.identificar(x_usuario_id)