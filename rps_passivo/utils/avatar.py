"""Gerador de avatar fallback (iniciais + cor) para lojas sem logo."""
import hashlib

PALETA = [
    "#E31E24", "#00A651", "#1A1A2E", "#FF8C00",
    "#6C757D", "#0077B6", "#9D4EDD", "#2A9D8F",
]


def cor_por_nome(nome: str) -> str:
    """Gera uma cor estável (hash do nome) dentro da paleta Cumani-friendly."""
    h = int(hashlib.md5(nome.encode("utf-8")).hexdigest(), 16)
    return PALETA[h % len(PALETA)]


def iniciais(nome: str) -> str:
    partes = [p for p in nome.strip().split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()
