import reflex as rx

from ..state import ContasPagarState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.semaforo_badge import semaforo_badge
from ..components.var_utils import vstr

VERMELHO = "#E31E24"
VERDE = "#00A651"


def _card_proximo(conta: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                semaforo_badge(conta["cor"], conta["status_txt"], "md"),
                rx.text(conta["loja"], size="1", weight="bold", color=rx.color("gray", 10)),
                spacing="2",
            ),
            rx.text(conta["nome"], size="2", weight="bold"),
            rx.text(conta["valor"], size="3", weight="bold", color=VERMELHO),
            rx.text(conta["vencimento"], size="1", color=rx.color("gray", 9)),
            rx.button(
                "Pagar",
                size="1",
                variant="soft",
                color_scheme="green",
                on_click=lambda: ContasPagarState.marcar_como_pago(conta["tipo"], conta["id"]),
            ),
            spacing="1",
            align="start",
        ),
        min_width="220px",
        padding="0.9em",
        border_radius="12px",
        style={"background": "#F8F9FA"},
        border=f"1px solid {rx.color('gray', 4)}",
    )


def _alerta_topo() -> rx.Component:
    return card_container(
        rx.heading("⚠️ Contas Próximas do Vencimento", size="3", margin_bottom="0.7em"),
        rx.cond(
            ContasPagarState.contas_proximas.length() > 0,
            rx.hstack(
                rx.foreach(ContasPagarState.contas_proximas, _card_proximo),
                overflow_x="auto",
                spacing="3",
                width="100%",
                padding_bottom="0.4em",
            ),
            rx.hstack(
                rx.icon("circle-check", color=VERDE),
                rx.text("Nenhuma conta próxima do vencimento", color=VERDE),
                spacing="2",
            ),
        ),
        margin_bottom="1.2em",
    )


def _linha_tabela(conta: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(semaforo_badge(conta["cor"], conta["status_txt"], "sm")),
        rx.table.cell(conta["loja"]),
        rx.table.cell(conta["tipo"]),
        rx.table.cell(conta["nome"]),
        rx.table.cell(conta["valor"]),
        rx.table.cell(conta["vencimento"]),
        rx.table.cell(conta["forma_pgto"]),
        rx.table.cell(
            rx.cond(
                conta["pago"],
                rx.badge("Pago", color_scheme="green"),
                rx.badge("Pendente", color_scheme="gray"),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.button("Detalhes", size="1", variant="soft", on_click=lambda: ContasPagarState.abrir_detalhe(conta)),
                rx.button("Editar", size="1", variant="soft", on_click=lambda: ContasPagarState.abrir_edicao_form(conta)),
                rx.button(
                    "Excluir", size="1", variant="soft", color_scheme="red",
                    on_click=lambda: ContasPagarState.excluir_conta(conta["tipo"], conta["id"]),
                ),
                spacing="2",
            ),
        ),
        style={"background": rx.cond(conta["cor"] == "#E31E24", "#FFF3F3", "white")},
    )


def _filtros() -> rx.Component:
    return card_container(
        rx.vstack(
            rx.hstack(
                rx.select.root(
                    rx.select.trigger(placeholder="Loja"),
                    rx.select.content(
                        rx.foreach(ContasPagarState.lojas_options, lambda l: rx.select.item(l, value=l)),
                    ),
                    value=ContasPagarState.filtro_loja,
                    on_change=ContasPagarState.set_filtro_loja,
                ),
                rx.select(
                    ["todas", "pendentes", "pagas"],
                    value=ContasPagarState.filtro_status,
                    on_change=ContasPagarState.set_filtro_status,
                ),
                rx.select(
                    ["todas", "fixas", "boletos"],
                    value=ContasPagarState.filtro_tipo,
                    on_change=ContasPagarState.set_filtro_tipo,
                ),
                rx.select(
                    ["vencimento", "valor"],
                    value=ContasPagarState.ordenar_por,
                    on_change=ContasPagarState.set_ordenar_por,
                ),
                spacing="3",
                wrap="wrap",
            ),
            rx.hstack(
                rx.vstack(
                    rx.text("De (histórico)", size="1", color=rx.color("gray", 9)),
                    rx.input(type="date", value=ContasPagarState.data_inicio, on_change=ContasPagarState.set_data_inicio),
                    spacing="1",
                    align="start",
                ),
                rx.vstack(
                    rx.text("Até", size="1", color=rx.color("gray", 9)),
                    rx.input(type="date", value=ContasPagarState.data_fim, on_change=ContasPagarState.set_data_fim),
                    spacing="1",
                    align="start",
                ),
                spacing="3",
            ),
            spacing="3",
        ),
        margin_bottom="1.2em",
    )


def _tabela() -> rx.Component:
    return card_container(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(""),
                    rx.table.column_header_cell("Loja"),
                    rx.table.column_header_cell("Tipo"),
                    rx.table.column_header_cell("Conta"),
                    rx.table.column_header_cell("Valor"),
                    rx.table.column_header_cell("Vencimento"),
                    rx.table.column_header_cell("Forma Pgto"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Ações"),
                )
            ),
            rx.table.body(rx.foreach(ContasPagarState.contas, _linha_tabela)),
            width="100%",
        ),
    )


def _drawer_detalhe() -> rx.Component:
    c = ContasPagarState.conta_selecionada
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(c["nome"]),
            rx.vstack(
                rx.text(c["loja"], color=rx.color("gray", 10)),
                rx.heading(c["valor"], size="7", color=VERMELHO),
                rx.hstack(
                    semaforo_badge(c["cor"], c["status_txt"], "lg"),
                    rx.text(c["status_txt"]),
                    spacing="2",
                ),
                rx.text("Vencimento: " + vstr(c["vencimento"])),
                rx.text("Forma de pagamento: " + vstr(c["forma_pgto"])),
                rx.cond(c["observacoes"] != "", rx.text("Obs: " + vstr(c["observacoes"]))),
                rx.hstack(
                    rx.button("Fechar", variant="soft", on_click=ContasPagarState.fechar_detalhe),
                    rx.button("Editar", variant="soft", on_click=lambda: ContasPagarState.abrir_edicao_form(c)),
                    rx.cond(
                        ~c["pago"],
                        rx.button(
                            "Marcar como Pago",
                            style={"background": VERDE, "color": "white"},
                            on_click=lambda: ContasPagarState.marcar_como_pago(c["tipo"], c["id"]),
                        ),
                    ),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=ContasPagarState.show_drawer,
    )


def _form_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(rx.cond(ContasPagarState.form_modo == "novo", "Nova Conta", "Editar Conta")),
            rx.vstack(
                rx.select.root(
                    rx.select.trigger(placeholder="Loja"),
                    rx.select.content(
                        rx.foreach(ContasPagarState.lojas_full, lambda s: rx.select.item(s["name"], value=s["id"])),
                    ),
                    value=ContasPagarState.form_loja_id,
                    on_change=ContasPagarState.set_form_loja_id,
                    width="100%",
                ),
                rx.segmented_control.root(
                    rx.segmented_control.item("Conta Fixa", value="fixa"),
                    rx.segmented_control.item("Outros", value="boleto"),
                    value=ContasPagarState.form_tipo,
                    on_change=ContasPagarState.set_form_tipo,
                    width="100%",
                ),
                rx.cond(
                    ContasPagarState.form_tipo == "fixa",
                    rx.vstack(
                        rx.input(placeholder="Nome da conta", value=ContasPagarState.form_nome, on_change=ContasPagarState.set_form_nome, width="100%"),
                        rx.input(placeholder="Dia de vencimento (ex: DIA 10)", value=ContasPagarState.form_dia, on_change=ContasPagarState.set_form_dia, width="100%"),
                        spacing="3",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.input(type="date", value=ContasPagarState.form_data, on_change=ContasPagarState.set_form_data, width="100%"),
                        rx.select.root(
                            rx.select.trigger(placeholder="Selecionar gasto"),
                            rx.select.content(
                                rx.foreach(ContasPagarState.distribuidoras_options, lambda d: rx.select.item(d["name"], value=d["id"])),
                            ),
                            value=ContasPagarState.form_distribuidor_id,
                            on_change=ContasPagarState.set_form_distribuidor_id,
                            width="100%",
                        ),
                        rx.select.root(
                            rx.select.trigger(placeholder="Tipo de despesa"),
                            rx.select.content(
                                rx.foreach(ContasPagarState.tipos_despesa_options, lambda t: rx.select.item(t["name"], value=t["id"])),
                            ),
                            value=ContasPagarState.form_tipo_despesa_id,
                            on_change=ContasPagarState.set_form_tipo_despesa_id,
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                rx.input(placeholder="Valor (R$)", value=ContasPagarState.form_valor, on_change=ContasPagarState.set_form_valor, width="100%"),
                rx.select(
                    ["Dinheiro", "PIX", "Boleto", "Caju", "Transferência"],
                    value=ContasPagarState.form_forma,
                    on_change=ContasPagarState.set_form_forma,
                    width="100%",
                ),
                rx.text_area(placeholder="Observações (opcional)", value=ContasPagarState.form_obs, on_change=ContasPagarState.set_form_obs, width="100%"),
                rx.hstack(
                    rx.button("Cancelar", variant="soft", on_click=ContasPagarState.fechar_form),
                    rx.button("Salvar", on_click=ContasPagarState.salvar_form, style={"background": VERMELHO, "color": "white"}),
                    spacing="2",
                ),
                spacing="3",
            ),
        ),
        open=ContasPagarState.show_form_modal,
    )


def contas_pagar_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.hstack(
                rx.heading("Contas a Pagar", size="6"),
                rx.spacer(),
                rx.button(rx.icon("plus", size=16), "Nova Conta", on_click=ContasPagarState.abrir_novo, style={"background": VERMELHO, "color": "white"}),
                rx.button(
                    rx.icon("download", size=16), "Exportar Excel",
                    variant="soft", on_click=ContasPagarState.exportar_excel,
                ),
                width="100%",
                align="center",
                margin_bottom="0.3em",
                wrap="wrap",
            ),
            _alerta_topo(),
            _filtros(),
            _tabela(),
            _drawer_detalhe(),
            _form_modal(),
            spacing="3",
            width="100%",
        ),
    )
