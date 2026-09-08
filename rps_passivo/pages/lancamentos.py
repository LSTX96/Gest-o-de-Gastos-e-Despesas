import reflex as rx

from ..state import LancamentosState
from ..components.navbar import page_shell
from ..components.cards import card_container

VERMELHO = "#E31E24"
VERDE = "#00A651"


def _modal_nova_loja() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Nova Loja"),
            rx.vstack(
                rx.input(placeholder="Nome da loja", value=LancamentosState.nova_loja_nome, on_change=LancamentosState.set_nova_loja_nome),
                rx.input(placeholder="Limite semanal (R$)", value=LancamentosState.nova_loja_limite_semanal, on_change=LancamentosState.set_nova_loja_limite_semanal),
                rx.input(placeholder="Limite mensal (R$)", value=LancamentosState.nova_loja_limite_mensal, on_change=LancamentosState.set_nova_loja_limite_mensal),
                rx.upload(
                    rx.button("Upload de logo (opcional)", variant="soft", size="2"),
                    id="upload_logo_loja",
                    max_files=1,
                    accept={"image/*": [".png", ".jpg", ".jpeg", ".webp"]},
                ),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=LancamentosState.toggle_modal_loja),
                    rx.button("Salvar", on_click=LancamentosState.salvar_nova_loja, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=LancamentosState.show_modal_loja,
    )


def _modal_nova_conta_fixa() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Nova Conta Fixa"),
            rx.vstack(
                rx.input(placeholder="Nome da conta", value=LancamentosState.nova_conta_nome, on_change=LancamentosState.set_nova_conta_nome),
                rx.input(placeholder="Valor mensal (R$)", value=LancamentosState.nova_conta_valor, on_change=LancamentosState.set_nova_conta_valor),
                rx.input(placeholder="Dia de vencimento (ex: DIA 10)", value=LancamentosState.nova_conta_dia, on_change=LancamentosState.set_nova_conta_dia),
                rx.select(["Dinheiro", "PIX", "Boleto", "Caju", "Transferência"], value=LancamentosState.nova_conta_forma, on_change=LancamentosState.set_nova_conta_forma),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=LancamentosState.toggle_modal_conta_fixa),
                    rx.button("Salvar", on_click=LancamentosState.salvar_nova_conta_fixa, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=LancamentosState.show_modal_conta_fixa,
    )


def _modal_nova_distribuidora() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Nova Distribuidora"),
            rx.vstack(
                rx.input(placeholder="Nome da distribuidora", value=LancamentosState.nova_distribuidora_nome, on_change=LancamentosState.set_nova_distribuidora_nome),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=LancamentosState.toggle_modal_distribuidora),
                    rx.button("Salvar", on_click=LancamentosState.salvar_nova_distribuidora, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=LancamentosState.show_modal_distribuidora,
    )


def _modal_novo_tipo() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Novo Tipo de Despesa"),
            rx.vstack(
                rx.input(placeholder="Nome do tipo", value=LancamentosState.novo_tipo_nome, on_change=LancamentosState.set_novo_tipo_nome),
                rx.select(["Fixa", "Variável"], value=LancamentosState.novo_tipo_categoria, on_change=LancamentosState.set_novo_tipo_categoria),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=LancamentosState.toggle_modal_tipo),
                    rx.button("Salvar", on_click=LancamentosState.salvar_novo_tipo, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=LancamentosState.show_modal_tipo,
    )


def _card_selecao_loja() -> rx.Component:
    return card_container(
        rx.heading("1. Loja", size="3", margin_bottom="0.5em"),
        rx.hstack(
            rx.select.root(
                rx.select.trigger(placeholder="Selecione a loja", width="100%"),
                rx.select.content(
                    rx.foreach(
                        LancamentosState.stores,
                        lambda s: rx.select.item(s["name"], value=s["id"]),
                    )
                ),
                value=LancamentosState.selected_store_id,
                on_change=LancamentosState.set_selected_store_id,
                width="100%",
            ),
            rx.button(rx.icon("plus", size=16), "Nova Loja", variant="soft", on_click=LancamentosState.toggle_modal_loja),
            rx.button(
                rx.icon("trash-2", size=16), "Remover",
                variant="soft", color_scheme="red",
                on_click=LancamentosState.remover_loja_selecionada,
            ),
            spacing="2",
            width="100%",
            wrap="wrap",
        ),
        margin_bottom="1.2em",
    )


def _card_tipo_e_dados() -> rx.Component:
    return card_container(
        rx.heading("2. Tipo de Lançamento", size="3", margin_bottom="0.5em"),
        rx.segmented_control.root(
            rx.segmented_control.item("Conta Fixa", value="fixa"),
            rx.segmented_control.item("Outros (compras, pagamentos diversos)", value="boleto"),
            value=LancamentosState.tipo_lancamento,
            on_change=LancamentosState.set_tipo_lancamento,
            width="100%",
            margin_bottom="1em",
        ),
        rx.cond(
            LancamentosState.tipo_lancamento == "fixa",
            rx.vstack(
                rx.hstack(
                    rx.select.root(
                        rx.select.trigger(placeholder="Selecione a conta fixa"),
                        rx.select.content(
                            rx.foreach(
                                LancamentosState.fixed_expenses_options,
                                lambda c: rx.select.item(c["name"], value=c["id"]),
                            )
                        ),
                        value=LancamentosState.selected_fixed_expense_id,
                        on_change=LancamentosState.set_selected_fixed_expense_id,
                        width="100%",
                    ),
                    rx.button(rx.icon("plus", size=16), "Nova Conta", variant="soft", on_click=LancamentosState.toggle_modal_conta_fixa),
                    spacing="2",
                    width="100%",
                ),
                rx.text("Valor sugerido com base no último lançamento — ajuste se necessário:", size="1", color=rx.color("gray", 9)),
                rx.input(placeholder="Valor (R$)", value=LancamentosState.fixa_valor, on_change=LancamentosState.set_fixa_valor),
                rx.checkbox("Pagamento já efetuado", checked=LancamentosState.fixa_pago, on_change=LancamentosState.set_fixa_pago),
                rx.button("Salvar Lançamento", on_click=LancamentosState.salvar_conta_fixa_lancamento, style={"background": VERMELHO, "color": "white"}, width="100%"),
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.hstack(
                    rx.select.root(
                        rx.select.trigger(placeholder="Selecionar gasto"),
                        rx.select.content(
                            rx.foreach(
                                LancamentosState.distributor_options,
                                lambda d: rx.select.item(d["name"], value=d["id"]),
                            )
                        ),
                        value=LancamentosState.selected_distributor_id,
                        on_change=LancamentosState.set_selected_distributor_id,
                        width="100%",
                    ),
                    rx.button(rx.icon("plus", size=16), variant="soft", on_click=LancamentosState.toggle_modal_distribuidora),
                    spacing="2",
                    width="100%",
                ),
                rx.input(type="date", value=LancamentosState.boleto_data, on_change=LancamentosState.set_boleto_data, width="100%"),
                rx.input(placeholder="Valor (R$)", value=LancamentosState.boleto_valor, on_change=LancamentosState.set_boleto_valor),
                rx.select(
                    ["Dinheiro", "PIX", "Boleto", "Caju", "Transferência"],
                    value=LancamentosState.boleto_forma_pgto,
                    on_change=LancamentosState.set_boleto_forma_pgto,
                    width="100%",
                ),
                rx.hstack(
                    rx.select.root(
                        rx.select.trigger(placeholder="Tipo de despesa"),
                        rx.select.content(
                            rx.foreach(
                                LancamentosState.expense_type_options,
                                lambda t: rx.select.item(t["name"], value=t["id"]),
                            )
                        ),
                        value=LancamentosState.selected_expense_type_id,
                        on_change=LancamentosState.set_selected_expense_type_id,
                        width="100%",
                    ),
                    rx.button(rx.icon("plus", size=16), variant="soft", on_click=LancamentosState.toggle_modal_tipo),
                    spacing="2",
                    width="100%",
                ),
                rx.text_area(placeholder="Observações (opcional)", value=LancamentosState.boleto_obs, on_change=LancamentosState.set_boleto_obs, width="100%"),
                rx.button("Salvar Lançamento", on_click=LancamentosState.salvar_boleto, style={"background": VERMELHO, "color": "white"}, width="100%"),
                spacing="3",
                width="100%",
            ),
        ),
        margin_bottom="1.2em",
    )


def _card_ultimos() -> rx.Component:
    return card_container(
        rx.heading("3. Lançamentos Recentes", size="3", margin_bottom="0.5em"),
        rx.cond(
            LancamentosState.msg_sucesso != "",
            rx.callout(LancamentosState.msg_sucesso, color_scheme="green", margin_bottom="0.6em"),
        ),
        rx.vstack(
            rx.foreach(
                LancamentosState.ultimos_lancamentos,
                lambda item: rx.hstack(
                    rx.text(item["descricao"], size="2"),
                    rx.spacer(),
                    rx.text(item["valor"], size="2", weight="bold"),
                    rx.text(item["data"], size="1", color=rx.color("gray", 9)),
                    width="100%",
                    padding="0.4em 0",
                    border_bottom=f"1px solid {rx.color('gray', 4)}",
                ),
            ),
            width="100%",
        ),
    )


def lancamentos_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Lançamentos", size="6", margin_bottom="0.3em"),
            _card_selecao_loja(),
            _card_tipo_e_dados(),
            _card_ultimos(),
            _modal_nova_loja(),
            _modal_nova_conta_fixa(),
            _modal_nova_distribuidora(),
            _modal_novo_tipo(),
            spacing="3",
            width="100%",
            max_width="720px",
        ),
    )
