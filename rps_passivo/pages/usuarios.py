import reflex as rx

from ..state import UsuariosState, AppState
from ..components.navbar import page_shell
from ..components.cards import card_container

VERMELHO = "#E31E24"
VERDE = "#00A651"


def _minha_senha() -> rx.Component:
    return card_container(
        rx.heading("Meu Login", size="3", margin_bottom="0.3em"),
        rx.text("Usuário: " + AppState.username, size="2", color=rx.color("gray", 10), margin_bottom="0.8em"),
        rx.heading("Alterar minha senha", size="2", margin_bottom="0.5em"),
        rx.vstack(
            rx.input(placeholder="Senha atual", type="password", value=UsuariosState.senha_atual, on_change=UsuariosState.set_senha_atual),
            rx.input(placeholder="Nova senha (mín. 6 caracteres)", type="password", value=UsuariosState.nova_senha, on_change=UsuariosState.set_nova_senha),
            rx.input(placeholder="Confirmar nova senha", type="password", value=UsuariosState.confirmar_senha, on_change=UsuariosState.set_confirmar_senha),
            rx.cond(
                UsuariosState.msg_senha != "",
                rx.callout(UsuariosState.msg_senha, color_scheme="green"),
            ),
            rx.button("Alterar Senha", on_click=UsuariosState.trocar_minha_senha, style={"background": VERMELHO, "color": "white"}),
            spacing="3",
            width="100%",
            max_width="380px",
        ),
        margin_bottom="1.2em",
    )


def _linha_usuario(u: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(u["display_name"]),
        rx.table.cell(u["username"]),
        rx.table.cell(rx.badge(u["role_label"], color_scheme="gray")),
        rx.table.cell(
            rx.cond(u["active"], rx.badge("Ativo", color_scheme="green"), rx.badge("Inativo", color_scheme="red")),
        ),
        rx.table.cell(
            rx.button(
                rx.cond(u["active"], "Desativar", "Reativar"),
                size="1", variant="soft",
                on_click=lambda: UsuariosState.alternar_ativo(u["id"]),
            ),
        ),
    )


def _gestao_usuarios() -> rx.Component:
    return rx.cond(
        AppState.role == "admin",
        rx.fragment(
            card_container(
                rx.heading("Criar Novo Login", size="3", margin_bottom="0.8em"),
                rx.vstack(
                    rx.input(placeholder="Nome de exibição", value=UsuariosState.novo_usuario_nome, on_change=UsuariosState.set_novo_usuario_nome),
                    rx.input(placeholder="Usuário (login)", value=UsuariosState.novo_usuario_username, on_change=UsuariosState.set_novo_usuario_username),
                    rx.input(placeholder="Senha (mín. 6 caracteres)", type="password", value=UsuariosState.novo_usuario_senha, on_change=UsuariosState.set_novo_usuario_senha),
                    rx.select(
                        ["operator", "viewer"],
                        value=UsuariosState.novo_usuario_role,
                        on_change=UsuariosState.set_novo_usuario_role,
                    ),
                    rx.text("operator = Operador (lança dados) · viewer = Visualizador (só consulta)", size="1", color=rx.color("gray", 9)),
                    rx.cond(
                        UsuariosState.msg_novo_usuario != "",
                        rx.callout(UsuariosState.msg_novo_usuario, color_scheme="green"),
                    ),
                    rx.button("Criar Usuário", on_click=UsuariosState.criar_usuario, style={"background": VERMELHO, "color": "white"}),
                    spacing="3",
                    width="100%",
                    max_width="380px",
                ),
                margin_bottom="1.2em",
            ),
            card_container(
                rx.heading("Todos os Usuários", size="3", margin_bottom="0.5em"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Nome"),
                            rx.table.column_header_cell("Login"),
                            rx.table.column_header_cell("Nível"),
                            rx.table.column_header_cell("Status"),
                            rx.table.column_header_cell("Ações"),
                        )
                    ),
                    rx.table.body(rx.foreach(UsuariosState.usuarios, _linha_usuario)),
                    width="100%",
                ),
            ),
        ),
    )


def usuarios_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Usuários", size="6", margin_bottom="0.3em"),
            _minha_senha(),
            _gestao_usuarios(),
            spacing="3",
            width="100%",
        ),
    )
