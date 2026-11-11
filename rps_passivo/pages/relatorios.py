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


def _titulo_secao(icone: str, titulo: str, subtitulo: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon(icone, size=18, color=PRIMARY),
            rx.heading(titulo, size="4", color=TEXT_TITLE),
            spacing="2",
            align="center",
        ),
        rx.text(subtitulo, size="1", color=TEXT_MUTED),
        spacing="1",
        width="100%",
    )


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
        numero_flutuante("Previsão de gasto mensal", RS.n_media, detalhe=RS.n_media_detalhe, icone="activity"),
        numero_flutuante("Média mensal (passado)", RS.n_media_hist, detalhe=RS.n_media_hist_label, icone="history"),
        numero_flutuante("Mês mais caro (passado)", RS.n_caro, detalhe=RS.n_caro_label, icone="trophy"),
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
        _titulo_secao(
            "brain", "Observações e sugestões",
            "Geradas automaticamente a partir dos lançamentos. Atualizam a cada novo dado.",
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
# Saúde dos pagamentos
# ---------------------------------------------------------------------------
def _saude_pagamentos() -> rx.Component:
    return rx.vstack(
        _titulo_secao(
            "heart-pulse", "Saúde dos pagamentos",
            "Pontualidade dos últimos 6 meses e contas em atraso hoje. "
            "Marque as contas como pagas no mesmo dia do pagamento para estes números refletirem a realidade.",
        ),
        painel_numeros(
            numero_flutuante("Pago em dia", RS.n_pct_em_dia, detalhe=RS.n_pct_em_dia_detalhe, cor=SUCCESS, icone="badge-check"),
            numero_flutuante("Prazo médio de pagamento", RS.n_prazo, detalhe=RS.n_prazo_detalhe, icone="timer"),
            numero_flutuante("Total vencido", RS.n_vencido, detalhe=RS.n_vencido_detalhe, cor=DANGER, icone="hourglass"),
            colunas="3",
        ),
        card_container(
            rx.text(
                "Contas em atraso por faixa de dias", size="2", weight="bold", color=TEXT_TITLE,
            ),
            rx.cond(
                RS.n_vencido == "R$ 0,00",
                rx.hstack(
                    rx.icon("circle-check", size=18, color=SUCCESS),
                    rx.text("Nenhuma conta em atraso.", size="2", color=TEXT_BODY),
                    spacing="2",
                    align="center",
                    padding="1em 0",
                ),
                rx.plotly(data=RS.fig_aging, width="100%"),
            ),
        ),
        spacing="3",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Disciplina das lojas
# ---------------------------------------------------------------------------
def _linha_disciplina(l) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(l["loja"], weight="bold", color=TEXT_TITLE)),
        rx.table.cell(
            rx.vstack(
                rx.text(l["gasto"], size="2", color=TEXT_TITLE),
                rx.text("Limite: ", l["limite"], size="1", color=TEXT_MUTED),
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(l["uso_txt"], size="2", weight="bold", color=l["cor_hex"]),
                rx.box(
                    rx.box(
                        width=l["uso_barra"] + "%",
                        height="100%",
                        bg=l["cor_hex"],
                        border_radius="999px",
                    ),
                    width="90px",
                    height="6px",
                    bg=CARD_BG_2,
                    border_radius="999px",
                    overflow="hidden",
                ),
                spacing="1",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(l["projecao"], size="2", color=TEXT_TITLE),
                rx.text(l["projecao_txt"], size="1", color=TEXT_MUTED),
                spacing="0",
            )
        ),
        rx.table.cell(rx.text(l["estouros"], size="2", color=TEXT_BODY)),
        rx.table.cell(rx.badge(l["situacao"], color_scheme=l["cor"], size="2")),
        align="center",
    )


def _disciplina() -> rx.Component:
    return rx.vstack(
        _titulo_secao(
            "gauge", "Disciplina das lojas",
            "Projeção de fechamento = compromissos do mês + ritmo diário das despesas variáveis "
            "aplicado aos dias que faltam. No começo do mês, a projeção é menos precisa.",
        ),
        card_container(
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Loja"),
                            rx.table.column_header_cell("Gasto no mês"),
                            rx.table.column_header_cell("Uso do limite"),
                            rx.table.column_header_cell("Projeção de fechamento"),
                            rx.table.column_header_cell("Estouros (6 meses)"),
                            rx.table.column_header_cell("Situação"),
                        )
                    ),
                    rx.table.body(rx.foreach(RS.disciplina, _linha_disciplina)),
                    width="100%",
                ),
                width="100%",
                overflow_x="auto",
            ),
        ),
        spacing="3",
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
# Curva ABC e variação de gastos recorrentes
# ---------------------------------------------------------------------------
def _cor_classe(classe):
    return rx.match(classe, ("A", "red"), ("B", "amber"), "gray")


def _linha_abc(l) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.badge(l["classe"], color_scheme=_cor_classe(l["classe"]), size="2", variant="solid")),
        rx.table.cell(rx.text(l["tipo"], weight="bold", color=TEXT_TITLE)),
        rx.table.cell(rx.text(l["valor"], color=TEXT_TITLE)),
        rx.table.cell(rx.text(l["pct"], color=TEXT_BODY)),
        rx.table.cell(rx.text(l["acum"], color=TEXT_MUTED)),
        align="center",
    )


def _linha_preco(p) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(p["gasto"], weight="bold", color=TEXT_TITLE),
                rx.text(p["loja"], " · ", p["categoria"], size="1", color=TEXT_MUTED),
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(p["anterior"], size="2", color=TEXT_BODY),
                rx.text(p["mes_ant"], size="1", color=TEXT_MUTED),
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.text(p["atual"], size="2", color=TEXT_TITLE),
                rx.text(p["mes_atu"], size="1", color=TEXT_MUTED),
                spacing="0",
            )
        ),
        rx.table.cell(rx.badge(p["var_txt"], color_scheme=p["cor"], size="2")),
        align="center",
    )


def _abc_precos() -> rx.Component:
    tabela_abc = rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Classe"),
                    rx.table.column_header_cell("Tipo de gasto"),
                    rx.table.column_header_cell("Valor"),
                    rx.table.column_header_cell("% do total"),
                    rx.table.column_header_cell("% acumulado"),
                )
            ),
            rx.table.body(rx.foreach(RS.abc_linhas, _linha_abc)),
            width="100%",
        ),
        width="100%",
        max_height="360px",
        overflow_y="auto",
        overflow_x="auto",
    )
    tabela_precos = rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Gasto"),
                    rx.table.column_header_cell("Mês anterior"),
                    rx.table.column_header_cell("Último mês"),
                    rx.table.column_header_cell("Variação"),
                )
            ),
            rx.table.body(rx.foreach(RS.precos, _linha_preco)),
            width="100%",
        ),
        width="100%",
        overflow_x="auto",
    )
    return rx.vstack(
        _titulo_secao(
            "layers", "Curva ABC dos gastos",
            "Usa o mesmo período escolhido em \"Geral\", nos gastos por tipo. "
            "Classe A: cerca de 80% do gasto. B: os próximos 15%. C: o restante.",
        ),
        card_container(
            rx.cond(
                RS.tem_abc,
                rx.vstack(
                    rx.plotly(data=RS.fig_abc, width="100%"),
                    rx.hstack(
                        rx.icon("lightbulb", size=16, color=PRIMARY, min_width="16px", margin_top="3px"),
                        rx.text(RS.abc_texto, size="2", color=TEXT_BODY, line_height="1.6"),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    tabela_abc,
                    spacing="3",
                    width="100%",
                ),
                rx.text("Não há gastos no período escolhido.", size="2", color=TEXT_MUTED),
            ),
        ),
        _titulo_secao(
            "trending-up", "Variação de gastos recorrentes",
            "Compara os dois últimos meses em que cada gasto apareceu, por loja. Em contas fixas, "
            "mostra mudança de preço; em despesas variáveis, mudança de volume e preço juntos.",
        ),
        card_container(
            rx.cond(
                RS.tem_precos,
                tabela_precos,
                rx.text(
                    "Ainda não há gastos recorrentes com dois meses de histórico para comparar.",
                    size="2", color=TEXT_MUTED,
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Linhas do tempo e suas análises
# ---------------------------------------------------------------------------
def _chip_destaque(dq) -> rx.Component:
    cor = rx.match(
        dq["tipo"],
        ("pico", DANGER),
        ("alerta", WARNING),
        ("leve", SUCCESS),
        AZUL,
    )
    return rx.vstack(
        rx.text(
            dq["rotulo"], size="1", color=TEXT_MUTED,
            text_transform="uppercase", letter_spacing="0.06em",
        ),
        rx.text(dq["valor"], size="4", weight="bold", color=cor),
        rx.text(dq["detalhe"], size="1", color=TEXT_BODY),
        spacing="0",
        align="start",
        padding="0.7em 0.9em",
        border_radius="12px",
        bg=CARD_BG_2,
        border_top="3px solid",
        border_top_color=cor,
        width="100%",
        transition="all 0.2s ease",
        _hover={"transform": "translateY(-2px)"},
    )


def _resumo_serie(texto, destaques) -> rx.Component:
    return rx.vstack(
        rx.grid(
            rx.foreach(destaques, _chip_destaque),
            columns=rx.breakpoints(initial="2", md="4"),
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.icon("lightbulb", size=16, color=PRIMARY, min_width="16px", margin_top="3px"),
            rx.text(texto, size="2", color=TEXT_BODY, line_height="1.6"),
            spacing="2",
            align="start",
            width="100%",
        ),
        spacing="3",
        width="100%",
        margin_top="0.6em",
    )


def _linha_semanal() -> rx.Component:
    return card_container(
        rx.flex(
            rx.vstack(
                rx.heading(RS.titulo_semanal, size="4", color=TEXT_TITLE),
                rx.text(
                    "Vencimentos de cada semana do ano, separando contas fixas e variáveis. "
                    "A linha tracejada marca a semana de hoje.",
                    size="1", color=TEXT_MUTED,
                ),
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevron-left", size=16), size="2", variant="soft",
                    on_click=RS.ano_semanal_anterior,
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=16), size="2", variant="soft",
                    on_click=RS.ano_semanal_proximo,
                ),
                rx.cond(
                    RS.ano_semanal_offset != 0,
                    rx.button("Ano atual", size="2", variant="ghost", on_click=RS.ano_semanal_atual),
                ),
                spacing="2",
                align="center",
            ),
            align="center",
            wrap="wrap",
            gap="0.8em",
            width="100%",
        ),
        rx.plotly(data=RS.fig_semanal, width="100%"),
        _resumo_serie(RS.analise_semanal, RS.destaques_semanal),
    )


def _linha_futuro() -> rx.Component:
    return card_container(
        rx.vstack(
            rx.heading(RS.titulo_futuro, size="4", color=TEXT_TITLE),
            rx.text(
                "Somente o que ainda falta pagar, semana a semana. O gráfico vai até a última "
                "conta em aberto, no máximo 52 semanas à frente.",
                size="1", color=TEXT_MUTED,
            ),
            spacing="1",
            width="100%",
        ),
        rx.cond(RS.tem_futuro, rx.plotly(data=RS.fig_futuro, width="100%")),
        _resumo_serie(RS.analise_futuro, RS.destaques_futuro),
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
        _resumo_serie(RS.analise_mensal, RS.destaques_mensal),
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
            _saude_pagamentos(),
            _disciplina(),
            _roscas(),
            _abc_precos(),
            _linha_semanal(),
            _linha_futuro(),
            _linha_mensal(),
            spacing="6",
            width="100%",
        ),
    )