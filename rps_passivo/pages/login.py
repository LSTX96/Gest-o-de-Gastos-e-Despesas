import reflex as rx

from ..state import AppState

VERMELHO = "#E31E24"
VERDE = "#00A651"


def login_page() -> rx.Component:
    return rx.center(
        rx.box(
            rx.vstack(
                rx.image(src="/logo_cumani.png", width="140px", height="140px", border_radius="50%"),
                rx.heading("Passivo Cumani", size="6", color="#1A1A2E", margin_top="0.5em"),
                rx.text("Controle de contas fixas e boletos da rede", size="2", color=rx.color("gray", 10)),
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
                        rx.text(AppState.login_error, color=VERMELHO, size="2"),
                    ),
                    rx.button(
                        "Entrar",
                        on_click=AppState.do_login,
                        width="100%",
                        size="3",
                        style={"background": VERMELHO, "color": "white"},
                    ),
                    spacing="3",
                    width="100%",
                    margin_top="1.5em",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            padding="2.5em",
            border_radius="18px",
            box_shadow="0 4px 24px rgba(0,0,0,0.10)",
            style={"background": "white"},
            width=["90vw", "400px", "400px"],
        ),
        min_height="100vh",
        style={"background": "linear-gradient(160deg, #FFF5F5 0%, #F0FBF6 100%)"},
    )
