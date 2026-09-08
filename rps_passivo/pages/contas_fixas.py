import reflex as rx

from ..state import ContasFixasState
from ..components.navbar import page_shell
from ..components.cards import card_container

VERMELHO = "#E31E24"


def _linha(conta: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(conta["nome"]),
        rx.table.cell(conta["valor"]),
        rx.table.cell(conta["dia"]),
        rx.table.cell(conta["forma"]),
        rx.table.cell(
            rx.cond(
                conta["criado_por_operador"],
                rx.badge("Operador", color_scheme="orange"),
                rx.badge("Admin", color_scheme="gray"),
            )
        ),
        rx.table.cell(
            rx.cond(
                conta["pode_editar"],
                rx.hstack(
                    rx.button("Editar", size="1", variant="soft", on_click=lambda: ContasFixasState.abrir_edicao(conta)),
                    rx.button("Excluir", size="1", variant="soft", color_scheme="red", on_click=lambda: ContasFixasState.excluir(conta["id"])),
                    spacing="2",
                ),
            )
        ),
    )


def _modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Conta Fixa"),
            rx.vstack(
                rx.input(placeholder="Nome da conta", value=ContasFixasState.form_nome, on_change=ContasFixasState.set_form_nome),
                rx.input(placeholder="Valor mensal (R$)", value=ContasFixasState.form_valor, on_change=ContasFixasState.set_form_valor),
                rx.input(placeholder="Dia de vencimento (ex: DIA 10)", value=ContasFixasState.form_dia, on_change=ContasFixasState.set_form_dia),
                rx.select(
                    ["Dinheiro", "PIX", "Boleto", "Caju", "Transferência"],
                    value=ContasFixasState.form_forma,
                    on_change=ContasFixasState.set_form_forma,
                ),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=ContasFixasState.fechar_modal),
                    rx.button("Salvar", on_click=ContasFixasState.salvar, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=ContasFixasState.show_modal,
    )


def contas_fixas_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.hstack(
                rx.heading("Contas Fixas", size="6"),
                rx.spacer(),
                rx.button(rx.icon("plus", size=16), "Nova Conta Fixa", on_click=ContasFixasState.abrir_novo, style={"background": VERMELHO, "color": "white"}),
                width="100%",
                align="center",
            ),
            card_container(
                rx.select.root(
                    rx.select.trigger(placeholder="Loja"),
                    rx.select.content(
                        rx.foreach(
                            ContasFixasState.lojas_options,
                            lambda s: rx.select.item(s["name"], value=s["id"]),
                        )
                    ),
                    value=ContasFixasState.filtro_loja_id,
                    on_change=ContasFixasState.set_filtro_loja_id,
                ),
                margin_bottom="1.2em",
            ),
            card_container(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Nome"),
                            rx.table.column_header_cell("Valor"),
                            rx.table.column_header_cell("Vencimento"),
                            rx.table.column_header_cell("Forma Pgto"),
                            rx.table.column_header_cell("Cadastrado por"),
                            rx.table.column_header_cell("Ações"),
                        )
                    ),
                    rx.table.body(rx.foreach(ContasFixasState.contas, _linha)),
                    width="100%",
                ),
            ),
            _modal(),
            spacing="3",
            width="100%",
        ),
    )
