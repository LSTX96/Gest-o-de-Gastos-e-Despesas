"""Script to update store_dashboard_card.py with Var-compatible code."""

content = '''"""Card de loja no Dashboard (Menu Inicial).

Exibe os campos no seguinte ordem (itens 4, 10, 14, 15):
1. Nome da loja
2. Gasto acumulado (total gasto no mes/periodo atual)
3. Limite mensal
4. Limite por Caixa (cash_limit) - com tooltip explicativo (item 14)
5. A vencer este mes

Adiciona tambem (item 10):
- Valor ja pago no mes (clicavel -> filtro "pagas")
- Valor que falta pagar (clicavel -> filtro "pendentes")

O card inteiro e clicavel -> /contas-pagar com filtro de loja (item 4).
"""

from __future__ import annotations

import reflex as rx
from reflex import Var

from ..state import role_allowed, DashboardState