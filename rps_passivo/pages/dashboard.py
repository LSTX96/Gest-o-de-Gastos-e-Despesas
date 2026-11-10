"""Página Menu Inicial.

- KPIs no topo, Acesso Rápido, alertas, cards por loja, gráficos e atividade.
- Cores seguem o tema (claro ou escuro) através das variáveis do theme.py.
- Função continua se chamando `dashboard_page` para não quebrar os imports.
"""
import reflex as rx

from ..state import DashboardState
from ..components.navbar import page_shell
from ..components.cards import kpi_card, card_container
from ..components.var_utils import vstr
from ..components.store_dashboard_card import store_dashboard_card, modal_edicao_limites
from ..theme import TEXT_MUTED, TEXT_TITLE, BORDER, CARD_BG_2, PRIMARY

VERMELHO = "#E31E24"
VERDE = "#00A651"
LARANJA = "#FF8C00"

# Botões grandes de navegação: mesmas páginas da navbar, com ícone e descrição curta.
MENU_BOTOES = [
    ("Menu Inicial", "/dashboard", "layout-dashboard", "Visão geral e indicadores"),
    ("Lançamentos", "/lancamentos", "square-plus", "Lançar despesas e contas fixas"),
    ("Contas a Pagar", "/contas-pagar", "receipt", "Ver e gerenciar contas"),
    ("Contas Fixas", "/contas-fixas", "list-checks", "Cadastro de contas fixas"),
    ("Relatório Semanal", "/relatorio-semanal", "calendar-days", "Acompanhamento por semana"),
    ("Relatório Mensal", "/relatorio-mensal", "calendar-range", "Acompanhamento por mês"),
    ("Lojas", "/lojas", "store", "Gerenciar lojas e limites"),
    ("Usuários", "/usuarios", "users", "Gerenciar acessos"),
]


def _botao_menu(item) -> rx.Component:
    nome, href, icone, desc = item
    return rx.link(
        rx.vstack(
            rx.icon(icone, size=28, color=PRIMARY),
            rx.text(nome, size="3", weight="bold", color=TEXT_TITLE),
            rx.text(desc, size="1", color=TEXT_MUTED, text_align="center"),
            spacing="2",
            align="center",
            justify="center",
            padding="1.4em 1em",
            border_radius="14px",
            bg=CARD_BG_2,
            border=f"1px solid {BORDER}",
            transition="all 0.2s ease",
            _hover={
                "border_color": PRIMARY,
                "box_shadow": "0 0 0 1px rgba(220,38,38,0.35), 0 8px 24px rgba(220,38,38,0.15)",
                "transform": "translateY(-3px)",
            },
            height="100%",
        ),
        href=href,
        underline="none",
        width="100%",
    )


def _menu_botoes() -> rx.Component:
    return card_container(
        rx.heading("Acesso Rápido", size="3", margin_bottom="0.8em"),
        rx.grid(
            *[_botao_menu(item) for item in MENU_BOTOES],
            columns=rx.breakpoints(initial="2", sm="2", md="4"),
            spacing="3",
            width="100%",
        ),
        margin_bottom="1.2em",
    )


def _alerta_vencimentos() -> rx.Component:
    return card_container(
        rx.hstack(
            rx.icon("triangle-alert", color=LARANJA),
            rx.heading("Contas Próximas do Vencimento", size="3"),
            spacing="2",
            align="center",
        ),
        rx.cond(
            DashboardState.contas_a_vencer > 0,
            rx.text(DashboardState.contas_a_vencer.to_string() + " conta(s) vencem nos próximos 5 dias."),
            rx.hstack(
                rx.icon("circle-check", color=VERDE, size=18),
                rx.text("Nenhuma conta próxima do vencimento", color=VERDE),
                spacing="2",
            ),
        ),
        rx.link(
            rx.button("Ver Contas a Pagar", variant="soft", margin_top="0.5em"),
            href="/contas-pagar",
        ),
        margin_bottom="1.2em",
    )


def _linha_atividade(item: dict) -> rx.Component:
    return rx.hstack(
        rx.icon("activity", size=16, color=TEXT_MUTED),
        rx.vstack(
            rx.text(vstr(item["acao"]), size="2", weight="medium"),
            rx.text(vstr(item["usuario"]) + " • " + vstr(item["quando"]), size="1", color=TEXT_MUTED),
            spacing="0",
            align="start",
        ),
        spacing="2",
        align="start",
        width="100%",
        padding_bottom="0.5em",
        border_bottom=f"1px solid {BORDER}",
    )


def _painel_atividade() -> rx.Component:
    return card_container(
        rx.heading("Atividade Recente", size="3", margin_bottom="0.6em"),
        rx.cond(
            DashboardState.atividade_recente.length() == 0,
            rx.text("Nenhuma atividade registrada.", size="2", color=TEXT_MUTED),
            rx.vstack(
                rx.foreach(DashboardState.atividade_recente, _linha_atividade),
                spacing="3",
                width="100%",
            ),
        ),
        margin_bottom="1.2em",
    )


def _resumo_lojas() -> rx.Component:
    """Cards de loja no Menu Inicial."""
    return card_container(
        rx.heading("Lojas — Visão Geral", size="3", margin_bottom="0.8em"),
        rx.grid(
            rx.foreach(DashboardState.lojas_resumo, _store_card),
            columns=rx.breakpoints(initial="1", sm="2", md="3", lg="4"),
            spacing="3",
            width="100%",
        ),
        margin_bottom="1.2em",
    )


def _store_card(item: dict) -> rx.Component:
    """Renderiza o card de uma loja usando o componente store_dashboard_card."""
    logo_b64 = item.get("logo_b64", "")
    return store_dashboard_card(
        loja_id=item["loja_id"],
        loja_name=item["loja"],
        avatar_color=item["cor"],
        logo_b64=logo_b64,
        gasto_acumulado=item["gasto"],
        monthly_limit=item["monthly_limit"],
        cash_limit=item["cash_limit"],
        a_vencer_mes=item["a_vencer_mes"],
        pago_mes=item["pago_mes"],
        falta_pagar=item["falta_pagar"],
        percentual_limite=item["percentual"],
        esta_no_limite=item["no_limite"],
        esta_excedida=item["excedido"],
    )


def _grafico_lojas() -> rx.Component:
    return card_container(
        rx.heading("Gastos por Loja (mês atual)", size="3", margin_bottom="0.5em"),
        rx.plotly(data=DashboardState.figura_lojas, width="100%"),
        margin_bottom="1.2em",
    )


def _grafico_tipos() -> rx.Component:
    return card_container(
        rx.heading("Distribuição por Tipo de Despesa", size="3", margin_bottom="0.5em"),
        rx.plotly(data=DashboardState.figura_tipos, width="100%"),
        margin_bottom="1.2em",
    )


def dashboard_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Menu Inicial", size="6", margin_bottom="0.3em"),
            # 1) KPIs no topo
            rx.grid(
                kpi_card("Total do Mês", DashboardState.total_mes, "wallet", VERMELHO),
                kpi_card("Total Boletos", DashboardState.total_boletos, "receipt", LARANJA),
                kpi_card("Total Fixas", DashboardState.total_fixas, "repeat", VERDE),
                kpi_card("Lojas no Limite", DashboardState.lojas_no_limite.to_string(), "circle-check", VERDE),
                kpi_card("Lojas Excedidas", DashboardState.lojas_excedidas.to_string(), "circle-alert", VERMELHO),
                columns=rx.breakpoints(initial="1", sm="2", md="3", lg="5"),
                spacing="4",
                width="100%",
                margin_bottom="1.2em",
            ),
            # 2) Acesso rápido
            _menu_botoes(),
            # 3) Alertas
            _alerta_vencimentos(),
            # 4) Cards de resumo por loja
            _resumo_lojas(),
            # 5) Modal de edição de limites
            modal_edicao_limites(),
            # 6) Gráficos e atividade
            _grafico_lojas(),
            _grafico_tipos(),
            _painel_atividade(),
            spacing="3",
            width="100%",
        ),
    )