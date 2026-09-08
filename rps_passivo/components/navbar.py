"""Navbar / Sidebar — layout base da aplicação.

Desktop (>1024px): sidebar fixa à esquerda (260px expandida).
Mobile (<768px): sidebar vira menu hambúrguer.  Header fixo no topo (64px).
"""
from __future__ import annotations

import reflex as rx

from ..state import AppState, role_allowed, ContasPagarState, LojasState
from ..theme import (
    PRIMARY, PRIMARY_BG, PRIMARY_HOVER, TEXT_TITLE, TEXT_BODY, TEXT_MUTED,
    SIDEBAR_BG, SIDEBAR_TEXT, BORDER, CARD_BG, SHADOW, RADIUS, SPACE,
    BTN_PRIMARY,
)

# Ícone + label de cada item de navegação
NAV_ITEMS = [
    ("Dashboard", "/dashboard", "layout-dashboard", ("admin", "operator", "viewer")),
    ("Lançamentos", "/lancamentos", "square-plus", ("admin", "operator")),
    ("Contas a Pagar", "/contas-pagar", "receipt", ("admin", "operator", "viewer")),
    ("Contas Fixas", "/contas-fixas", "list-checks", ("admin", "operator", "viewer")),
    ("Relatório Semanal", "/relatorio-semanal", "calendar-days", ("admin", "operator", "viewer")),
    ("Relatório Mensal", "/relatorio-mensal", "calendar-range", ("admin", "operator", "viewer")),
    ("Lojas", "/lojas", "store", ("admin", "operator", "viewer")),
    ("Usuários", "/usuarios", "users", ("admin", "operator", "viewer")),
]

SIDEBAR_EXPANDED = 260
SIDEBAR_COLLAPSED = 72


def _sidebar_item(item) -> rx.Component:
    """Item da sidebar — ícone + label, com destaque no ativo."""
    nome = item[0]
    href = item[1]
    icone = item[2]
    roles = item[3]

    is_active = AppState.current_route == href
    return rx.cond(
        role_allowed(AppState.role, roles),
        rx.link(
            rx.hstack(
                rx.icon(icone, size=20, color=rx.cond(is_active, "white", SIDEBAR_TEXT)),
                rx.cond(
                    is_active,
                    rx.text(nome, size="2", weight="medium", color="white"),
                    rx.text(nome, size="2", weight="regular", color=SIDEBAR_TEXT),
                ),
                spacing="3",
                padding=f"{SPACE[2]} {SPACE[3]}",
                border_radius=RADIUS["sm"],
                width="100%",
                _hover={"background": "rgba(255,255,255,0.08)"},
                style=rx.cond(is_active, {"background": PRIMARY}, {}),
            ),
            href=href,
            underline="none",
        ),
    )


def sidebar() -> rx.Component:
    """Sidebar fixa à esquerda — desktop apenas."""
    return rx.box(
        rx.flex(
            # Logo
            rx.link(
                rx.hstack(
                    rx.image(src="/logo_cumani.png", width="32px", height="32px", border_radius="50%"),
                    rx.heading("Passivo Cumani", size="3", color="white", weight="bold"),
                    spacing="2", align="center",
                    padding=SPACE[3],
                ),
                href="/dashboard", underline="none", color="white",
            ),
            # Navegação
            rx.scroll_area(
                rx.vstack(
                    *[_sidebar_item(item) for item in NAV_ITEMS],
                    spacing="1", width="100%", padding=SPACE[2],
                ),
                height="100%",
            ),
            # Rodapé: avatar + logout
            rx.flex(
                rx.hstack(
                    rx.flex(
                        AppState.display_name[:1].upper(),
                        width="32px", height="32px", border_radius="50%",
                        style={"background": PRIMARY},
                        justify="center", align="center",
                        color="white", font_weight="bold", font_size="12px",
                    ),
                    rx.vstack(
                        rx.text(AppState.display_name, size="1", weight="medium", color="white"),
                        rx.text(AppState.role_label, size="1", color=SIDEBAR_TEXT),
                        spacing="0", align="start",
                    ),
                    rx.button(
                        rx.icon("log-out", size=16),
                        variant="ghost", size="1",
                        color=SIDEBAR_TEXT,
                        on_click=AppState.logout,
                        _hover={"background": "rgba(255,255,255,0.1)"},
                    ),
                    spacing="2", align="center",
                    width="100%", justify="start",
                ),
                padding=SPACE[3],
                border_top=f"1px solid {BORDER}",
            ),
            direction="column",
            height="100vh",
            width=f"{SIDEBAR_EXPANDED}px",
        ),
        position="sticky", top="0", left="0", z_index="30",
        style={"background": SIDEBAR_BG},
        display=["none", "none", "block"],
        overflow_y="auto",
    )


def _breadcrumb_label() -> rx.Component:
    """Label da página atual para o breadcrumb do header."""
    label = rx.text("Dashboard", size="2", color=TEXT_MUTED)
    for nome, href, _icone, _roles in reversed(NAV_ITEMS):
        label = rx.cond(
            AppState.current_route == href,
            rx.text(nome, size="2", color=TEXT_MUTED),
            label,
        )
    return label


def _header_action() -> rx.Component:
    """Ação contextual no header conforme a página ativa."""
    return rx.cond(
        AppState.current_route == "/contas-pagar",
        rx.button(
            rx.icon("plus", size=16), "Nova Conta",
            on_click=ContasPagarState.abrir_novo,
            style=BTN_PRIMARY,
        ),
        rx.cond(
            AppState.current_route == "/lojas",
            rx.button(
                rx.icon("plus", size=16), "Nova Loja",
                on_click=LojasState.abrir_novo,
                style=BTN_PRIMARY,
            ),
            rx.fragment(),
        ),
    )


def header() -> rx.Component:
    """Header fixo no topo — breadcrumb, ação contextual, notificações, perfil."""
    return rx.box(
        rx.hstack(
            # Breadcrumb: Passivo Cumani / Página atual
            rx.hstack(
                rx.link(
                    rx.text("Passivo Cumani", size="2", color=TEXT_MUTED),
                    href="/dashboard",
                    underline="none",
                    _hover={"color": PRIMARY},
                ),
                rx.icon("chevron-right", size=14, color=TEXT_MUTED),
                _breadcrumb_label(),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            _header_action(),
            rx.button(
                rx.icon("bell", size=18),
                variant="ghost", size="1",
                color=TEXT_BODY,
                _hover={"background": PRIMARY_BG},
            ),
            rx.hstack(
                rx.flex(
                    AppState.display_name[:1].upper(),
                    width="32px", height="32px", border_radius="50%",
                    style={"background": PRIMARY},
                    justify="center", align="center",
                    color="white", font_weight="bold", font_size="12px",
                ),
                rx.icon("chevron-down", size=16, color=TEXT_MUTED),
                spacing="2", align="center",
                display=["none", "none", "flex"],
            ),
            width="100%", align="center",
            padding=f"0 {SPACE[3]}",
            height="64px",
            box_shadow=SHADOW["sm"],
            style={"background": CARD_BG, "border-bottom": f"1px solid {BORDER}"},
        ),
        position="sticky", top="0", z_index="20", width="100%",
        display=["flex", "flex", "flex"],
    )


def page_shell(*children) -> rx.Component:
    """Layout padrão: sidebar (desktop) + conteúdo principal."""
    return rx.cond(
        AppState.is_logged_in,
        rx.box(
            rx.hstack(
                sidebar(),
                rx.box(
                    header(),
                    rx.box(
                        *children,
                        padding=[f"{SPACE[3]} {SPACE[4]}", f"{SPACE[3]} {SPACE[4]}", f"{SPACE[4]} {SPACE[5]}"],
                        width="100%",
                        max_width="1280px",
                        margin="0 auto",
                        padding_bottom="3rem",
                    ),
                    width="100%",
                ),
                width="100%",
            ),
            min_height="100vh",
            style={"background": "#F8FAFC", "font_family": "Inter, sans-serif"},
        ),
        rx.center(rx.spinner(), height="100vh"),
    )