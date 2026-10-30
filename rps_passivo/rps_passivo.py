"""Gestão de Custos e Despesas Cumani — Entry point da aplicação Reflex.

ALTERADO (item 1): título do app atualizado para "Gestão de Custos e
Despesas Cumani" em todas as páginas — isso define o texto exibido na
aba do navegador (metadado <title>) para cada rota. O nome interno do
pacote Reflex (rps_passivo, em rxconfig.py) NÃO precisa mudar — é só um
identificador técnico, não aparece para o usuário.
O título "de cabeçalho" (dentro da página) já vem da navbar (`APP_TITLE`
em components/navbar.py).
"""
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
from .pages.loja_detalhe import loja_detalhe_page, LojaDetalheState
from .pages.relatorio_semanal import relatorio_semanal_page
from .pages.relatorio_mensal import relatorio_mensal_page
from .pages.usuarios import usuarios_page

APP_TITLE = "Gestão de Custos e Despesas Cumani"


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

app.add_page(index, route="/", on_load=AppState.route_index, title=APP_TITLE)
app.add_page(login_page, route="/login", title=f"Login — {APP_TITLE}")
app.add_page(
    dashboard_page, route="/dashboard",
    on_load=[AppState.check_auth, DashboardState.carregar],
    title=f"Menu Inicial — {APP_TITLE}",
)
app.add_page(
    lancamentos_page, route="/lancamentos",
    on_load=[AppState.check_auth, LancamentosState.carregar],
    title=f"Lançamentos — {APP_TITLE}",
)
app.add_page(
    contas_pagar_page, route="/contas-pagar",
    on_load=[AppState.check_auth, ContasPagarState.carregar],
    title=f"Contas a Pagar — {APP_TITLE}",
)
app.add_page(
    contas_fixas_page, route="/contas-fixas",
    on_load=[AppState.check_auth, ContasFixasState.carregar],
    title=f"Contas Fixas — {APP_TITLE}",
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
    relatorio_semanal_page, route="/relatorio-semanal",
    on_load=[AppState.check_auth, RelatorioSemanalState.carregar],
    title=f"Relatório Semanal — {APP_TITLE}",
)
app.add_page(
    relatorio_mensal_page, route="/relatorio-mensal",
    on_load=[AppState.check_auth, RelatorioMensalState.carregar],
    title=f"Relatório Mensal — {APP_TITLE}",
)
app.add_page(
    usuarios_page, route="/usuarios",
    on_load=[AppState.check_auth, UsuariosState.carregar],
    title=f"Usuários — {APP_TITLE}",
)