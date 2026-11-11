"""Página inicial (Menu Inicial). As regras ficam em inicio_estado.py."""
import reflex as rx

from .inicio_estado import InicioState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import numero_flutuante, painel_numeros
from ..theme import (
    PRIMARY, SUCCESS, WARNING, DANGER, TEXT_TITLE, TEXT_MUTED, BORDER, CARD_BG, CARD_BG_2,
)

IS = InicioState

BRILHO_HOVER = "0 0 0 1px rgba(220,38,38,0.35), 0 10px 28px rgba(220,38,38,0.16)"

MENU_BOTOES = [
    ("Lançamentos", "/lancamentos", "square-plus", "Lançar despesas e contas fixas"),
    ("Contas", "/contas", "receipt", "Todas as contas, por vencimento"),
    ("Lojas", "/lojas", "store", "Gerenciar lojas e limites"),
    ("Relatório Semanal", "/relatorio-semanal", "calendar-days", "Acompanhamento por semana"),
    ("Relatório Mensal", "/relatorio-mensal", "calendar-range", "Acompanhamento por mês"),
    ("Usuários", "/usuarios", "users", "Gerenciar acessos"),
]


# ---------------------------------------------------------------------------
# Topo
# ---------------------------------------------------------------------------
def _cabecalho() -> rx.Component:
    return rx.vstack(
        rx.heading(IS.saudacao, size="7", letter_spacing="-0.02em", color=TEXT_TITLE),
        rx.text(IS.data_hoje, size="2", color=TEXT_MUTED),
        spacing="1",
    )


def _numeros() -> rx.Component:
    return painel_numeros(
        numero_flutuante("Gasto do mês", IS.n_gasto_mes, icone="wallet"),
        numero_flutuante("Gasto acumulado total", IS.n_acumulado, detalhe=IS.n_acumulado_pago, icone="landmark"),
        numero_flutuante("Contas fixas no mês", IS.n_fixas, icone="repeat"),
        numero_flutuante("Gastos variados no mês", IS.n_variaveis, icone="shuffle"),
        colunas="4",
    )


# ---------------------------------------------------------------------------
# Situação das lojas (nomes clicáveis)
# ---------------------------------------------------------------------------
def _chip_excedida(l) -> rx.Component:
    return rx.link(
        rx.badge(
            l["nome"], " · +", l["excesso"],
            color_scheme="red", size="2", variant="soft",
            _hover={"filter": "brightness(1.25)"},
        ),
        href="/contas?loja=" + l["id"],
        underline="none",
    )


def _chip_dentro(l) -> rx.Component:
    return rx.link(
        rx.badge(
            l["nome"], color_scheme="green", size="2", variant="soft",
            _hover={"filter": "brightness(1.25)"},
        ),
        href="/contas?loja=" + l["id"],
        underline="none",
    )


def _chip_sem_limite(l) -> rx.Component:
    return rx.link(
        rx.badge(l["nome"], color_scheme="gray", size="1", variant="soft"),
        href="/contas?loja=" + l["id"],
        underline="none",
    )


def _bloco_lojas(titulo: str, icone: str, cor: str, quantidade, chips, detalhe) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon(icone, size=14, color=TEXT_MUTED),
            rx.text(
                titulo, size="1", weight="medium", color=TEXT_MUTED,
                text_transform="uppercase", letter_spacing="0.08em",
            ),
            spacing="1",
            align="center",
        ),
        rx.text(
            quantidade, font_size=["1.7rem", "2rem", "2.4rem"], font_weight="700",
            color=cor, line_height="1.1",
        ),
        rx.text(detalhe, size="2", color=TEXT_MUTED),
        rx.flex(chips, wrap="wrap", gap="0.4em", margin_top="0.3em"),
        spacing="1",
        align="start",
        padding="0.8em 1em",
        border_radius="16px",
        transition="all 0.25s ease",
        _hover={
            "transform": "translateY(-4px)",
            "background": "radial-gradient(circle at 30% 40%, rgba(220,38,38,0.08), transparent 70%)",
        },
    )


def _situacao_lojas() -> rx.Component:
    return rx.vstack(
        painel_numeros(
            _bloco_lojas(
                "Lojas excedidas", "circle-alert", DANGER,
                IS.lojas_excedidas.length().to_string(),
                rx.foreach(IS.lojas_excedidas, _chip_excedida),
                IS.n_excedente,
            ),
            _bloco_lojas(
                "Lojas dentro do limite", "circle-check", SUCCESS,
                IS.lojas_dentro.length().to_string(),
                rx.foreach(IS.lojas_dentro, _chip_dentro),
                "Clique em uma loja para ver as contas dela",
            ),
            colunas="2",
        ),
        rx.cond(
            IS.lojas_sem_limite.length() > 0,
            rx.hstack(
                rx.text("Sem limite cadastrado:", size="1", color=TEXT_MUTED),
                rx.foreach(IS.lojas_sem_limite, _chip_sem_limite),
                spacing="2",
                align="center",
                wrap="wrap",
                padding_left="1em",
            ),
        ),
        spacing="2",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Alertas de vencimento
# ---------------------------------------------------------------------------
def _alerta(icone: str, cor: str, titulo, valor, ativo) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.center(
                rx.icon(icone, size=20, color=cor),
                width="42px", height="42px", min_width="42px",
                border_radius="12px", bg=CARD_BG_2,
            ),
            rx.vstack(
                rx.text(titulo, size="2", weight="bold", color=TEXT_TITLE),
                rx.text(valor, size="2", color=TEXT_MUTED),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.icon("chevron-right", size=18, color=TEXT_MUTED),
            align="center",
            spacing="3",
            width="100%",
            padding="0.9em 1em",
            border_radius="14px",
            border=rx.cond(ativo, f"1px solid {cor}", f"1px solid {BORDER}"),
            transition="all 0.2s ease",
            _hover={"transform": "translateY(-2px)", "box_shadow": BRILHO_HOVER},
        ),
        href="/contas",
        underline="none",
        width="100%",
    )


def _alertas() -> rx.Component:
    return rx.grid(
        _alerta(
            "triangle-alert", DANGER,
            rx.cond(IS.qtd_vencidas > 0, IS.qtd_vencidas.to_string() + " conta(s) vencida(s)", "Nenhuma conta vencida"),
            rx.cond(IS.qtd_vencidas > 0, "Total de " + IS.valor_vencidas, "Tudo em dia"),
            IS.qtd_vencidas > 0,
        ),
        _alerta(
            "bell", WARNING,
            rx.cond(IS.qtd_proximas > 0, IS.qtd_proximas.to_string() + " conta(s) vencem em até 5 dias", "Nada vence nos próximos 5 dias"),
            rx.cond(IS.qtd_proximas > 0, "Total de " + IS.valor_proximas, "Sem vencimentos próximos"),
            IS.qtd_proximas > 0,
        ),
        columns=rx.breakpoints(initial="1", md="2"),
        spacing="3",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Acesso rápido
# ---------------------------------------------------------------------------
def _botao_menu(item) -> rx.Component:
    nome, href, icone, desc = item
    return rx.link(
        rx.vstack(
            rx.icon(icone, size=28, color=PRIMARY),
            rx.text(nome, size="3", weight="bold", color=TEXT_TITLE),
            rx.text(desc, size="1", color=TEXT_MUTED, text_align="center"),
            spacing="2",
            align="center",
            justify="center",
            padding="1.4em 1em",
            border_radius="14px",
            bg=CARD_BG_2,
            border=f"1px solid {BORDER}",
            transition="all 0.2s ease",
            _hover={"border_color": PRIMARY, "box_shadow": BRILHO_HOVER, "transform": "translateY(-3px)"},
            height="100%",
        ),
        href=href,
        underline="none",
        width="100%",
    )


def _menu_botoes() -> rx.Component:
    return card_container(
        rx.heading("Acesso Rápido", size="3", margin_bottom="0.8em"),
        rx.grid(
            *[_botao_menu(item) for item in MENU_BOTOES],
            columns=rx.breakpoints(initial="2", md="3"),
            spacing="3",
            width="100%",
        ),
    )


# ---------------------------------------------------------------------------
# Cards das lojas
# ---------------------------------------------------------------------------
def _badge_loja(status) -> rx.Component:
    return rx.match(
        status,
        ("excedida", rx.badge("Excedida", color_scheme="red", size="1")),
        ("alerta", rx.badge("Atenção", color_scheme="orange", size="1")),
        ("sem_limite", rx.badge("Sem limite", color_scheme="gray", size="1")),
        rx.badge("Dentro do limite", color_scheme="green", size="1"),
    )


def _mini(titulo: str, valor, cor: str) -> rx.Component:
    return rx.vstack(
        rx.text(titulo, size="1", color=TEXT_MUTED),
        rx.text(valor, size="2", weight="bold", color=cor),
        spacing="0",
        align="start",
        padding="0.5em 0.7em",
        border_radius="10px",
        bg=CARD_BG_2,
        width="100%",
    )


def _card_loja(l) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(
                    rx.text(l["inicial"], weight="bold", color="white"),
                    width="40px", height="40px", min_width="40px",
                    border_radius="50%", bg=l["cor"],
                ),
                rx.vstack(
                    rx.link(
                        rx.text(l["nome"], weight="bold", size="3", color=TEXT_TITLE),
                        href="/lojas/" + l["id"],
                        underline="none",
                    ),
                    rx.text("Limite: ", l["limite"], size="1", color=TEXT_MUTED),
                    spacing="0",
                    align="start",
                    min_width="0",
                ),
                rx.spacer(),
                _badge_loja(l["status"]),
                width="100%",
                align="center",
            ),
            rx.box(
                rx.box(
                    width=l["pct_barra"] + "%",
                    height="100%",
                    bg=l["barra_cor"],
                    border_radius="999px",
                    transition="width 0.6s ease",
                ),
                width="100%",
                height="8px",
                bg=CARD_BG_2,
                border_radius="999px",
                overflow="hidden",
            ),
            rx.hstack(
                rx.text(l["gasto"], weight="bold", size="4", color=TEXT_TITLE),
                rx.spacer(),
                rx.text(l["pct_txt"], size="2", weight="bold", color=l["barra_cor"]),
                width="100%",
                align="baseline",
            ),
            rx.grid(
                _mini("Pago", l["pago"], SUCCESS),
                _mini("Falta pagar", l["falta"], WARNING),
                columns="2",
                spacing="2",
                width="100%",
            ),
            rx.hstack(
                rx.link(rx.button("Ver contas", size="1", variant="soft"), href="/contas?loja=" + l["id"]),
                rx.link(rx.button("Detalhes", size="1", variant="ghost"), href="/lojas/" + l["id"]),
                spacing="2",
            ),
            spacing="3",
            width="100%",
        ),
        padding="1.1em",
        border_radius="16px",
        bg=CARD_BG,
        border=f"1px solid {BORDER}",
        transition="all 0.2s ease",
        _hover={"border_color": PRIMARY, "transform": "translateY(-3px)", "box_shadow": BRILHO_HOVER},
    )


def _lojas() -> rx.Component:
    return rx.vstack(
        rx.heading("Lojas", size="4", color=TEXT_TITLE),
        rx.grid(
            rx.foreach(IS.lojas_cards, _card_loja),
            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Gráfico e atividade
# ---------------------------------------------------------------------------
def _grafico_limites() -> rx.Component:
    return card_container(
        rx.heading("Uso do limite mensal por loja", size="3"),
        rx.text("A linha tracejada marca 100% do limite.", size="1", color=TEXT_MUTED, margin_bottom="0.4em"),
        rx.plotly(data=IS.figura_limites, width="100%"),
    )


def _linha_atividade(a) -> rx.Component:
    return rx.hstack(
        rx.icon("activity", size=16, color=TEXT_MUTED),
        rx.vstack(
            rx.text(a["acao"], size="2", weight="bold", color=TEXT_TITLE),
            rx.text(a["descricao"], size="1", color=TEXT_MUTED),
            spacing="0",
            align="start",
            min_width="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(a["usuario"], size="1", color=TEXT_MUTED),
            rx.text(a["quando"], size="1", color=TEXT_MUTED),
            spacing="0",
            align="end",
        ),
        width="100%",
        align="center",
        padding="0.6em 0",
        border_bottom=f"1px solid {BORDER}",
    )


def _atividade() -> rx.Component:
    return card_container(
        rx.heading("Atividade recente", size="3", margin_bottom="0.4em"),
        rx.cond(
            IS.atividade.length() == 0,
            rx.text("Nenhuma atividade registrada.", size="2", color=TEXT_MUTED),
            rx.vstack(rx.foreach(IS.atividade, _linha_atividade), spacing="0", width="100%"),
        ),
    )


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
def dashboard_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            _cabecalho(),
            _numeros(),
            _situacao_lojas(),
            _alertas(),
            _menu_botoes(),
            _lojas(),
            rx.grid(
                _grafico_limites(),
                _atividade(),
                columns=rx.breakpoints(initial="1", lg="2"),
                spacing="4",
                width="100%",
            ),
            spacing="6",
            width="100%",
        ),
    )