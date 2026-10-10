from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hashear(password: str) -> str:
    """Devuelve el hash argon2 de la contraseña (nunca se guarda en texto plano)."""
    return _hasher.hash(password)


def verificar(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False