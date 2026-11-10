"""Tela de login: segue o tema (escuro por padrão, com opção de claro)."""
import reflex as rx

from ..state import AppState
from ..theme import (
    PRIMARY, PRIMARY_HOVER, PAGE_BG, CARD_BG, BORDER, TEXT_TITLE, TEXT_MUTED,
)


def _botao_tema() -> rx.Component:
    return rx.icon_button(
        rx.color_mode_cond(
            light=rx.icon("moon", size=18),
            dark=rx.icon("sun", size=18),
        ),
        on_click=rx.toggle_color_mode,
        variant="ghost",
        color_scheme="gray",
        size="3",
        position="fixed",
        top="1em",
        right="1em",
        title="Alternar tema claro/escuro",
    )


def login_page() -> rx.Component:
    return rx.center(
        _botao_tema(),
        rx.box(
            rx.vstack(
                rx.image(
                    src="/logo_cumani.png",
                    width="132px",
                    height="132px",
                    border_radius="50%",
                    box_shadow="0 0 0 6px rgba(220,38,38,0.10), 0 0 40px rgba(220,38,38,0.35)",
                ),
                rx.heading(
                    "Passivo Cumani",
                    size="7",
                    color=TEXT_TITLE,
                    margin_top="0.7em",
                    letter_spacing="-0.02em",
                ),
                rx.text(
                    "Gestão de custos e despesas da rede",
                    size="2",
                    color=TEXT_MUTED,
                ),
                rx.vstack(
                    rx.input(
                        placeholder="Usuário",
                        value=AppState.login_username,
                        on_change=AppState.set_login_username,
                        size="3",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Senha",
                        type="password",
                        value=AppState.login_password,
                        on_change=AppState.set_login_password,
                        size="3",
                        width="100%",
                        on_key_down=lambda k: rx.cond(k == "Enter", AppState.do_login, rx.noop()),
                    ),
                    rx.cond(
                        AppState.login_error != "",
                        rx.callout(
                            AppState.login_error,
                            icon="triangle-alert",
                            color_scheme="red",
                            size="1",
                            width="100%",
                        ),
                    ),
                    rx.button(
                        "Entrar",
                        on_click=AppState.do_login,
                        width="100%",
                        size="3",
                        style={
                            "background": PRIMARY,
                            "color": "white",
                            "font_weight": "600",
                            "_hover": {"background": PRIMARY_HOVER},
                        },
                    ),
                    spacing="3",
                    width="100%",
                    margin_top="1.6em",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            padding="2.5em",
            border_radius="20px",
            bg=CARD_BG,
            border=f"1px solid {BORDER}",
            box_shadow="0 20px 60px rgba(0,0,0,0.25)",
            width=["90vw", "400px", "400px"],
            position="relative",
            z_index="1",
        ),
        min_height="100vh",
        bg=PAGE_BG,
        style={
            "background_image": (
                "radial-gradient(circle at 50% 35%, rgba(220,38,38,0.18), transparent 55%)"
            ),
        },
    )