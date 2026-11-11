"""Navbar: barra superior vermelha, fixa no topo, com alternância de tema.

- Links de navegação não quebram linha; se faltar espaço, a faixa central rola.
- Logo Cumani dentro de um quadro branco, para aparecer sobre o vermelho.
- Botão de sol/lua alterna entre o tema escuro (padrão) e o claro.
"""
from __future__ import annotations

import reflex as rx

from ..state import AppState, role_allowed, LojasState
from ..theme import (
    PRIMARY, PRIMARY_BG, TEXT_BODY, PAGE_BG,
    BORDER, CARD_BG, SHADOW, RADIUS, SPACE,
)

APP_TITLE = "Gestão de Custos e Despesas Cumani"

BAR_RED = "#E31E24"
BAR_TEXT = "#FFFFFF"
BAR_HOVER = "rgba(255,255,255,0.15)"

# Ajustes para gráficos (Plotly) acompanharem o tema
TEMA_CSS = """
<style>
.js-plotly-plot .main-svg { background: transparent !important; }
.js-plotly-plot .bg { fill: transparent !important; }
</style>
"""

# (label, rota, ícone, perfis que enxergam)
NAV_ITEMS =  [
    ("Menu Inicial", "/dashboard", "layout-dashboard", ("admin", "operator", "viewer")),
    ("Lançamentos", "/lancamentos", "square-plus", ("admin", "operator")),
    ("Contas", "/contas", "receipt", ("admin", "operator", "viewer")),
    ("Relatórios", "/relatorios", "chart-pie", ("admin", "operator", "viewer")),
    ("Lojas", "/lojas", "store", ("admin", "operator", "viewer")),
]

USERS_ITEM = ("Usuários", "/usuarios", "users", ("admin", "operator", "viewer"))


def _nav_link(item, mobile: bool = False) -> rx.Component:
    """Link de navegação. No desktop fica sobre o vermelho; no mobile, sobre o card."""
    nome, href, icone, roles = item
    is_active = AppState.current_route == href

    if mobile:
        cor_texto = rx.cond(is_active, "white", TEXT_BODY)
        cor_fundo = rx.cond(is_active, PRIMARY, "transparent")
        cor_hover = rx.cond(is_active, PRIMARY, PRIMARY_BG)
        largura = "100%"
    else:
        cor_texto = rx.cond(is_active, BAR_RED, BAR_TEXT)
        cor_fundo = rx.cond(is_active, "#FFFFFF", "transparent")
        cor_hover = rx.cond(is_active, "#FFFFFF", BAR_HOVER)
        largura = "auto"

    conteudo = rx.hstack(
        rx.icon(icone, size=18, color=cor_texto),
        rx.text(
            nome,
            size="2",
            weight=rx.cond(is_active, "bold", "medium"),
            color=cor_texto,
            white_space="nowrap",
        ),
        spacing="2",
        align="center",
        padding=f"{SPACE[2]} {SPACE[3]}",
        border_radius=RADIUS["sm"],
        width=largura,
        white_space="nowrap",
        bg=cor_fundo,
        _hover={"background": cor_hover},
    )

    return rx.cond(
        role_allowed(AppState.role, roles),
        rx.link(
            conteudo,
            href=href,
            underline="none",
            on_click=AppState.fechar_mobile_menu,
            flex_shrink="0",
        ),
    )


def _brand() -> rx.Component:
    """Logo Cumani dentro de um quadro branco."""
    return rx.link(
        rx.box(
            rx.image(
                src="/logo_cumani.png",
                width="36px",
                height="36px",
                style={"object_fit": "contain"},
            ),
            bg="#FFFFFF",
            padding="4px",
            border_radius=RADIUS["sm"],
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        href="/dashboard",
        underline="none",
        flex_shrink="0",
    )


def _botao_tema() -> rx.Component:
    """Alterna entre tema escuro e claro."""
    return rx.icon_button(
        rx.color_mode_cond(
            light=rx.icon("moon", size=16),
            dark=rx.icon("sun", size=16),
        ),
        on_click=rx.toggle_color_mode,
        variant="ghost",
        size="2",
        style={"color": BAR_TEXT},
        title="Alternar tema claro/escuro",
    )


def _user_menu() -> rx.Component:
    return rx.hstack(
        rx.cond(
            role_allowed(AppState.role, USERS_ITEM[3]),
            rx.link(
                rx.icon_button(
                    rx.icon("users", size=18),
                    variant="ghost",
                    size="2",
                    style={
                        "background": rx.cond(
                            AppState.current_route == USERS_ITEM[1], "#FFFFFF", "transparent"
                        ),
                        "color": rx.cond(
                            AppState.current_route == USERS_ITEM[1], BAR_RED, BAR_TEXT
                        ),
                    },
                ),
                href=USERS_ITEM[1],
                underline="none",
            ),
        ),
        _botao_tema(),
        rx.flex(
            AppState.display_name[:1].upper(),
            width="32px",
            height="32px",
            border_radius="50%",
            bg="#FFFFFF",
            justify="center",
            align="center",
            color=BAR_RED,
            font_weight="bold",
            font_size="12px",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(AppState.display_name, size="1", weight="medium", color=BAR_TEXT),
            rx.text(AppState.role_label, size="1", color="rgba(255,255,255,0.8)"),
            spacing="0",
            align="start",
            display=["none", "none", "none", "flex"],
        ),
        rx.button(
            rx.icon("log-out", size=16),
            variant="ghost",
            size="1",
            style={"color": BAR_TEXT},
            on_click=AppState.logout,
        ),
        spacing="3",
        align="center",
        flex_shrink="0",
    )


def _header_action() -> rx.Component:
    """Ação principal da página ativa, em branco sobre o vermelho."""
    estilo_botao = {
        "background": "#FFFFFF",
        "color": BAR_RED,
        "font_weight": "bold",
    }
    return rx.cond(
        (AppState.current_route == "/contas") & role_allowed(AppState.role, ("admin", "operator")),
        rx.link(
            rx.button(rx.icon("plus", size=16), "Novo lançamento", style=estilo_botao),
            href="/lancamentos",
            underline="none",
        ),
        rx.cond(
            AppState.current_route == "/lojas",
            rx.button(
                rx.icon("plus", size=16), "Nova Loja",
                on_click=LojasState.abrir_novo,
                style=estilo_botao,
            ),
            rx.fragment(),
        ),
    )


def _menu_mobile() -> rx.Component:
    """Menu hambúrguer para telas pequenas."""
    return rx.box(
        rx.button(
            rx.icon("menu", size=22),
            variant="ghost",
            on_click=AppState.toggle_mobile_menu,
            style={"color": BAR_TEXT},
            display=["flex", "flex", "flex", "none"],
        ),
        rx.cond(
            AppState.mobile_menu_open,
            rx.box(
                rx.vstack(
                    *[_nav_link(item, mobile=True) for item in NAV_ITEMS],
                    _nav_link(USERS_ITEM, mobile=True),
                    spacing="1",
                    width="100%",
                    padding=SPACE[3],
                ),
                position="absolute",
                top="64px",
                left="0",
                width="100%",
                style={"background": CARD_BG, "border-bottom": f"1px solid {BORDER}"},
                box_shadow=SHADOW["sm"],
                z_index="40",
                display=["block", "block", "block", "none"],
            ),
        ),
    )


def navbar() -> rx.Component:
    """Barra superior vermelha, fixa no topo."""
    return rx.box(
        rx.hstack(
            rx.box(_brand(), flex_shrink="0"),
            rx.hstack(
                *[_nav_link(item) for item in NAV_ITEMS],
                spacing="1",
                align="center",
                wrap="nowrap",
                flex="1",
                min_width="0",
                overflow_x="auto",
                display=["none", "none", "none", "flex"],
                style={"scrollbar_width": "none"},
            ),
            rx.box(_header_action(), flex_shrink="0"),
            rx.box(_menu_mobile(), flex_shrink="0"),
            rx.box(_user_menu(), flex_shrink="0"),
            width="100%",
            align="center",
            spacing="3",
            wrap="nowrap",
            padding=f"0 {SPACE[4]}",
            height="64px",
        ),
        position="sticky",
        top="0",
        z_index="30",
        width="100%",
        bg=BAR_RED,
        box_shadow=SHADOW["sm"],
    )


def page_shell(*children) -> rx.Component:
    """Layout padrão: barra superior + conteúdo principal, com fundo do tema."""
    return rx.cond(
        AppState.is_logged_in,
        rx.vstack(
            rx.html(TEMA_CSS),
            navbar(),
            rx.box(
                *children,
                padding=[f"{SPACE[3]} {SPACE[3]}", f"{SPACE[3]} {SPACE[4]}", f"{SPACE[4]} {SPACE[5]}"],
                width="100%",
                max_width="1280px",
                margin="0 auto",
                padding_bottom="3rem",
            ),
            width="100%",
            spacing="0",
            min_height="100vh",
            style={"background": PAGE_BG, "font_family": "Inter, sans-serif"},
        ),
        rx.center(rx.spinner(), height="100vh"),
    )