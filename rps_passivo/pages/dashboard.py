"""Página Menu Inicial (antes 'Dashboard') — itens 3 e 11 da lista de melhorias.

ALTERADO:
- Título da página: "Dashboard" -> "Menu Inicial" (item 3).
- Nova seção `_menu_botoes()`: um botão grande para cada página do app (item 3).
- Gráfico de gasto por loja (`_grafico_lojas`) ficou mais largo, com rótulos
  das lojas legíveis (rotação/margem ajustadas), e os gráficos + atividade
  recente agora ficam EMPILHADOS verticalmente em coluna única, não mais
  lado a lado (item 11).
- Função ainda se chama `dashboard_page` para não quebrar os imports em
  rps_passivo.py — só o conteúdo/rota interna muda de nome visualmente.

Observação: os cards de loja completos (item 4, 10, 14, 15) serão feitos
no Bloco 3 — aqui a seção `_resumo_lojas` é mantida como está por enquanto.
"""
import reflex as rx

from ..state import DashboardState
from ..components.navbar import page_shell
from ..components.cards import kpi_card, card_container
from ..components.var_utils import vstr
from ..components.store_dashboard_card import store_dashboard_card, modal_edicao_limites
from ..theme import TEXT_MUTED

VERMELHO = "#E31E24"
VERDE = "#00A651"
LARANJA = "#FF8C00"

# Botões grandes de navegação (item 3) — mesmas páginas da navbar,
# com ícone e descrição curta.
MENU_BOTOES = [
    ("Menu Inicial", "/dashboard", "layout-dashboard", "Visão geral e indicadores"),
    ("Lançamentos", "/lancamentos", "square-plus", "Lançar boletos e contas fixas"),
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
            rx.icon(icone, size=28, color=VERMELHO),
            rx.text(nome, size="3", weight="bold"),
            rx.text(desc, size="1", color=TEXT_MUTED, text_align="center"),
            spacing="2",
            align="center",
            justify="center",
            padding="1.4em 1em",
            border_radius="14px",
            style={"background": "white"},
            box_shadow="0 1px 6px rgba(0,0,0,0.06)",
            _hover={"box_shadow": "0 4px 14px rgba(0,0,0,0.10)", "transform": "translateY(-2px)"},
            transition="all 0.15s ease",
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
        border_bottom="1px solid #F1F5F9",
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
    """Cards de loja no Menu Inicial com os itens 4, 10, 14, 15 implementados."""
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
    # Convert logo_b64 to string para evitar problemas com Var no compile time
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
    # ALTERADO (item 11): gráfico mais largo/alto, rótulos das lojas com
    # margem inferior maior e rotação para não cortar/sobrepor nomes.
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
            # 2) Acesso rápido — botões grandes para cada página (item 3)
            _menu_botoes(),
            # 3) Alertas
            _alerta_vencimentos(),
            # 4) Cards de resumo por loja (será substituído no Bloco 3)
            _resumo_lojas(),
            # 5) Modal de edição de limites (Item 15)
            modal_edicao_limites(),
            # 6) Gráficos e atividade — AGORA EMPILHADOS EM COLUNA ÚNICA (item 11)
            _grafico_lojas(),
            _grafico_tipos(),
            _painel_atividade(),
            spacing="3",
            width="100%",
        ),
    )