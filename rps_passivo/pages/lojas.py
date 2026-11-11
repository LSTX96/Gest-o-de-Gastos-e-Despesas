"""Página Lojas: limites, uso do mês, edição e desativação com confirmação."""
import reflex as rx

from ..state import LojasState, AppState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import numero_flutuante, painel_numeros, confirmar
from ..components.var_utils import vstr
from ..theme import (
    PRIMARY, PRIMARY_HOVER, DANGER, SUCCESS, WARNING,
    TEXT_TITLE, TEXT_MUTED, BORDER, CARD_BG, CARD_BG_2,
)

LS = LojasState
BRILHO_HOVER = "0 0 0 1px rgba(220,38,38,0.35), 0 10px 28px rgba(220,38,38,0.16)"


def _numeros() -> rx.Component:
    return painel_numeros(
        numero_flutuante("Soma dos limites mensais", LS.n_total_limite, icone="landmark"),
        numero_flutuante("Gasto do mês na rede", LS.n_total_gasto, icone="wallet"),
        numero_flutuante("Lojas excedidas", LS.n_excedidas, cor=DANGER, icone="circle-alert"),
        colunas="3",
    )


def _badge_situacao(loja: dict) -> rx.Component:
    """A cor já vem calculada no servidor e indica a situação da loja."""
    return rx.match(
        loja["cor_hex"],
        ("#EF4444", rx.badge("Excedida", color_scheme="red", size="1")),
        ("#F59E0B", rx.badge("Atenção", color_scheme="orange", size="1")),
        ("#94A3B8", rx.badge("Sem limite", color_scheme="gray", size="1")),
        rx.badge("Dentro do limite", color_scheme="green", size="1"),
    )


def _acoes(loja: dict) -> rx.Component:
    return rx.hstack(
        rx.link(
            rx.button(rx.icon("receipt", size=14), "Ver contas", size="1", variant="soft"),
            href="/contas?loja=" + vstr(loja["id_txt"]),
        ),
        rx.link(
            rx.button("Detalhes", size="1", variant="ghost"),
            href="/lojas/" + vstr(loja["id_txt"]),
        ),
        rx.spacer(),
        rx.cond(
            loja["pode_editar"],
            rx.icon_button(
                rx.icon("pencil", size=14),
                size="1",
                variant="soft",
                title="Editar loja",
                on_click=LS.abrir_edicao(loja),
            ),
        ),
        rx.cond(
            AppState.role == "admin",
            confirmar(
                rx.icon_button(
                    rx.icon("power", size=14), size="1", variant="soft",
                    color_scheme="red", title="Desativar loja",
                ),
                "Desativar esta loja?",
                "A loja sai das telas e dos totais. Os lançamentos continuam guardados "
                "e ela pode ser reativada a qualquer momento.",
                lambda: LS.desativar(loja["id"]),
                texto_confirmar="Desativar",
                cor="red",
            ),
        ),
        spacing="2",
        align="center",
        width="100%",
    )


def _card_loja(loja: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(
                    rx.text(loja["inicial"], weight="bold", color="white"),
                    width="42px", height="42px", min_width="42px",
                    border_radius="50%", bg=loja["cor"],
                ),
                rx.vstack(
                    rx.link(
                        rx.text(loja["nome"], weight="bold", size="3", color=TEXT_TITLE),
                        href="/lojas/" + vstr(loja["id_txt"]),
                        underline="none",
                    ),
                    rx.text("Limite: ", vstr(loja["limite_mensal"]), size="1", color=TEXT_MUTED),
                    spacing="0",
                    align="start",
                    min_width="0",
                ),
                rx.spacer(),
                _badge_situacao(loja),
                width="100%",
                align="center",
            ),
            rx.box(
                rx.box(
                    width=vstr(loja["largura_barra"]),
                    height="100%",
                    bg=loja["cor_hex"],
                    border_radius="999px",
                    transition="width 0.6s ease",
                ),
                width="100%",
                height="8px",
                bg=CARD_BG_2,
                border_radius="999px",
                overflow="hidden",
            ),
            rx.hstack(
                rx.text(vstr(loja["gasto_mes"]), weight="bold", size="4", color=TEXT_TITLE),
                rx.spacer(),
                rx.text(vstr(loja["pct_txt"]), size="2", weight="bold", color=loja["cor_hex"]),
                width="100%",
                align="baseline",
            ),
            rx.cond(
                loja["excedido"],
                rx.text("Acima do limite: ", vstr(loja["excesso"]), size="1", color=DANGER, weight="medium"),
                rx.cond(
                    loja["sem_limite"],
                    rx.text("Cadastre um limite para acompanhar o uso.", size="1", color=TEXT_MUTED),
                    rx.text("Disponível: ", vstr(loja["restante"]), size="1", color=SUCCESS),
                ),
            ),
            _acoes(loja),
            spacing="3",
            width="100%",
        ),
        padding="1.1em",
        border_radius="16px",
        bg=CARD_BG,
        border=f"1px solid {BORDER}",
        transition="all 0.2s ease",
        _hover={"border_color": PRIMARY, "transform": "translateY(-3px)", "box_shadow": BRILHO_HOVER},
    )


def _linha_inativa(loja: dict) -> rx.Component:
    return rx.hstack(
        rx.center(
            rx.icon("store", size=16, color="white"),
            width="32px", height="32px", min_width="32px",
            border_radius="50%", bg=loja["cor"], opacity="0.6",
        ),
        rx.text(loja["nome"], weight="bold", size="2", color=TEXT_MUTED),
        rx.spacer(),
        confirmar(
            rx.button(rx.icon("rotate-ccw", size=14), "Reativar", size="1", variant="soft", color_scheme="green"),
            "Reativar esta loja?",
            "A loja volta para as telas e para os totais, com todos os lançamentos.",
            lambda: LS.reativar(loja["id"]),
            texto_confirmar="Reativar",
            cor="green",
        ),
        width="100%",
        align="center",
        padding="0.6em 0",
        border_bottom=f"1px solid {BORDER}",
    )


def _inativas() -> rx.Component:
    return rx.cond(
        (AppState.role == "admin") & (LS.inativas.length() > 0),
        card_container(
            rx.hstack(
                rx.icon("power-off", size=16, color=TEXT_MUTED),
                rx.heading("Lojas desativadas", size="3", color=TEXT_TITLE),
                spacing="2",
                align="center",
                margin_bottom="0.4em",
            ),
            rx.vstack(rx.foreach(LS.inativas, _linha_inativa), spacing="0", width="100%"),
        ),
    )


def _campo(rotulo: str, componente: rx.Component, ajuda: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(rotulo, size="2", weight="medium", color=TEXT_TITLE),
        componente,
        rx.text(ajuda, size="1", color=TEXT_MUTED) if ajuda else rx.fragment(),
        spacing="1",
        width="100%",
    )


def _modal_loja() -> rx.Component:
    """Modal único para cadastrar (edit_id = 0) ou editar (edit_id > 0) uma loja."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(rx.cond(LS.edit_id > 0, "Editar loja", "Nova loja")),
            rx.vstack(
                _campo(
                    "Nome da loja *",
                    rx.input(
                        value=LS.form_nome,
                        on_change=LS.set_form_nome,
                        placeholder="Ex.: JARDIM CATARINA",
                        width="100%",
                        size="3",
                        style={"text_transform": "uppercase"},
                    ),
                ),
                rx.grid(
                    _campo(
                        "Limite mensal",
                        rx.input(
                            value=LS.form_limite_mensal,
                            on_change=LS.set_form_limite_mensal,
                            placeholder="Ex.: 60.000,00",
                            width="100%",
                            size="3",
                        ),
                    ),
                    _campo(
                        "Limite semanal",
                        rx.input(
                            value=LS.form_limite_semanal,
                            on_change=LS.set_form_limite_semanal,
                            placeholder="Ex.: 15.000,00",
                            width="100%",
                            size="3",
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.cond(
                    LS.erro != "",
                    rx.callout(LS.erro, color_scheme="red", icon="triangle-alert", size="1", width="100%"),
                ),
                spacing="3",
                width="100%",
                margin_top="0.8em",
            ),
            rx.hstack(
                rx.button("Cancelar", variant="soft", color_scheme="gray", on_click=LS.fechar_modal),
                rx.button(
                    "Salvar",
                    on_click=LS.salvar,
                    style={"background": PRIMARY, "color": "white", "_hover": {"background": PRIMARY_HOVER}},
                ),
                spacing="3",
                justify="end",
                width="100%",
                margin_top="1.2em",
            ),
            max_width="480px",
        ),
        open=LS.show_modal,
    )


def lojas_page() -> rx.Component:
    return page_shell(
        _modal_loja(),
        rx.vstack(
            rx.flex(
                rx.vstack(
                    rx.heading("Lojas e limites", size="7", letter_spacing="-0.02em", color=TEXT_TITLE),
                    rx.text(
                        "Teto de gastos de cada filial e quanto já foi usado no mês.",
                        size="2", color=TEXT_MUTED,
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=16), "Nova loja",
                    on_click=LS.abrir_novo,
                    size="3",
                    style={"background": PRIMARY, "color": "white", "_hover": {"background": PRIMARY_HOVER}},
                ),
                align="center",
                wrap="wrap",
                gap="1em",
                width="100%",
            ),
            _numeros(),
            rx.grid(
                rx.foreach(LS.lojas, _card_loja),
                columns=rx.breakpoints(initial="1", sm="2", lg="3"),
                spacing="3",
                width="100%",
            ),
            _inativas(),
            spacing="5",
            width="100%",
        ),
    )