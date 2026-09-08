"""Componente SemaforoBadge — círculo colorido com tooltip de dias restantes."""
import reflex as rx

TAMANHOS = {"sm": "8px", "md": "12px", "lg": "20px"}


def semaforo_badge(cor: str, texto_tooltip: str, tamanho: str = "md") -> rx.Component:
    px = TAMANHOS.get(tamanho, TAMANHOS["md"])
    cor_str = rx.Var.create(cor).to(str)
    return rx.tooltip(
        rx.box(
            width=px,
            height=px,
            border_radius="50%",
            style={"background": cor, "boxShadow": "0 0 0 3px " + cor_str + "22"},
            display="inline-block",
        ),
        content=texto_tooltip,
    )


def semaforo_com_texto(cor: str, texto_status: str) -> rx.Component:
    return rx.hstack(
        semaforo_badge(cor, texto_status, "md"),
        rx.text(texto_status, size="2", color=rx.color("gray", 11)),
        spacing="2",
        align="center",
    )
