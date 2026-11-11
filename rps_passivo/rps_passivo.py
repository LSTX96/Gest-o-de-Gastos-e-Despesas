"""Gestão de Custos e Despesas Cumani — Entry point da aplicação Reflex."""
import reflex as rx

from .state import AppState, LojasState, UsuariosState
from .theme import get_theme
from .pages.login import login_page
from .pages.dashboard import dashboard_page
from .pages.inicio_estado import InicioState
from .pages.lancamentos import lancamentos_page, LancamentoState
from .pages.contas import contas_page, ContasState
from .pages.relatorios import relatorios_page, RelatoriosState
from .pages.lojas import lojas_page
from .pages.loja_detalhe import loja_detalhe_page, LojaDetalheState
from .pages.usuarios import usuarios_page

APP_TITLE = "Gestão de Custos e Despesas Cumani"


def index() -> rx.Component:
    return rx.center(rx.spinner(), height="100vh")


def redirecionando() -> rx.Component:
    """Página de passagem para endereços antigos."""
    return rx.center(rx.spinner(), height="100vh")


app = rx.App(
    theme=get_theme(),
    stylesheets=["/cores.css"],
    style={"font_family": "Inter, sans-serif"},
)

app.add_page(index, route="/", on_load=AppState.route_index, title=APP_TITLE)
app.add_page(login_page, route="/login", title=f"Login — {APP_TITLE}")
app.add_page(
    dashboard_page, route="/dashboard",
    on_load=[AppState.check_auth, InicioState.carregar],
    title=f"Menu Inicial — {APP_TITLE}",
)
app.add_page(
    lancamentos_page, route="/lancamentos",
    on_load=[AppState.check_auth, LancamentoState.carregar],
    title=f"Lançamentos — {APP_TITLE}",
)
app.add_page(
    contas_page, route="/contas",
    on_load=[AppState.check_auth, ContasState.abrir],
    title=f"Contas — {APP_TITLE}",
)
app.add_page(
    relatorios_page, route="/relatorios",
    on_load=[AppState.check_auth, RelatoriosState.abrir],
    title=f"Relatórios — {APP_TITLE}",
)
app.add_page(
    lojas_page, route="/lojas",
    on_load=[AppState.check_auth, LojasState.carregar],
    title=f"Lojas — {APP_TITLE}",
)
app.add_page(
    loja_detalhe_page, route="/lojas/[loja_id]",
    on_load=[AppState.check_auth, LojaDetalheState.carregar],
    title=f"Gastos da Loja — {APP_TITLE}",
)
app.add_page(
    usuarios_page, route="/usuarios",
    on_load=[AppState.check_auth, UsuariosState.carregar],
    title=f"Usuários — {APP_TITLE}",
)

# Endereços antigos: continuam funcionando e abrem as páginas novas
for rota_antiga, destino in [
    ("/contas-pagar", "/contas"),
    ("/contas-fixas", "/contas"),
    ("/relatorio-semanal", "/relatorios"),
    ("/relatorio-mensal", "/relatorios"),
]:
    app.add_page(
        redirecionando,
        route=rota_antiga,
        on_load=rx.redirect(destino),
        title=APP_TITLE,
    )