import reflex as rx

from ..state import RelatorioSemanalState
from ..components.navbar import page_shell
from ..components.cards import card_container

VERMELHO = "#E31E24"
VERDE = "#00A651"


def _linha(item: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item["loja"]),
        rx.table.cell(item["limite"]),
        rx.table.cell(item["boletos"]),
        rx.table.cell(item["fixas"]),
        rx.table.cell(item["total"]),
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
        RelatorioSemanalState.lojas_selecionadas.contains(loja["id"]),
        rx.button(
            loja["name"], size="1", variant="solid", color_scheme="red",
            on_click=lambda: RelatorioSemanalState.toggle_loja(loja["id"]),
        ),
        rx.button(
            loja["name"], size="1", variant="soft", color_scheme="gray",
            on_click=lambda: RelatorioSemanalState.toggle_loja(loja["id"]),
        ),
    )


def _seletor_lojas() -> rx.Component:
    return card_container(
        rx.text("Comparar lojas", size="2", weight="bold", margin_bottom="0.5em"),
        rx.hstack(
            rx.foreach(RelatorioSemanalState.lojas_options, _chip_loja),
            wrap="wrap",
            spacing="2",
        ),
        margin_bottom="1.2em",
    )


def _navegacao_periodo() -> rx.Component:
    return rx.hstack(
        rx.button("← Semana anterior", size="2", variant="soft", on_click=RelatorioSemanalState.semana_anterior),
        rx.heading(RelatorioSemanalState.periodo_label, size="4"),
        rx.button("Semana atual", size="2", variant="ghost", on_click=RelatorioSemanalState.semana_atual),
        rx.button("Próxima semana →", size="2", variant="soft", on_click=RelatorioSemanalState.semana_proxima),
        rx.input(
            type="date",
            value=RelatorioSemanalState.data_ref,
            on_change=RelatorioSemanalState.set_data_ref,
            width="160px",
        ),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="0.8em",
        wrap="wrap",
    )


def relatorio_semanal_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Relatório Semanal", size="6", margin_bottom="0.3em"),
            rx.text(
                "Use as setas para consultar semanas anteriores (histórico) ou futuras.",
                size="2", color=rx.color("gray", 9), margin_bottom="0.6em",
            ),
            _navegacao_periodo(),
            _seletor_lojas(),
            rx.grid(
                card_container(rx.text("Limite Total", size="1"), rx.heading(RelatorioSemanalState.total_limite, size="4")),
                card_container(rx.text("Boletos", size="1"), rx.heading(RelatorioSemanalState.total_boletos, size="4")),
                card_container(rx.text("Fixas", size="1"), rx.heading(RelatorioSemanalState.total_fixas, size="4")),
                card_container(rx.text("Total Geral", size="1"), rx.heading(RelatorioSemanalState.total_geral, size="4", color=VERMELHO)),
                columns=rx.breakpoints(initial="2", sm="2", md="4"),
                spacing="4",
                width="100%",
                margin_bottom="1.2em",
            ),
            card_container(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Loja"),
                            rx.table.column_header_cell("Limite Semanal"),
                            rx.table.column_header_cell("Boletos"),
                            rx.table.column_header_cell("Fixas"),
                            rx.table.column_header_cell("Boletos + Fixas"),
                            rx.table.column_header_cell("Status"),
                        )
                    ),
                    rx.table.body(rx.foreach(RelatorioSemanalState.linhas, _linha)),
                    width="100%",
                ),
                margin_bottom="1.2em",
            ),
            rx.grid(
                card_container(
                    rx.heading("Gastos por Tipo de Despesa (comparativo)", size="3", margin_bottom="0.5em"),
                    rx.plotly(data=RelatorioSemanalState.figura_tipos, width="100%"),
                ),
                card_container(
                    rx.heading("Formas de Pagamento mais usadas (comparativo)", size="3", margin_bottom="0.5em"),
                    rx.plotly(data=RelatorioSemanalState.figura_formas, width="100%"),
                ),
                columns=rx.breakpoints(initial="1", sm="1", md="2"),
                spacing="4",
                width="100%",
            ),
            spacing="2",
            width="100%",
        ),
    )
