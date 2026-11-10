"""Design Tokens & tema visual do Passivo Cumani.

As cores de fundo, card, borda e texto usam as variáveis do próprio Radix
(a biblioteca visual do Reflex). Elas mudam sozinhas entre o tema escuro
(padrão) e o claro quando o usuário alterna pelo botão da barra superior.
"""
from __future__ import annotations

import reflex as rx


# ---------------------------------------------------------------------------
# Paletas fixas (iguais nos dois temas)
# ---------------------------------------------------------------------------
RED = {
    50: "#FEF2F2", 100: "#FFE4E4", 200: "#FECACA", 300: "#FCA5A5",
    400: "#F87171", 500: "#DC2626", 600: "#B91C1C", 700: "#991B1B",
    800: "#7F1D1D", 900: "#450A0A",
}

GREEN = {
    50: "#F0FDF4", 100: "#DCFCE7", 200: "#BBF7D0", 300: "#86EFAC",
    400: "#4ADE80", 500: "#10B981", 600: "#059669", 700: "#047857",
    800: "#065F46", 900: "#064E3B",
}

AMBER = {
    50: "#FFFBEB", 100: "#FEF3C7", 200: "#FEEFBD", 300: "#FCD34D",
    400: "#FBBF24", 500: "#F59E0B", 600: "#D97706", 700: "#B45309",
    800: "#92400E", 900: "#78350F",
}

RED_CRITICAL = {
    50: "#FEF2F2", 100: "#FFE4E4", 200: "#FECACA", 300: "#FCA5A5",
    400: "#F87171", 500: "#EF4444", 600: "#DC2626", 700: "#B91C1C",
    800: "#991B1B", 900: "#7F1D1D",
}

SURFACE = {
    50: "#F8FAFC", 100: "#F1F5F9", 200: "#E2E8F0", 300: "#CBD5E1",
    400: "#94A3B8", 500: "#94A3B8", 600: "#64748B", 700: "#475569",
    800: "#334159", 900: "#0F172A",
}

NEUTRAL = {
    50: "#FFFFFF", 100: "#F8FAFC", 200: "#F1F5F9", 300: "#E2E8F0",
    400: "#CBD5E1", 500: "#94A3B8", 600: "#64748B", 700: "#475569",
    800: "#334159", 900: "#0F172A",
}


# ---------------------------------------------------------------------------
# Constantes nomeadas usadas pelo projeto
# ---------------------------------------------------------------------------
PRIMARY = RED[500]                        # vermelho Cumani (igual nos dois temas)
PRIMARY_HOVER = RED[600]
PRIMARY_BG = "rgba(220, 38, 38, 0.12)"    # fundo avermelhado suave, funciona nos dois temas
SUCCESS = GREEN[500]
WARNING = AMBER[500]
DANGER = RED_CRITICAL[500]

# Cores que mudam com o tema (variáveis do Radix, trocadas automaticamente)
PAGE_BG = "var(--color-background)"       # fundo da página
CARD_BG = "var(--color-panel-solid)"      # fundo dos cards
CARD_BG_2 = "var(--gray-a2)"              # fundo levemente destacado
BORDER = "var(--gray-a5)"                 # bordas
TEXT_TITLE = "var(--gray-12)"             # títulos e valores
TEXT_BODY = "var(--gray-11)"              # texto comum
TEXT_MUTED = "var(--gray-10)"             # rótulos e textos secundários
GRID = "var(--gray-a4)"                   # linhas de grade

SIDEBAR_BG = NEUTRAL[900]
SIDEBAR_TEXT = "#CBD5E1"

# Semáforo de vencimento (compatível com utils/semaforo.py)
SEMAFORO_VERDE = GREEN[500]
SEMAFORO_AMARELO = AMBER[500]
SEMAFORO_LARANJA = "#F97316"
SEMAFORO_VERMELHO = RED_CRITICAL[500]

# Cores de avatar ficam em hexadecimal (são gravadas no banco)
AVATAR_PALETTE = [
    PRIMARY, SUCCESS, "#1A1A2E", WARNING, "#94A3B8",
    "#0077B6", "#9D4EDD", "#2A9D8F",
]


# ---------------------------------------------------------------------------
# Tipografia
# ---------------------------------------------------------------------------
FONT_FAMILY = "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

TITULO_TIPO = {
    "size": "24px",
    "weight": "600",
    "letter_spacing": "-0.01em",
    "color": TEXT_TITLE,
}

SUBTITULO_TIPO = {
    "size": "16px",
    "weight": "500",
    "text_transform": "uppercase",
    "letter_spacing": "0.05em",
    "color": TEXT_BODY,
}

CORPO_TIPO = {
    "size": "14px",
    "weight": "400",
    "color": TEXT_BODY,
    "line_height": "1.5",
}

MONETARIO_TIPO = {
    "font_variant_numeric": "tabular-nums",
    "font_family": "ui-monospace, 'Fira Mono', 'Menlo', monospace",
    "font_size": "14px",
    "font_weight": "400",
}


# ---------------------------------------------------------------------------
# Sombras
# ---------------------------------------------------------------------------
SHADOW = {
    "sm": "0 1px 2px rgba(0,0,0,0.06)",
    "DEFAULT": "0 1px 3px rgba(0,0,0,0.10), 0 1px 2px rgba(0,0,0,0.06)",
    "md": "0 4px 6px -1px rgba(0,0,0,0.12), 0 2px 4px -2px rgba(0,0,0,0.06)",
    "lg": "0 10px 15px -3px rgba(0,0,0,0.14), 0 4px 6px -4px rgba(0,0,0,0.06)",
    "xl": "0 20px 25px -5px rgba(0,0,0,0.16), 0 10px 10px -5px rgba(0,0,0,0.06)",
}


# ---------------------------------------------------------------------------
# Bordas arredondadas
# ---------------------------------------------------------------------------
RADIUS = {
    "sm": "6px",
    "DEFAULT": "10px",
    "md": "12px",
    "lg": "14px",
    "xl": "18px",
    "full": "9999px",
}


# ---------------------------------------------------------------------------
# Espaçamentos (grade de 4px)
# ---------------------------------------------------------------------------
SPACE = {
    0: "0", 1: "0.25rem", 2: "0.5rem", 3: "0.75rem", 4: "1rem",
    5: "1.25rem", 6: "1.5rem", 7: "1.75rem", 8: "2rem", 9: "2.25rem",
    10: "2.5rem", 11: "2.75rem", 12: "3rem",
}


# ---------------------------------------------------------------------------
# Estilos reutilizáveis
# ---------------------------------------------------------------------------
PAGE_CONTAINER = {
    "padding": f"{SPACE[4]} {SPACE[5]}",
    "max_width": "1280px",
    "margin": "0 auto",
    "width": "100%",
}

CARD_STYLE = {
    "background": CARD_BG,
    "border_radius": RADIUS["md"],
    "box_shadow": SHADOW["DEFAULT"],
    "border": f"1px solid {BORDER}",
    "padding": f"{SPACE[4]}",
}

INPUT_STYLE = {
    "background": CARD_BG,
    "border": f"1px solid {BORDER}",
    "border_radius": RADIUS["sm"],
    "padding": f"{SPACE[2]} {SPACE[3]}",
    "font_size": "14px",
    "color": TEXT_TITLE,
    "width": "100%",
    "_focus": {
        "outline": "none",
        "border_color": PRIMARY,
        "box_shadow": f"0 0 0 2px {PRIMARY_BG}",
    },
}

BTN_PRIMARY = {
    "background": PRIMARY,
    "color": "white",
    "border": "none",
    "border_radius": RADIUS["sm"],
    "padding": f"{SPACE[2]} {SPACE[4]}",
    "font_size": "14px",
    "font_weight": "500",
    "cursor": "pointer",
    "_hover": {"background": PRIMARY_HOVER},
    "_active": {"background": PRIMARY_HOVER},
}

BTN_SECONDARY = {
    "background": "transparent",
    "color": TEXT_BODY,
    "border": f"1px solid {BORDER}",
    "border_radius": RADIUS["sm"],
    "padding": f"{SPACE[2]} {SPACE[4]}",
    "font_size": "14px",
    "font_weight": "500",
    "cursor": "pointer",
    "_hover": {"background": CARD_BG_2},
}

TABLE_HEADER_STYLE = {
    "background": CARD_BG,
    "border_bottom": f"2px solid {BORDER}",
}

TABLE_ROW_STYLE = {
    "_even": {"background": CARD_BG_2},
    "_hover": {"background": PRIMARY_BG},
}


def get_theme() -> rx.Theme:
    """Tema Reflex: escuro por padrão, cinza 'slate' (grafite azulado), alternável."""
    return rx.theme(
        appearance="dark",
        accent_color="red",
        gray_color="slate",
        radius="large",
    )