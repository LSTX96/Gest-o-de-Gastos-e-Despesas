"""Página Usuários: troca da própria senha e gestão de logins (administrador)."""
import reflex as rx

from ..state import UsuariosState, AppState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import confirmar
from ..theme import PRIMARY, PRIMARY_HOVER, TEXT_TITLE, TEXT_MUTED, BORDER

US = UsuariosState
BOTAO_PRIMARIO = {"background": PRIMARY, "color": "white", "_hover": {"background": PRIMARY_HOVER}}


def _mensagem(texto) -> rx.Component:
    """Verde quando a mensagem fala em sucesso; vermelho nos demais casos."""
    return rx.cond(
        texto != "",
        rx.callout(
            texto,
            color_scheme=rx.cond(texto.contains("sucesso"), "green", "red"),
            size="1",
            width="100%",
        ),
    )


def _campo(rotulo: str, componente: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.text(rotulo, size="2", weight="medium", color=TEXT_TITLE),
        componente,
        spacing="1",
        width="100%",
    )


def _minha_senha() -> rx.Component:
    return card_container(
        rx.hstack(
            rx.icon("key-round", size=18, color=PRIMARY),
            rx.heading("Meu login", size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
        ),
        rx.text("Usuário: ", AppState.username, size="2", color=TEXT_MUTED, margin_bottom="0.8em"),
        rx.vstack(
            _campo("Senha atual", rx.input(type="password", value=US.senha_atual, on_change=US.set_senha_atual, size="3", width="100%")),
            _campo("Nova senha (mín. 6 caracteres)", rx.input(type="password", value=US.nova_senha, on_change=US.set_nova_senha, size="3", width="100%")),
            _campo("Confirmar nova senha", rx.input(type="password", value=US.confirmar_senha, on_change=US.set_confirmar_senha, size="3", width="100%")),
            _mensagem(US.msg_senha),
            rx.button("Alterar senha", on_click=US.trocar_minha_senha, size="3", style=BOTAO_PRIMARIO),
            spacing="3",
            width="100%",
            max_width="420px",
        ),
    )


def _novo_usuario() -> rx.Component:
    return card_container(
        rx.hstack(
            rx.icon("user-plus", size=18, color=PRIMARY),
            rx.heading("Criar novo login", size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
            margin_bottom="0.6em",
        ),
        rx.vstack(
            _campo("Nome de exibição", rx.input(value=US.novo_usuario_nome, on_change=US.set_novo_usuario_nome, size="3", width="100%")),
            _campo("Usuário (login)", rx.input(value=US.novo_usuario_username, on_change=US.set_novo_usuario_username, size="3", width="100%")),
            _campo("Senha (mín. 6 caracteres)", rx.input(type="password", value=US.novo_usuario_senha, on_change=US.set_novo_usuario_senha, size="3", width="100%")),
            _campo(
                "Nível de acesso",
                rx.select.root(
                    rx.select.trigger(width="100%"),
                    rx.select.content(
                        rx.select.item("Operador: lança e paga contas", value="operator"),
                        rx.select.item("Visualizador: só consulta", value="viewer"),
                    ),
                    value=US.novo_usuario_role,
                    on_change=US.set_novo_usuario_role,
                    size="3",
                ),
            ),
            _mensagem(US.msg_novo_usuario),
            rx.button("Criar usuário", on_click=US.criar_usuario, size="3", style=BOTAO_PRIMARIO),
            spacing="3",
            width="100%",
            max_width="420px",
        ),
    )


def _linha_usuario(u: dict) -> rx.Component:
    botao = rx.button(
        rx.cond(u["active"], "Desativar", "Reativar"),
        size="1",
        variant="soft",
        color_scheme=rx.cond(u["active"], "red", "green"),
    )
    return rx.table.row(
        rx.table.cell(rx.text(u["display_name"], weight="bold", color=TEXT_TITLE)),
        rx.table.cell(u["username"]),
        rx.table.cell(rx.badge(u["role_label"], color_scheme="gray")),
        rx.table.cell(
            rx.cond(u["active"], rx.badge("Ativo", color_scheme="green"), rx.badge("Inativo", color_scheme="red")),
        ),
        rx.table.cell(
            rx.cond(
                u["id"] == AppState.user_id,
                rx.text("você", size="1", color=TEXT_MUTED),
                confirmar(
                    botao,
                    "Alterar o acesso deste usuário?",
                    "Usuário desativado não consegue entrar no sistema. Você pode reativar depois.",
                    lambda: US.alternar_ativo(u["id"]),
                    texto_confirmar="Confirmar",
                    cor="red",
                ),
            ),
        ),
    )


def _lista_usuarios() -> rx.Component:
    return card_container(
        rx.hstack(
            rx.icon("users", size=18, color=PRIMARY),
            rx.heading("Todos os usuários", size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
            margin_bottom="0.4em",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Nome"),
                        rx.table.column_header_cell("Login"),
                        rx.table.column_header_cell("Nível"),
                        rx.table.column_header_cell("Situação"),
                        rx.table.column_header_cell("Ações"),
                    )
                ),
                rx.table.body(rx.foreach(US.usuarios, _linha_usuario)),
                width="100%",
            ),
            width="100%",
            overflow_x="auto",
        ),
    )


def usuarios_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.vstack(
                rx.heading("Usuários", size="7", letter_spacing="-0.02em", color=TEXT_TITLE),
                rx.text("Seu acesso e, para o administrador, os logins da equipe.", size="2", color=TEXT_MUTED),
                spacing="1",
            ),
            rx.grid(
                _minha_senha(),
                rx.cond(AppState.role == "admin", _novo_usuario()),
                columns=rx.breakpoints(initial="1", lg="2"),
                spacing="4",
                width="100%",
            ),
            rx.cond(AppState.role == "admin", _lista_usuarios()),
            spacing="5",
            width="100%",
        ),
    )