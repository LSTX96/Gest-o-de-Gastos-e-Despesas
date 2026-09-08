"""Página de gerenciamento de lojas e limites mensais."""
import reflex as rx

from ..state import LojasState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.store_avatar import store_avatar
from ..components.var_utils import vstr
from ..theme import SUCCESS, WARNING, DANGER, SURFACE, TEXT_MUTED

VERMELHO = "#E31E24"


def _barra_progresso(loja: dict) -> rx.Component:
    """Barra de uso do limite mensal: verde < 80%, âmbar 80–100%, vermelho > 100%."""
    # Convertemos o percentual para Var numérica nativa do Reflex
    pct = rx.Var.create(loja["percentual"]).to(int)
    
    cor_barra = rx.cond(
        pct >= 100,
        "red",
        rx.cond(pct >= 80, "amber", "green"),
    )
    
    return rx.vstack(
        rx.hstack(
            rx.text("Uso do limite mensal", size="1", color=TEXT_MUTED),
            rx.spacer(),
            rx.text(vstr(loja["percentual"]) + "%", size="1", weight="bold", color=DANGER),
            width="100%",
        ),
        # Substitui os rx.box manuais por um componente nativo que não quebra tipos CSS
        rx.progress(
            value=pct,
            color_scheme=cor_barra,
            size="2",
            width="100%",
        ),
        rx.cond(
            loja["excedido"],
            rx.text(
                f"Excedido: {loja['gasto_mes']} / {loja['limite_mensal']}",
                size="1", color=DANGER, weight="medium",
            ),
            rx.text(
                f"Disponível: {loja['restante']}", 
                size="1", color=SUCCESS,
            ),
        ),
        width="100%",
        spacing="1",
    )




def _card_loja(loja: dict) -> rx.Component:
    """Card moderno que exibe as informações e consumo de limite de uma loja."""
    return card_container(
        rx.vstack(
            rx.hstack(
                store_avatar(loja["nome"]),
                rx.vstack(
                    rx.heading(loja["nome"], size="3", weight="bold"),
                    rx.text(f"Limite: {loja['limite_mensal']}", size="1", color=TEXT_MUTED),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                spacing="3",
                align="center",
                width="100%",
            ),
            _barra_progresso(loja),
            spacing="4",
            width="100%",
        )
    )


def lojas_page() -> rx.Component:
    """Estrutura principal da página de Lojas com Grid Responsivo."""
    return page_shell(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Lojas e Limites", size="6", weight="bold"),
                    rx.text("Monitore o teto de gastos e limites de crédito por filial", size="2", color=TEXT_MUTED),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
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
