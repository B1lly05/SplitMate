from typing import Optional

from back.logica.modelos import Estado, Rol, Usuario
from back.logica.repositorio import RepositorioUsuarios
from back.logica.errores import EmailDuplicado

class RepositorioMemoria(RepositorioUsuarios):
    def __init__(self):
        self._usuarios: dict[int, Usuario] = {}
        self._siguiente_id = 1

    def crear(self, email: str, rol: Rol, estado: Estado,
              password_hash: Optional[str] = None) -> Usuario:
        if self.obtener_por_email(email):
            raise EmailDuplicado("Ya existe un usuario con ese email")      
        usuario = Usuario(id=self._siguiente_id, email=email, rol=rol,
                          estado=estado, password_hash=password_hash)
        self._usuarios[usuario.id] = usuario
        self._siguiente_id += 1
        return usuario

    def obtener_por_id(self, id: int) -> Optional[Usuario]:
        return self._usuarios.get(id)

    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        return next((u for u in self._usuarios.values() if u.email == email), None)

    def listar(self) -> list[Usuario]:
        return list(self._usuarios.values())

    def actualizar(self, usuario: Usuario) -> None:
        self._usuarios[usuario.id] = usuario