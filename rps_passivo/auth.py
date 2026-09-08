"""Autenticação e controle de acesso por papel (role)."""
import bcrypt

ROLES = ("admin", "operator", "viewer")


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def pode_editar(role: str) -> bool:
    return role in ("admin", "operator")


def pode_lancar(role: str) -> bool:
    return role in ("admin", "operator")


def pode_administrar_usuarios(role: str) -> bool:
    return role == "admin"


def pode_editar_item(role: str, user_id: int, item_created_by: int | None) -> bool:
    """Admin edita tudo. Operador só edita o que ele mesmo criou."""
    if role == "admin":
        return True
    if role == "operator":
        return item_created_by == user_id
    return False
