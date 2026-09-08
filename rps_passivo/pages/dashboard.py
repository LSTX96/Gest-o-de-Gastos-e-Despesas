import reflex as rx

from ..state import DashboardState
from ..components.navbar import page_shell
from ..components.cards import kpi_card, card_container
from ..components.var_utils import vstr
from ..theme import TEXT_MUTED

VERMELHO = "#E31E24"
VERDE = "#00A651"
LARANJA = "#FF8C00"


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
        border_bottom=f"1px solid #F1F5F9",
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
    )


def _card_loja_resumo(item: dict) -> rx.Component:
    cor_barra = rx.cond(item["excedido"], VERMELHO, VERDE)
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(width="10px", height="10px", border_radius="50%", style={"background": item["cor"]}),
                rx.text(
                    item["loja"], weight="bold", size="2",
                    cursor="pointer", text_decoration="underline",
                    on_click=lambda: DashboardState.ver_loja(item["loja"]),
                    _hover={"color": VERMELHO},
                ),
                spacing="2",
                align="center",
            ),
            rx.box(
                rx.box(
                    width=vstr(item["largura_barra"]) + "%",
                    height="8px",
                    border_radius="4px",
                    style={"background": cor_barra},
                ),
                width="100%",
                height="8px",
                border_radius="4px",
                style={"background": "#EEE"},
                margin_y="0.4em",
            ),
            rx.hstack(
                rx.text("Gasto: " + vstr(item["gasto"]), size="1", color=rx.color("gray", 10)),
                rx.spacer(),
                rx.text("Limite: " + vstr(item["limite"]), size="1", color=rx.color("gray", 10)),
                width="100%",
            ),
            rx.cond(
                item["excedido"],
                rx.badge("⚠️ Limite excedido", color_scheme="red", size="1"),
                rx.text("Ainda disponível: " + vstr(item["restante"]), size="1", color=VERDE),
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
        padding="1em",
        border_radius="12px",
        style={"background": "white"},
        box_shadow="0 1px 6px rgba(0,0,0,0.06)",
    )


def _resumo_lojas() -> rx.Component:
    return card_container(
        rx.heading("Limite x Gasto do Mês, por Loja", size="3", margin_bottom="0.8em"),
        rx.grid(
            rx.foreach(DashboardState.lojas_resumo, _card_loja_resumo),
            columns=rx.breakpoints(initial="1", sm="2", md="3", lg="4"),
            spacing="3",
            width="100%",
        ),
        margin_bottom="1.2em",
    )


def _grafico_lojas() -> rx.Component:
    return card_container(
        rx.heading("Gastos por Loja (mês atual)", size="3", margin_bottom="0.5em"),
        rx.plotly(data=DashboardState.figura_lojas, width="100%"),
    )


def _grafico_tipos() -> rx.Component:
    return card_container(
        rx.heading("Distribuição por Tipo de Despesa", size="3", margin_bottom="0.5em"),
        rx.plotly(data=DashboardState.figura_tipos, width="100%"),
    )


def dashboard_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Dashboard", size="6", margin_bottom="0.3em"),
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
            # 2) Banner de alertas LOGO ABAIXO dos KPIs
            _alerta_vencimentos(),
            _resumo_lojas(),
            # 3) Gráficos (2/3) + Atividade Recente (1/3)
            rx.grid(
                rx.grid(
                    _grafico_lojas(),
                    _grafico_tipos(),
                    columns=rx.breakpoints(initial="1", lg="2"),
                    spacing="4",
                    width="100%",
                    grid_column="span 2",
                ),
                _painel_atividade(),
                columns=rx.breakpoints(initial="1", md="3"),
                spacing="4",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )