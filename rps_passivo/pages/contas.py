"""Página Contas (parte visual). As regras ficam em contas_estado.py."""
import reflex as rx

from .contas_estado import ContasState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import numero_flutuante, painel_numeros, confirmar
from ..theme import (
    PRIMARY, SUCCESS, WARNING, TEXT_TITLE, TEXT_MUTED, BORDER, CARD_BG_2,
)

CS = ContasState

__all__ = ["contas_page", "ContasState"]


def _numeros() -> rx.Component:
    return painel_numeros(
        numero_flutuante("A pagar no mês", CS.n_a_pagar, cor=WARNING, icone="clock"),
        numero_flutuante("Pago no mês", CS.n_pago, cor=SUCCESS, icone="circle-check"),
        numero_flutuante("Contas fixas no mês", CS.n_fixas, icone="repeat"),
        numero_flutuante("Despesas variáveis no mês", CS.n_variaveis, icone="shuffle"),
        numero_flutuante("Total histórico", CS.n_historico, detalhe=CS.n_historico_pago, icone="landmark"),
        colunas="3",
    )


def _destaque(icone: str, titulo: str, valor, cor: str) -> rx.Component:
    return rx.hstack(
        rx.center(
            rx.icon(icone, size=18, color=cor),
            width="40px",
            height="40px",
            min_width="40px",
            border_radius="12px",
            bg=CARD_BG_2,
        ),
        rx.vstack(
            rx.text(
                titulo, size="1", color=TEXT_MUTED,
                text_transform="uppercase", letter_spacing="0.06em",
            ),
            rx.text(valor, size="3", weight="bold", color=TEXT_TITLE),
            spacing="0",
            align="start",
            min_width="0",
        ),
        spacing="3",
        align="center",
        padding="0.9em 1em",
        border_radius="14px",
        border=f"1px solid {BORDER}",
        width="100%",
        transition="all 0.2s ease",
        _hover={"border_color": PRIMARY, "transform": "translateY(-2px)"},
    )


def _destaques() -> rx.Component:
    return rx.grid(
        _destaque("flame", "Principal despesa do mês", CS.destaque_mes, PRIMARY),
        _destaque("history", "Principal despesa histórica", CS.destaque_hist, WARNING),
        _destaque("telescope", "Principal previsão (30 dias)", CS.destaque_prev, SUCCESS),
        columns=rx.breakpoints(initial="1", md="3"),
        spacing="3",
        width="100%",
    )


def _filtros() -> rx.Component:
    return card_container(
        rx.flex(
            rx.hstack(
                rx.icon_button(rx.icon("chevron-left", size=18), variant="soft", on_click=CS.mes_anterior),
                rx.heading(CS.mes_label, size="4", min_width="170px", text_align="center"),
                rx.icon_button(rx.icon("chevron-right", size=18), variant="soft", on_click=CS.mes_proximo),
                rx.cond(
                    CS.mes_offset != 0,
                    rx.button("Mês atual", size="1", variant="soft", on_click=CS.mes_atual),
                ),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("file-spreadsheet", size=16), "Exportar Excel",
                    variant="soft", color_scheme="green", on_click=CS.exportar,
                ),
                rx.button(
                    rx.icon("trash-2", size=16),
                    rx.cond(CS.ver_lixeira, "Voltar às contas", "Lixeira"),
                    variant=rx.cond(CS.ver_lixeira, "solid", "soft"),
                    color_scheme="gray",
                    on_click=CS.alternar_lixeira,
                ),
                spacing="2",
            ),
            gap="0.8em",
            wrap="wrap",
            align="center",
            width="100%",
        ),
        rx.flex(
            rx.segmented_control.root(
                rx.segmented_control.item("Todas", value="todas"),
                rx.segmented_control.item("A pagar", value="a_pagar"),
                rx.segmented_control.item("Vencidas", value="vencidas"),
                rx.segmented_control.item("Pagas", value="pagas"),
                value=CS.filtro_situacao,
                on_change=CS.set_filtro_situacao,
            ),
            rx.select.root(
                rx.select.trigger(placeholder="Loja", min_width="170px"),
                rx.select.content(
                    rx.select.item("Todas as lojas", value="todas"),
                    rx.foreach(CS.lojas_opcoes, lambda x: rx.select.item(x["nome"], value=x["id"])),
                ),
                value=CS.filtro_loja,
                on_change=CS.set_filtro_loja,
            ),
            rx.select.root(
                rx.select.trigger(placeholder="Categoria", min_width="150px"),
                rx.select.content(
                    rx.select.item("Fixas e variáveis", value="todos"),
                    rx.select.item("Só contas fixas", value="fixas"),
                    rx.select.item("Só variáveis", value="variaveis"),
                ),
                value=CS.filtro_tipo,
                on_change=CS.set_filtro_tipo,
            ),
            rx.input(
                rx.input.slot(rx.icon("search", size=16)),
                placeholder="Buscar gasto, tipo ou loja",
                value=CS.busca,
                on_change=CS.set_busca,
                flex="1 1 220px",
            ),
            gap="0.8em",
            wrap="wrap",
            align="center",
            width="100%",
            margin_top="1em",
        ),
    )


def _badge_status(c) -> rx.Component:
    return rx.match(
        c["status"],
        ("paga", rx.badge(rx.icon("check", size=12), "Paga", color_scheme="green", size="1")),
        ("vencida", rx.badge(rx.icon("triangle-alert", size=12), "Vencida", color_scheme="red", size="1")),
        ("hoje", rx.badge(rx.icon("bell", size=12), "Vence hoje", color_scheme="orange", size="1")),
        rx.badge("A pagar", color_scheme="gray", size="1"),
    )


def _acoes(c) -> rx.Component:
    botao_pagar = rx.button(
        rx.icon("check", size=14), "Pagar",
        size="1", variant="soft", color_scheme="green",
        on_click=lambda: CS.abrir_pagamento(c["kind"], c["id"], c["comp"], c["gasto"], c["valor"]),
    )
    botao_desfazer = confirmar(
        rx.button(rx.icon("undo-2", size=14), "Desfazer", size="1", variant="soft", color_scheme="gray"),
        "Desfazer o pagamento?",
        "A conta " + c["gasto"] + " voltará para A PAGAR.",
        lambda: CS.desfazer(c["kind"], c["id"], c["comp"]),
        texto_confirmar="Desfazer pagamento",
        cor="orange",
    )
    botao_excluir = confirmar(
        rx.icon_button(rx.icon("trash-2", size=14), size="1", variant="soft", color_scheme="red"),
        "Enviar para a lixeira?",
        "A conta " + c["gasto"] + " sai da lista. Você pode restaurá-la depois pela Lixeira.",
        lambda: CS.excluir(c["kind"], c["id"]),
        texto_confirmar="Enviar para a lixeira",
        cor="red",
    )
    return rx.cond(
        CS.pode_agir,
        rx.hstack(
            rx.cond(c["status"] == "paga", botao_desfazer, botao_pagar),
            botao_excluir,
            spacing="2",
        ),
    )


def _dialogo_pagamento() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Registrar pagamento"),
            rx.alert_dialog.description(
                "Confira a data em que a conta foi paga.", size="2", color=TEXT_MUTED,
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(CS.pag_nome, weight="bold", size="3", color=TEXT_TITLE),
                    rx.spacer(),
                    rx.text(CS.pag_valor, weight="bold", size="3", color=TEXT_TITLE),
                    width="100%",
                    align="center",
                ),
                rx.text("Data do pagamento", size="2", weight="medium", color=TEXT_TITLE, margin_top="0.6em"),
                rx.input(
                    type="date",
                    value=CS.pag_data,
                    on_change=CS.set_pag_data,
                    max=CS.pag_max,
                    size="3",
                    width="100%",
                ),
                rx.text(
                    "Já vem com a data de hoje. Se a conta foi paga em outro dia, troque a data: "
                    "é ela que alimenta os indicadores de pontualidade.",
                    size="1", color=TEXT_MUTED,
                ),
                spacing="1",
                width="100%",
                margin_top="0.8em",
                padding="0.9em",
                border_radius="10px",
                bg=CARD_BG_2,
                border=f"1px solid {BORDER}",
            ),
            rx.flex(
                rx.button("Cancelar", variant="soft", color_scheme="gray", on_click=CS.fechar_pagamento),
                rx.button(
                    rx.icon("check", size=16), "Confirmar pagamento",
                    color_scheme="green", on_click=CS.confirmar_pagamento,
                ),
                spacing="3",
                justify="end",
                margin_top="1.2em",
            ),
            max_width="440px",
        ),
        open=CS.pag_aberto,
    )


def _linha_conta(c) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(c["dia"], size="6", weight="bold", line_height="1", color=TEXT_TITLE),
            rx.text(c["mes_abrev"], size="1", color=TEXT_MUTED, letter_spacing="0.08em"),
            spacing="1",
            align="center",
            justify="center",
            min_width="56px",
            padding="0.5em 0.4em",
            border_radius="12px",
            bg=CARD_BG_2,
        ),
        rx.vstack(
            rx.hstack(
                rx.text(c["gasto"], weight="bold", size="3", color=TEXT_TITLE),
                rx.cond(c["parcela"] != "", rx.badge(c["parcela"], variant="soft", size="1")),
                spacing="2",
                align="center",
                wrap="wrap",
            ),
            rx.text(c["tipo"], " · ", c["loja"], size="1", color=TEXT_MUTED),
            rx.badge(
                c["categoria"],
                variant="outline",
                size="1",
                color_scheme=rx.cond(c["categoria"] == "FIXA", "blue", "gray"),
            ),
            spacing="1",
            align="start",
            min_width="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                c["valor"], weight="bold", size="4", color=TEXT_TITLE,
                style={"font_variant_numeric": "tabular-nums"},
            ),
            _badge_status(c),
            _acoes(c),
            spacing="2",
            align="end",
        ),
        width="100%",
        align="center",
        spacing="3",
        padding="0.9em 0.7em",
        border_radius="12px",
        border_bottom=f"1px solid {BORDER}",
        transition="background 0.15s ease",
        _hover={"background": CARD_BG_2},
    )


def _lista_contas() -> rx.Component:
    return card_container(
        rx.hstack(
            rx.heading("Contas do mês", size="4"),
            rx.spacer(),
            rx.text(CS.resumo_lista, size="2", color=TEXT_MUTED),
            align="center",
            width="100%",
            margin_bottom="0.6em",
        ),
        rx.cond(
            CS.contas_filtradas.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=32, color=TEXT_MUTED),
                    rx.text("Nenhuma conta encontrada com estes filtros.", color=TEXT_MUTED),
                    align="center",
                    spacing="2",
                ),
                padding="2.5em",
            ),
            rx.vstack(rx.foreach(CS.contas_filtradas, _linha_conta), spacing="0", width="100%"),
        ),
    )


def _linha_lixeira(item) -> rx.Component:
    return rx.hstack(
        rx.icon("trash-2", size=18, color=TEXT_MUTED),
        rx.vstack(
            rx.text(item["gasto"], weight="bold", size="2", color=TEXT_TITLE),
            rx.text(item["detalhe"], size="1", color=TEXT_MUTED),
            rx.text(item["quando"], size="1", color=TEXT_MUTED),
            spacing="0",
            align="start",
            min_width="0",
        ),
        rx.spacer(),
        rx.text(item["valor"], weight="bold", size="3", color=TEXT_TITLE),
        rx.cond(
            CS.pode_agir,
            confirmar(
                rx.button(
                    rx.icon("rotate-ccw", size=14), "Restaurar",
                    size="1", variant="soft", color_scheme="green",
                ),
                "Restaurar esta conta?",
                "A conta " + item["gasto"] + " volta para a lista e para os totais.",
                lambda: CS.restaurar(item["kind"], item["id"]),
                texto_confirmar="Restaurar",
                cor="green",
            ),
        ),
        width="100%",
        align="center",
        spacing="3",
        padding="0.8em 0.6em",
        border_bottom=f"1px solid {BORDER}",
    )


def _lista_lixeira() -> rx.Component:
    return card_container(
        rx.heading("Lixeira", size="4", margin_bottom="0.2em"),
        rx.text(
            "Contas excluídas não entram nos totais. Restaure se a exclusão foi por engano.",
            size="2",
            color=TEXT_MUTED,
            margin_bottom="0.6em",
        ),
        rx.cond(
            CS.lixeira.length() == 0,
            rx.center(rx.text("A lixeira está vazia.", color=TEXT_MUTED), padding="2em"),
            rx.vstack(rx.foreach(CS.lixeira, _linha_lixeira), spacing="0", width="100%"),
        ),
    )


def contas_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.vstack(
                rx.heading("Contas", size="7", letter_spacing="-0.02em"),
                rx.text(
                    "Contas fixas e despesas variáveis da rede, em ordem de vencimento.",
                    size="2",
                    color=TEXT_MUTED,
                ),
                spacing="1",
            ),
            _numeros(),
            _destaques(),
            _filtros(),
            rx.cond(CS.ver_lixeira, _lista_lixeira(), _lista_contas()),
            _dialogo_pagamento(),
            spacing="5",
            width="100%",
        ),
    )