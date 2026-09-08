"""Cards reutilizáveis: KPI, container de card e alertas.

Redesenho Enterprise: KPI cards com círculo de ícone colorido, números tabulares
e rodapé com variação vs mês anterior.
"""
import reflex as rx

from ..theme import (
    CARD_BG, BORDER, SHADOW, RADIUS, SPACE,
    PRIMARY, SUCCESS, WARNING, DANGER,
    TEXT_BODY, TEXT_MUTED, TEXT_TITLE,
    MONETARIO_TIPO, CARD_STYLE,
)


def kpi_card(
    titulo: str,
    valor: str,
    icone: str,
    cor: str = PRIMARY,
    variacao: str = "",
    variacao_positiva: bool = True,
) -> rx.Component:
    """Card de KPI com círculo de ícone, valor em destaque e rodapé de variação.

    Args:
        titulo: Rótulo do card (ex: "Total do Mês")
        valor: Valor exibido (ex: "R$ 12.345,67")
        icone: Nome do ícone do Lucide
        cor: Cor de fundo do círculo do ícone
        variacao: Texto da variação (ex: "+5,2% vs mês anterior")
        variacao_positiva: Se True, exibe em verde; se False, em vermelho.
    """
    var_cor = SUCCESS if variacao_positiva else DANGER
    return rx.box(
        rx.hstack(
            # Círculo de ícone
            rx.flex(
                rx.icon(icone, size=20, color="white"),
                width="40px",
                height="40px",
                border_radius="50%",
                style={"background": cor},
                justify="center",
                align="center",
            ),
            rx.vstack(
                rx.text(titulo, size="1", color=TEXT_MUTED, text_transform="uppercase",
                        letter_spacing="0.05em", weight="medium"),
                rx.heading(valor, size="5", color=TEXT_TITLE,
                           style=MONETARIO_TIPO),
                rx.cond(
                    variacao != "",
                    rx.hstack(
                        rx.icon(
                            "trending-up" if variacao_positiva else "trending-down",
                            size=12,
                            color=var_cor,
                        ),
                        rx.text(variacao, size="1", color=var_cor, weight="medium"),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                spacing="1",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        **CARD_STYLE, # Mantido o estilo padrão do tema, que já gerencia o espaçamento correto
        width="100%",
    )


def card_container(*children, **props) -> rx.Component:
    """Container de card branco com sombra sutil e border-radius."""
    return rx.box(
        *children,
        padding=SPACE[4],
        border_radius=RADIUS["md"],
        style={"background": CARD_BG},
        box_shadow=SHADOW["DEFAULT"],
        border=f"1px solid {BORDER}",
        width="100%",
        **props,
    )


def alert_card(
    titulo: str,
    icone: str = "triangle-alert",
    cor_fundo: str = "#FFFBEB",
    cor_icone: str = WARNING,
) -> rx.Component:
    """Card de alerta com ícone e título — usado no banner de vencimentos."""
    return rx.box(
        rx.hstack(
            rx.flex(
                rx.icon(icone, size=18, color=cor_icone),
                width="32px",
                height="32px",
                border_radius="50%",
                style={"background": cor_fundo},
                justify="center",
                align="center",
            ),
            rx.heading(titulo, size="3", color=TEXT_TITLE, weight="medium"), # Corrigido peso para string válida
            spacing="3",
            align="center",
        ),
        padding=f"{SPACE[3]} {SPACE[4]}",
        border_radius=RADIUS["md"], # Corrigido de .md para ["md"]
        style={"background": cor_fundo},
        border=f"1px solid {BORDER}",
        width="100%",
    )
