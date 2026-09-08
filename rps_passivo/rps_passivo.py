"""Passivo Cumani — Entry point da aplicação Reflex."""
import reflex as rx

from .state import (
    AppState, DashboardState, LancamentosState, ContasPagarState,
    ContasFixasState, LojasState, RelatorioSemanalState, RelatorioMensalState,
    UsuariosState,
)
from .pages.login import login_page
from .pages.dashboard import dashboard_page
from .pages.lancamentos import lancamentos_page
from .pages.contas_pagar import contas_pagar_page
from .pages.contas_fixas import contas_fixas_page
from .pages.lojas import lojas_page
from .pages.relatorio_semanal import relatorio_semanal_page
from .pages.relatorio_mensal import relatorio_mensal_page
from .pages.usuarios import usuarios_page


def index() -> rx.Component:
    return rx.center(rx.spinner(), height="100vh")


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="red",
        radius="large",
    ),
    style={"font_family": "Inter, sans-serif"},
)

app.add_page(index, route="/", on_load=AppState.route_index)
app.add_page(login_page, route="/login")
app.add_page(dashboard_page, route="/dashboard", on_load=[AppState.check_auth, DashboardState.carregar])
app.add_page(lancamentos_page, route="/lancamentos", on_load=[AppState.check_auth, LancamentosState.carregar])
app.add_page(contas_pagar_page, route="/contas-pagar", on_load=[AppState.check_auth, ContasPagarState.carregar])
app.add_page(contas_fixas_page, route="/contas-fixas", on_load=[AppState.check_auth, ContasFixasState.carregar])
app.add_page(lojas_page, route="/lojas", on_load=[AppState.check_auth, LojasState.carregar])
app.add_page(relatorio_semanal_page, route="/relatorio-semanal", on_load=[AppState.check_auth, RelatorioSemanalState.carregar])
app.add_page(relatorio_mensal_page, route="/relatorio-mensal", on_load=[AppState.check_auth, RelatorioMensalState.carregar])
app.add_page(usuarios_page, route="/usuarios", on_load=[AppState.check_auth, UsuariosState.carregar])
