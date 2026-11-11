"""Página Relatórios (parte visual). As regras ficam em relatorios_estado.py."""
import reflex as rx

from .relatorios_estado import RelatoriosState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import numero_flutuante, painel_numeros
from ..theme import (
    PRIMARY, SUCCESS, WARNING, DANGER, TEXT_TITLE, TEXT_BODY, TEXT_MUTED, BORDER, CARD_BG_2,
)

RS = RelatoriosState
AZUL = "#3B82F6"

__all__ = ["relatorios_page", "RelatoriosState"]


# ---------------------------------------------------------------------------
# Topo
# ---------------------------------------------------------------------------
def _cabecalho() -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.heading("Relatórios", size="7", letter_spacing="-0.02em", color=TEXT_TITLE),
            rx.text(
                "Indicadores, previsões e análise automática dos gastos.",
                size="2", color=TEXT_MUTED,
            ),
            spacing="1",
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                rx.icon("file-spreadsheet", size=16), "Exportar Excel",
                variant="soft", color_scheme="green", size="3",
                on_click=RS.exportar,
            ),
            rx.select.root(
                rx.select.trigger(placeholder="Loja", min_width="200px"),
                rx.select.content(
                    rx.select.item("Toda a rede", value="todas"),
                    rx.foreach(RS.lojas_opcoes, lambda x: rx.select.item(x["nome"], value=x["id"])),
                ),
                value=RS.filtro_loja,
                on_change=RS.set_filtro_loja,
                size="3",
            ),
            spacing="3",
            align="center",
            wrap="wrap",
        ),
        align="center",
        wrap="wrap",
        gap="1em",
        width="100%",
    )

def _numeros() -> rx.Component:
    return painel_numeros(
        numero_flutuante("Compromissos do mês", RS.n_mes, icone="wallet"),
        numero_flutuante("A pagar em 30 dias", RS.n_30d, cor=WARNING, icone="clock"),
        numero_flutuante("Média mensal (passado)", RS.n_media_hist, detalhe=RS.n_media_hist_label, icone="history"),
        numero_flutuante("Mês mais caro (passado)", RS.n_caro, detalhe=RS.n_caro_label, icone="trophy"),
        numero_flutuante("Média mensal prevista", RS.n_media, detalhe="Próximos 12 meses", icone="activity"),
        numero_flutuante("Mês mais carregado à frente", RS.n_pico, detalhe=RS.n_pico_label, cor=DANGER, icone="flame"),
        colunas="3",
    )


# ---------------------------------------------------------------------------
# Storytelling e observações
# ---------------------------------------------------------------------------
def _historia() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon("sparkles", size=18, color=PRIMARY),
            rx.heading("A história do mês", size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
            margin_bottom="0.6em",
        ),
        rx.vstack(
            rx.foreach(
                RS.historia,
                lambda p: rx.text(p, size="3", color=TEXT_BODY, line_height="1.75"),
            ),
            spacing="3",
            width="100%",
        ),
        padding="1.4em 1.6em",
        border_radius="18px",
        border=f"1px solid {BORDER}",
        border_left=f"4px solid {PRIMARY}",
        background="linear-gradient(135deg, rgba(220,38,38,0.08), transparent 60%)",
        width="100%",
    )


def _cor_nivel(nivel):
    return rx.match(
        nivel,
        ("alerta", DANGER),
        ("atencao", WARNING),
        ("positivo", SUCCESS),
        AZUL,
    )


def _icone_nivel(nivel) -> rx.Component:
    return rx.match(
        nivel,
        ("alerta", rx.icon("triangle-alert", size=18, color=DANGER)),
        ("atencao", rx.icon("circle-alert", size=18, color=WARNING)),
        ("positivo", rx.icon("circle-check", size=18, color=SUCCESS)),
        rx.icon("lightbulb", size=18, color=AZUL),
    )


def _rotulo_nivel(nivel) -> rx.Component:
    return rx.match(
        nivel,
        ("alerta", rx.badge("Alerta", color_scheme="red", size="1")),
        ("atencao", rx.badge("Atenção", color_scheme="orange", size="1")),
        ("positivo", rx.badge("Positivo", color_scheme="green", size="1")),
        rx.badge("Sugestão", color_scheme="blue", size="1"),
    )


def _card_insight(o) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.center(
                _icone_nivel(o["nivel"]),
                width="36px", height="36px", min_width="36px",
                border_radius="10px", bg=CARD_BG_2,
            ),
            rx.text(o["titulo"], size="3", weight="bold", color=TEXT_TITLE),
            rx.spacer(),
            _rotulo_nivel(o["nivel"]),
            align="center",
            spacing="3",
            width="100%",
        ),
        rx.text(o["texto"], size="2", color=TEXT_BODY, line_height="1.6"),
        spacing="2",
        padding="1em 1.1em",
        border_radius="14px",
        border=f"1px solid {BORDER}",
        border_left="3px solid",
        border_left_color=_cor_nivel(o["nivel"]),
        width="100%",
        transition="all 0.2s ease",
        _hover={"transform": "translateY(-2px)", "box_shadow": "0 8px 24px rgba(0,0,0,0.18)"},
    )


def _observacoes() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("brain", size=18, color=PRIMARY),
            rx.heading("Observações e sugestões", size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
        ),
        rx.text(
            "Geradas automaticamente a partir dos lançamentos. Atualizam a cada novo dado.",
            size="1", color=TEXT_MUTED,
        ),
        rx.grid(
            rx.foreach(RS.insights, _card_insight),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="3",
            width="100%",
            margin_top="0.4em",
        ),
        spacing="2",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Roscas por período
# ---------------------------------------------------------------------------
def _navegador(rotulo, anterior, proximo, atual, mostrar_atual, texto_atual: str) -> rx.Component:
    return rx.hstack(
        rx.icon_button(rx.icon("chevron-left", size=16), size="1", variant="soft", on_click=anterior),
        rx.text(rotulo, size="2", weight="bold", color=TEXT_TITLE, text_align="center", flex="1"),
        rx.icon_button(rx.icon("chevron-right", size=16), size="1", variant="soft", on_click=proximo),
        rx.cond(
            mostrar_atual,
            rx.button(texto_atual, size="1", variant="ghost", on_click=atual),
        ),
        align="center",
        spacing="2",
        width="100%",
    )


def _card_rosca(titulo: str, controles: rx.Component, figura) -> rx.Component:
    return card_container(
        rx.text(
            titulo, size="1", weight="medium", color=TEXT_MUTED,
            text_transform="uppercase", letter_spacing="0.08em",
        ),
        rx.box(controles, width="100%", margin_top="0.5em"),
        rx.plotly(data=figura, width="100%"),
    )


def _controles_geral() -> rx.Component:
    return rx.vstack(
        rx.segmented_control.root(
            rx.segmented_control.item("Este ano", value="ano"),
            rx.segmented_control.item("12 meses", value="12m"),
            rx.segmented_control.item("Tudo", value="tudo"),
            value=RS.geral_preset,
            on_change=RS.set_geral_preset,
            size="1",
            width="100%",
        ),
        rx.hstack(
            rx.input(type="date", value=RS.geral_ini, on_change=RS.set_geral_ini, size="1", width="100%"),
            rx.text("a", size="1", color=TEXT_MUTED),
            rx.input(type="date", value=RS.geral_fim, on_change=RS.set_geral_fim, size="1", width="100%"),
            align="center",
            spacing="2",
            width="100%",
        ),
        rx.text(RS.geral_label, size="1", color=TEXT_MUTED),
        spacing="2",
        width="100%",
    )


def _roscas() -> rx.Component:
    return rx.vstack(
        rx.heading("Gastos por tipo", size="4", color=TEXT_TITLE),
        rx.grid(
            _card_rosca(
                "Semana",
                _navegador(
                    RS.semana_label, RS.semana_anterior, RS.semana_proxima,
                    RS.semana_atual, RS.semana_offset != 0, "Esta semana",
                ),
                RS.fig_semana,
            ),
            _card_rosca(
                "Mês",
                _navegador(
                    RS.mes_label, RS.mes_anterior, RS.mes_proximo,
                    RS.mes_atual, RS.mes_offset != 0, "Este mês",
                ),
                RS.fig_mes,
            ),
            _card_rosca("Geral", _controles_geral(), RS.fig_geral),
            columns=rx.breakpoints(initial="1", lg="3"),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Linhas do tempo
# ---------------------------------------------------------------------------
def _linha_semanal() -> rx.Component:
    return card_container(
        rx.heading("Próximas 52 semanas", size="4", color=TEXT_TITLE),
        rx.text(
            "Vencimentos programados por semana, separando contas fixas e variáveis. "
            "Passe o cursor para ver os valores de cada semana.",
            size="1", color=TEXT_MUTED,
        ),
        rx.plotly(data=RS.fig_semanal, width="100%"),
    )


def _linha_mensal() -> rx.Component:
    return card_container(
        rx.flex(
            rx.vstack(
                rx.heading(RS.titulo_mensal, size="4", color=TEXT_TITLE),
                rx.text(
                    "Compromissos previstos por mês, separando contas fixas e variáveis.",
                    size="1", color=TEXT_MUTED,
                ),
                spacing="1",
            ),
            rx.spacer(),
            rx.segmented_control.root(
                rx.segmented_control.item("Até dezembro", value="ano"),
                rx.segmented_control.item("12 meses", value="12m"),
                value=RS.horizonte,
                on_change=RS.set_horizonte,
                size="1",
            ),
            align="center",
            wrap="wrap",
            gap="0.8em",
            width="100%",
        ),
        rx.plotly(data=RS.fig_mensal, width="100%"),
    )


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
def relatorios_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            _cabecalho(),
            _numeros(),
            _historia(),
            _observacoes(),
            _roscas(),
            _linha_semanal(),
            _linha_mensal(),
            spacing="6",
            width="100%",
        ),
    )