"""Componente StoreAvatar — mostra a logo da loja ou um avatar com iniciais."""
import reflex as rx

TAMANHOS = {"xs": "24px", "sm": "32px", "md": "48px", "lg": "80px", "xl": "120px"}
FONTE = {"xs": "9px", "sm": "12px", "md": "16px", "lg": "26px", "xl": "40px"}


def store_avatar(
    name: str,
    logo_b64: str = "",
    iniciais: str = "",
    cor: str = "#E31E24",
    tamanho: str = "md",
) -> rx.Component:
    px = TAMANHOS.get(tamanho, TAMANHOS["md"])
    font_px = FONTE.get(tamanho, FONTE["md"])
    return rx.box(
        rx.cond(
            logo_b64 != "",
            rx.image(
                src=logo_b64,
                width=px,
                height=px,
                object_fit="cover",
                border_radius="50%",
                box_shadow="0 1px 4px rgba(0,0,0,0.15)",
            ),
            rx.flex(
                rx.text(iniciais, color="white", font_weight="700", font_size=font_px),
                width=px,
                height=px,
                border_radius="50%",
                align="center",
                justify="center",
                style={"background": cor},
                box_shadow="0 1px 4px rgba(0,0,0,0.15)",
            ),
        ),
        title=name,
        transition="opacity 200ms ease-in-out",
    )
