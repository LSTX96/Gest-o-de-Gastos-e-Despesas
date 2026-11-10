"""Componentes de interação: números flutuantes, confirmação e avisos visuais."""
import reflex as rx

from ..theme import TEXT_TITLE, TEXT_MUTED, PRIMARY

BRILHO = "0 0 18px rgba(220, 38, 38, 0.35)"


# ---------------------------------------------------------------------------
# Números grandes flutuantes
# ---------------------------------------------------------------------------
def numero_flutuante(
    titulo: str,
    valor,
    detalhe=None,
    cor: str = TEXT_TITLE,
    icone: str | None = None,
) -> rx.Component:
    """Número grande em destaque, sem card, com brilho ao passar o cursor.

    titulo: rótulo curto em cima do número
    valor: texto já formatado (ex.: "R$ 12.345,67") ou Var do estado
    detalhe: linha menor embaixo (opcional), ex.: "(R$ 9.000,00 pagos)"
    """
    cabecalho = rx.hstack(
        rx.icon(icone, size=14, color=TEXT_MUTED) if icone else rx.fragment(),
        rx.text(
            titulo,
            size="1",
            weight="medium",
            color=TEXT_MUTED,
            text_transform="uppercase",
            letter_spacing="0.08em",
        ),
        spacing="1",
        align="center",
    )
    return rx.vstack(
        cabecalho,
        rx.text(
            valor,
            font_size=["1.7rem", "2rem", "2.4rem"],
            font_weight="700",
            color=cor,
            line_height="1.1",
            letter_spacing="-0.02em",
            style={"font_variant_numeric": "tabular-nums"},
        ),
        rx.text(detalhe, size="2", color=TEXT_MUTED) if detalhe is not None else rx.fragment(),
        spacing="1",
        align="start",
        padding="0.8em 1em",
        border_radius="16px",
        cursor="default",
        transition="all 0.25s ease",
        _hover={
            "transform": "translateY(-4px) scale(1.03)",
            "background": "radial-gradient(circle at 30% 40%, rgba(220,38,38,0.08), transparent 70%)",
            "text_shadow": BRILHO,
        },
    )


def painel_numeros(*itens, colunas: str = "3") -> rx.Component:
    """Agrupa números flutuantes. Ao focar um, os demais ficam mais apagados."""
    return rx.grid(
        *itens,
        columns=rx.breakpoints(initial="1", sm="2", md=colunas),
        spacing="2",
        width="100%",
        style={
            "& > *": {"transition": "opacity 0.25s ease"},
            "&:hover > *": {"opacity": "0.45"},
            "& > *:hover": {"opacity": "1"},
        },
    )


# ---------------------------------------------------------------------------
# Confirmação antes de qualquer alteração
# ---------------------------------------------------------------------------
def confirmar(
    gatilho: rx.Component,
    titulo: str,
    mensagem,
    ao_confirmar,
    texto_confirmar: str = "Confirmar",
    cor: str = "red",
) -> rx.Component:
    """Envolve um botão: a ação só acontece depois de confirmar na janela.

    Uso: confirmar(rx.button("Excluir"), "Excluir conta?", "Ela vai para a lixeira.",
                   lambda: Estado.excluir(id))
    """
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(gatilho),
        rx.alert_dialog.content(
            rx.alert_dialog.title(titulo),
            rx.alert_dialog.description(mensagem, size="2"),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button("Cancelar", variant="soft", color_scheme="gray"),
                ),
                rx.alert_dialog.action(
                    rx.button(texto_confirmar, color_scheme=cor, on_click=ao_confirmar),
                ),
                spacing="3",
                justify="end",
                margin_top="1.2em",
            ),
            max_width="440px",
        ),
    )


# ---------------------------------------------------------------------------
# Avisos visuais (usados nos métodos do estado com `return`)
# ---------------------------------------------------------------------------
def aviso_sucesso(mensagem: str):
    """Aviso verde no topo da tela, confirmando que o dado foi gravado."""
    return rx.toast.success(mensagem, position="top-center", duration=4000)


def aviso_erro(mensagem: str):
    """Aviso vermelho no topo da tela, quando algo impede a gravação."""
    return rx.toast.error(mensagem, position="top-center", duration=6000)