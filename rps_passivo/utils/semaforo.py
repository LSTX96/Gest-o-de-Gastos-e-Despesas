"""Lógica do Semáforo de Vencimento.

Regras:
    > 5 dias        -> verde   (tranquilo)
    3 a 5 dias      -> amarelo (atenção)
    1 a 2 dias      -> laranja (urgente)
    0 ou vencido    -> vermelho (vencido / vence hoje)
"""
from datetime import date, datetime
from typing import Union

COR_VERDE = "#00A651"
COR_AMARELO = "#FFC107"
COR_LARANJA = "#FF8C00"
COR_VERMELHO = "#E31E24"

DateLike = Union[date, datetime, str, None]


def _to_date(value: DateLike) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def dias_restantes(vencimento: DateLike, hoje: DateLike = None) -> int | None:
    d = _to_date(vencimento)
    if d is None:
        return None
    base = _to_date(hoje) or date.today()
    return (d - base).days


def cor_semaforo(vencimento: DateLike, hoje: DateLike = None) -> str:
    dias = dias_restantes(vencimento, hoje)
    if dias is None:
        return COR_VERDE
    if dias <= 0:
        return COR_VERMELHO
    if dias <= 2:
        return COR_LARANJA
    if dias <= 5:
        return COR_AMARELO
    return COR_VERDE


def status_semaforo(vencimento: DateLike, hoje: DateLike = None) -> str:
    dias = dias_restantes(vencimento, hoje)
    if dias is None:
        return "sem data"
    if dias < 0:
        return f"Venceu há {abs(dias)} dia(s)"
    if dias == 0:
        return "Vence hoje"
    return f"Faltam {dias} dia(s)"


def nivel_semaforo(vencimento: DateLike, hoje: DateLike = None) -> str:
    """Retorna verde|amarelo|laranja|vermelho — útil para ordenação/filtros."""
    cor = cor_semaforo(vencimento, hoje)
    return {
        COR_VERDE: "verde",
        COR_AMARELO: "amarelo",
        COR_LARANJA: "laranja",
        COR_VERMELHO: "vermelho",
    }[cor]
