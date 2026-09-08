import reflex as rx

from ..state import RelatorioMensalState
from ..components.navbar import page_shell
from ..components.cards import card_container

VERMELHO = "#E31E24"


def _linha(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item["loja"]),
        rx.table.cell(item["limite"]),
        rx.table.cell(item["mes_atual"]),
        rx.table.cell(
            rx.cond(
                item["excedido"],
                rx.badge("⚠️ Excedido", color_scheme="red"),
                rx.badge("✅ Dentro do limite", color_scheme="green"),
            )
        ),
        style={"background": rx.cond(item["excedido"], "#FFF3F3", "white")},
    )


def _chip_loja(loja: dict) -> rx.Component:
    return rx.cond(
        RelatorioMensalState.lojas_selecionadas.contains(loja["id"]),
        rx.button(
            loja["name"], size="1", variant="solid", color_scheme="red",
            on_click=lambda: RelatorioMensalState.toggle_loja(loja["id"]),
        ),
        rx.button(
            loja["name"], size="1", variant="soft", color_scheme="gray",
            on_click=lambda: RelatorioMensalState.toggle_loja(loja["id"]),
        ),
    )


def _seletor_lojas() -> rx.Component:
    return card_container(
        rx.text("Comparar lojas", size="2", weight="bold", margin_bottom="0.5em"),
        rx.hstack(
            rx.foreach(RelatorioMensalState.lojas_options, _chip_loja),
            wrap="wrap",
            spacing="2",
        ),
        margin_bottom="1.2em",
    )


def _navegacao_periodo() -> rx.Component:
    return rx.hstack(
        rx.button("← Mês anterior", size="2", variant="soft", on_click=RelatorioMensalState.mes_anterior),
        rx.heading(RelatorioMensalState.periodo_label, size="4"),
        rx.button("Mês atual", size="2", variant="ghost", on_click=RelatorioMensalState.mes_atual),
        rx.button("Próximo mês →", size="2", variant="soft", on_click=RelatorioMensalState.mes_proximo),
        rx.select(
            RelatorioMensalState.meses_disponiveis,
            value=RelatorioMensalState.mes_selecionado_nome,
            on_change=RelatorioMensalState.set_mes_selecionado,
            width="140px",
        ),
        rx.select(
            RelatorioMensalState.anos_disponiveis,
            value=RelatorioMensalState.ano_selecionado.to_string(),
            on_change=RelatorioMensalState.set_ano_selecionado,
            width="100px",
        ),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="0.8em",
        wrap="wrap",
    )


def relatorio_mensal_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Relatório Mensal", size="6", margin_bottom="0.3em"),
            rx.text(
                "Use as setas para consultar meses anteriores (histórico) ou futuros.",
                size="2", color=rx.color("gray", 9), margin_bottom="0.6em",
            ),
            _navegacao_periodo(),
            _seletor_lojas(),
            card_container(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Loja"),
                            rx.table.column_header_cell("Limite Mensal"),
                            rx.table.column_header_cell("Total (Boletos + Fixas)"),
                            rx.table.column_header_cell("Status"),
                        )
                    ),
                    rx.table.body(rx.foreach(RelatorioMensalState.linhas, _linha)),
                    width="100%",
                ),
                margin_bottom="1.2em",
            ),
            rx.grid(
                card_container(
                    rx.heading("Gastos por Tipo de Despesa (comparativo)", size="3", margin_bottom="0.5em"),
                    rx.plotly(data=RelatorioMensalState.figura_tipos, width="100%"),
                ),
                card_container(
                    rx.heading("Formas de Pagamento mais usadas (comparativo)", size="3", margin_bottom="0.5em"),
                    rx.plotly(data=RelatorioMensalState.figura_formas, width="100%"),
                ),
                columns=rx.breakpoints(initial="1", sm="1", md="2"),
                spacing="4",
                width="100%",
            ),
            spacing="2",
            width="100%",
        ),
    )
