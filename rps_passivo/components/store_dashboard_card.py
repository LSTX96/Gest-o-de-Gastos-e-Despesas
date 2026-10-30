"""Card de loja no Dashboard (Menu Inicial) — itens 4, 10, 14, 15.

Exibe os campos na seguinte ordem:
1. Nome da loja
2. Gasto acumulado (total gasto no mês/período atual)
3. Limite mensal (com tooltip explicativo — item 14)
4. Limite por Caixa (cash_limit)
5. A vencer este mês
6. Já pago no mês (item 10, clicável -> filtro "pagas")
7. Falta pagar (item 10, clicável -> filtro "pendentes")

O card inteiro é clicável -> /contas-pagar com filtro de loja (item 4).
"""
from __future__ import annotations

import reflex as rx

from ..state import AppState, EditarLimitesState, role_allowed
from ..theme import (
    DANGER,
    SUCCESS,
    TEXT_TITLE, TEXT_BODY, TEXT_MUTED,
    BORDER, CARD_BG, SHADOW, RADIUS, SPACE,
)
from .store_avatar import store_avatar
from .var_utils import vstr


def store_dashboard_card(
    loja_id: int,
    loja_name: str,
    avatar_color: str,
    logo_b64: str,
    gasto_acumulado,
    monthly_limit,
    cash_limit,
    a_vencer_mes,
    pago_mes,
    falta_pagar,
    percentual_limite,
    esta_no_limite,
    esta_excedida,
) -> rx.Component:
    """Card completo de uma loja no Menu Inicial."""
    return rx.link(
        rx.box(
            rx.vstack(
                store_avatar(
                    name=loja_name,
                    logo_b64=logo_b64,
                    iniciais="",
                    cor=avatar_color,
                    tamanho="md",
                ),
                rx.text(loja_name, size="3", weight="bold", color=TEXT_TITLE),
                rx.spacer(),
                rx.cond(
                    esta_excedida,
                    rx.badge("Excedida", color_scheme="red", size="1"),
                    rx.cond(
                        esta_no_limite,
                        rx.badge("No limite", color_scheme="orange", size="1"),
                        rx.badge("OK", color_scheme="green", size="1"),
                    ),
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.separator(color=BORDER, margin_y=SPACE[2]),
            # 2. Gasto acumulado
            rx.hstack(
                rx.text("Gasto Acumulado", size="1", color=TEXT_MUTED,
                        text_transform="uppercase"),
                rx.spacer(),
                rx.text(vstr(gasto_acumulado), size="2", weight="bold", color=TEXT_TITLE),
                width="100%",
                justify="between",
            ),
            # 3. Limite mensal (item 14 — tooltip)
            rx.hstack(
                rx.tooltip(
                    rx.text("Limite Mensal ⓘ", size="1", color=TEXT_MUTED,
                            text_transform="uppercase"),
                    content="Teto de gastos do mês para esta loja (boletos + contas fixas).",
                ),
                rx.spacer(),
                rx.text(vstr(monthly_limit), size="2", weight="medium", color=TEXT_BODY),
                width="100%",
                justify="between",
            ),
            # 4. Limite por Caixa (item 14 — tooltip)
            rx.hstack(
                rx.tooltip(
                    rx.text("Limite por Caixa ⓘ", size="1", color=TEXT_MUTED,
                            text_transform="uppercase"),
                    content="Limite para pagamentos em dinheiro (cash).",
                ),
                rx.spacer(),
                rx.text(vstr(cash_limit), size="2", weight="medium", color=TEXT_BODY),
                width="100%",
                justify="between",
            ),
            rx.separator(color=BORDER, margin_y=SPACE[2]),
            # 5. A vencer este mês
            rx.hstack(
                rx.text("A Vencer Este Mês", size="1", color=TEXT_MUTED,
                        text_transform="uppercase"),
                rx.spacer(),
                rx.text(vstr(a_vencer_mes), size="2", weight="bold", color=DANGER),
                width="100%",
                justify="between",
            ),
            # 6/7. Pago e falta pagar (item 10) — viram áreas clicáveis, sem link aninhado
            rx.hstack(
                rx.box(
                    rx.hstack(
                        rx.text("Pago no mês", size="1", color=TEXT_MUTED),
                        rx.text(vstr(pago_mes), size="2", weight="bold", color=SUCCESS),
                        spacing="2",
                    ),
                    cursor="pointer",
                    on_click=[
                        rx.stop_propagation,
                        rx.prevent_default,
                        rx.redirect(f"/contas-pagar?loja={loja_name}&filtro=pagas"),
                    ],
                ),
                rx.spacer(),
                rx.box(
                    rx.hstack(
                        rx.text("Falta pagar", size="1", color=TEXT_MUTED),
                        rx.text(vstr(falta_pagar), size="2", weight="bold", color=DANGER),
                        spacing="2",
                    ),
                    cursor="pointer",
                    on_click=[
                        rx.stop_propagation,
                        rx.prevent_default,
                        rx.redirect(f"/contas-pagar?loja={loja_name}&filtro=pendentes"),
                    ],
                ),
                width="100%",
                justify="between",
            ),
            # Barra de uso do limite
            rx.progress(
                value=percentual_limite,
                color_scheme=rx.cond(esta_excedida, "red", rx.cond(esta_no_limite, "amber", "green")),
                size="1",
                width="100%",
            ),
            # Botão de editar limites (item 15)
            rx.cond(
                role_allowed(AppState.role, ("admin", "operator")),
                rx.button(
                    rx.icon("pencil", size=12),
                    "Editar limites",
                    size="1",
                    variant="soft",
                    on_click=[
                        rx.stop_propagation,
                        rx.prevent_default,
                        EditarLimitesState.abrir_edicao_loja(
                            loja_id, loja_name, monthly_limit, cash_limit
                        ),
                    ],
                    width="100%",
                ),
            ),
            padding=SPACE[4],
            border_radius=RADIUS["md"],
            style={"background": CARD_BG},
            box_shadow=SHADOW["DEFAULT"],
            border=f"1px solid {BORDER}",
            width="100%",
        ),
        href="/lojas/" + loja_id.to_string(),
        underline="none",
        width="100%",
        _hover={"box_shadow": SHADOW["DEFAULT"], "transform": "translateY(-1px)"},
        transition="all 0.15s ease",
    )


def modal_edicao_limites() -> rx.Component:
    """Modal de edição de limites da loja (item 15) — usa EditarLimitesState."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Editar limites — " + EditarLimitesState.loja_editar_nome),
            rx.vstack(
                rx.text("Limite mensal", size="1", color=TEXT_MUTED),
                rx.input(
                    value=EditarLimitesState.novo_limite_mensal,
                    on_change=EditarLimitesState.set_novo_limite_mensal,
                    placeholder="Ex: 15000",
                ),
                rx.text("Limite por Caixa", size="1", color=TEXT_MUTED),
                rx.input(
                    value=EditarLimitesState.novo_limite_caixa,
                    on_change=EditarLimitesState.set_novo_limite_caixa,
                    placeholder="Ex: 3000",
                ),
                rx.cond(
                    EditarLimitesState.edit_error != "",
                    rx.text(EditarLimitesState.edit_error, size="2", color=DANGER),
                ),
                spacing="2",
                margin_top="0.8em",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button("Cancelar", variant="soft",
                              on_click=EditarLimitesState.fechar_edicao_loja),
                ),
                rx.button("Salvar", on_click=EditarLimitesState.salvar_limites_loja,
                          style={"background": "#E31E24", "color": "white"}),
                spacing="3",
                justify="end",
                margin_top="1em",
            ),
        ),
        open=EditarLimitesState.show_edit_modal,
    )