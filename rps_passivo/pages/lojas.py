"""Página de gerenciamento de lojas e limites mensais."""
import reflex as rx

from ..state import LojasState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.store_avatar import store_avatar
from ..components.var_utils import vstr
from ..theme import SUCCESS, DANGER, TEXT_MUTED

VERMELHO = "#E31E24"


def _barra_progresso(loja: dict) -> rx.Component:
    """Barra de uso do limite mensal. A cor e o valor vêm prontos do LojasState."""
    return rx.vstack(
        rx.hstack(
            rx.text("Uso do limite mensal", size="1", color=TEXT_MUTED),
            rx.spacer(),
            rx.text(vstr(loja["percentual"]) + "%", size="1", weight="bold", color=DANGER),
            width="100%",
        ),
        rx.progress(
            value=loja["barra"],
            color_scheme=loja["cor_barra"],
            size="2",
            width="100%",
        ),
        rx.cond(
            loja["excedido"],
            rx.text(
                "Excedido: " + vstr(loja["gasto_mes"]) + " / " + vstr(loja["limite_mensal"]),
                size="1",
                color=DANGER,
                weight="medium",
            ),
            rx.text(
                "Disponível: " + vstr(loja["restante"]),
                size="1",
                color=SUCCESS,
            ),
        ),
        width="100%",
        spacing="1",
    )


def _conteudo_card(loja: dict) -> rx.Component:
    """Conteúdo visual de um card de loja, com o botão de editar quando permitido."""
    return card_container(
        rx.vstack(
            rx.hstack(
                store_avatar(loja["nome"]),
                rx.vstack(
                    rx.heading(loja["nome"], size="3", weight="bold"),
                    rx.text(
                        "Limite: " + vstr(loja["limite_mensal"]),
                        size="1",
                        color=TEXT_MUTED,
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.cond(
                    loja["pode_editar"],
                    rx.button(
                        rx.icon("pencil", size=14),
                        size="1",
                        variant="soft",
                        on_click=[
                            rx.stop_propagation,
                            rx.prevent_default,
                            LojasState.abrir_edicao(loja),
                        ],
                    ),
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            _barra_progresso(loja),
            spacing="4",
            width="100%",
        )
    )


def _card_loja(loja: dict) -> rx.Component:
    """Card clicável: leva para a página de gastos da loja."""
    return rx.link(
        rx.box(
            _conteudo_card(loja),
            width="100%",
        ),
        href="/lojas/" + loja["id"].to_string(),
        underline="none",
        width="100%",
        _hover={"transform": "translateY(-2px)"},
        transition="all 0.15s ease",
    )


def _modal_loja() -> rx.Component:
    """Modal único para cadastrar (edit_id = 0) ou editar (edit_id > 0) uma loja."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(LojasState.edit_id > 0, "Editar loja", "Nova loja")
            ),
            rx.vstack(
                rx.text("Nome da loja", size="1", color=TEXT_MUTED),
                rx.input(
                    value=LojasState.form_nome,
                    on_change=LojasState.set_form_nome,
                    placeholder="Ex: JARDIM CATARINA",
                    width="100%",
                ),
                rx.text("Limite semanal", size="1", color=TEXT_MUTED),
                rx.input(
                    value=LojasState.form_limite_semanal,
                    on_change=LojasState.set_form_limite_semanal,
                    placeholder="Ex: 15000",
                    width="100%",
                ),
                rx.text("Limite mensal", size="1", color=TEXT_MUTED),
                rx.input(
                    value=LojasState.form_limite_mensal,
                    on_change=LojasState.set_form_limite_mensal,
                    placeholder="Ex: 60000",
                    width="100%",
                ),
                rx.cond(
                    LojasState.erro != "",
                    rx.text(LojasState.erro, size="2", color=DANGER),
                ),
                spacing="2",
                width="100%",
                margin_top="0.8em",
            ),
            rx.hstack(
                rx.button(
                    "Cancelar",
                    variant="soft",
                    on_click=LojasState.fechar_modal,
                ),
                rx.button(
                    "Salvar",
                    on_click=LojasState.salvar,
                    style={"background": VERMELHO, "color": "white"},
                ),
                spacing="3",
                justify="end",
                width="100%",
                margin_top="1em",
            ),
        ),
        open=LojasState.show_modal,
    )


def lojas_page() -> rx.Component:
    """Página de Lojas com grid responsivo, cards clicáveis e edição de loja."""
    return page_shell(
        _modal_loja(),
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Lojas e Limites", size="6", weight="bold"),
                    rx.text(
                        "Monitore o teto de gastos e limites de crédito por filial",
                        size="2",
                        color=TEXT_MUTED,
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=16),
                    "Nova Loja",
                    on_click=LojasState.abrir_novo,
                    style={"background": VERMELHO, "color": "white"},
                ),
                align="center",
                width="100%",
                margin_bottom="1.5em",
            ),
            rx.grid(
                rx.foreach(LojasState.lojas, _card_loja),
                columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
                spacing="4",
                width="100%",
            ),
            width="100%",
            spacing="4",
        )
    )