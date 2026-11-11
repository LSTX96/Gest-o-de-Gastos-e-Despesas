"""Estado da página inicial: números da rede, situação das lojas, alertas e atividade."""
from collections import defaultdict
from datetime import date, datetime, timedelta

import plotly.graph_objects as go
import reflex as rx
from sqlmodel import select

from ..models import Store, BoletoEntry, FixedExpense, FixedExpensePayment, AuditLog
from ..state import AppState
from ..utils.helpers import fmt_moeda
from ..utils.graficos import travar
from .contas_estado import _dia_venc, _ultimo_dia

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
ACOES = {
    "create": "Novo lançamento",
    "update": "Alteração",
    "delete": "Enviado para a lixeira",
    "pay": "Pagamento registrado",
    "unpay": "Pagamento desfeito",
    "restore": "Restaurado da lixeira",
}
TITULOS = {
    ("create", "boleto_entry"): "Nova despesa lançada",
    ("update", "boleto_entry"): "Despesa alterada",
    ("create", "fixed_expense"): "Nova conta fixa",
    ("update", "fixed_expense"): "Conta fixa atualizada",
    ("create", "store"): "Nova loja",
    ("update", "store"): "Loja atualizada",
    ("delete", "store"): "Loja desativada",
    ("restore", "store"): "Loja reativada",
    ("create", "user"): "Novo usuário",
    ("update", "user"): "Acesso de usuário alterado",
    ("create", "distributor"): "Novo gasto cadastrado",
    ("create", "expense_type"): "Novo tipo de despesa",
}
VERMELHO = "#EF4444"
LARANJA = "#F59E0B"
VERDE = "#10B981"
CINZA = "#94A3B8"


def _agora_brasilia() -> datetime:
    """Horário de Brasília (UTC-3), sem depender do fuso do servidor."""
    return datetime.utcnow() - timedelta(hours=3)


class InicioState(AppState):
    saudacao: str = ""
    data_hoje: str = ""

    # Números
    n_gasto_mes: str = "R$ 0,00"
    n_acumulado: str = "R$ 0,00"
    n_acumulado_pago: str = ""
    n_fixas: str = "R$ 0,00"
    n_variaveis: str = "R$ 0,00"
    n_excedente: str = ""

    # Situação das lojas
    lojas_excedidas: list[dict[str, str]] = []
    lojas_dentro: list[dict[str, str]] = []
    lojas_sem_limite: list[dict[str, str]] = []
    lojas_cards: list[dict[str, str]] = []

    # Alertas
    qtd_vencidas: int = 0
    valor_vencidas: str = "R$ 0,00"
    qtd_proximas: int = 0
    valor_proximas: str = "R$ 0,00"

    # Atividade e gráfico
    atividade: list[dict[str, str]] = []
    figura_limites: go.Figure = go.Figure()
    tem_limites: bool = False

    def carregar(self):
        agora = _agora_brasilia()
        hoje = agora.date()
        hora = agora.hour
        cumprimento = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
        self.saudacao = f"{cumprimento}, {self.display_name or self.username}"
        self.data_hoje = (
            f"{DIAS[hoje.weekday()].capitalize()}, {hoje.day} de "
            f"{MESES[hoje.month - 1]} de {hoje.year}"
        )

        ini = hoje.replace(day=1)
        fim = _ultimo_dia(hoje.year, hoje.month)
        limite_alerta = hoje + timedelta(days=5)

        with rx.session() as s:
            lojas = [l for l in s.exec(select(Store)).all() if l.active]
            ids = {l.id for l in lojas}
            boletos = [
                b for b in s.exec(select(BoletoEntry)).all()
                if b.deleted_at is None and b.store_id in ids
            ]
            fixas = [
                f for f in s.exec(select(FixedExpense)).all()
                if f.active and f.deleted_at is None and f.store_id in ids
            ]
            pagamentos = [
                p for p in s.exec(select(FixedExpensePayment)).all() if p.store_id in ids
            ]
            logs = s.exec(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(8)).all()

        pagos_fixa = {(p.fixed_expense_id, p.competencia) for p in pagamentos}

        # --- gasto do mês por loja ---
        gasto_loja = defaultdict(float)
        pago_loja = defaultdict(float)
        var_mes = 0.0
        fix_mes = 0.0
        for b in boletos:
            if ini <= b.boleto_date <= fim:
                gasto_loja[b.store_id] += b.amount
                var_mes += b.amount
                if b.is_paid:
                    pago_loja[b.store_id] += b.amount
        for f in fixas:
            gasto_loja[f.store_id] += f.amount
            fix_mes += f.amount
            if (f.id, ini) in pagos_fixa:
                pago_loja[f.store_id] += f.amount

        self.n_gasto_mes = fmt_moeda(var_mes + fix_mes)
        self.n_fixas = fmt_moeda(fix_mes)
        self.n_variaveis = fmt_moeda(var_mes)

        # --- acumulado total ---
        acumulado = sum(b.amount for b in boletos) + sum(p.amount for p in pagamentos)
        acumulado_pago = sum(b.amount for b in boletos if b.is_paid) + sum(p.amount for p in pagamentos)
        self.n_acumulado = fmt_moeda(acumulado)
        self.n_acumulado_pago = f"({fmt_moeda(acumulado_pago)} pagos)"

        # --- situação das lojas ---
        excedidas, dentro, sem_limite, cards = [], [], [], []
        total_excedente = 0.0
        for l in lojas:
            gasto = gasto_loja[l.id]
            pago = pago_loja[l.id]
            limite = l.monthly_limit or 0.0
            pct = (gasto / limite * 100) if limite > 0 else 0.0
            if limite <= 0:
                status, cor = "sem_limite", CINZA
                sem_limite.append({"id": str(l.id), "nome": l.name})
            elif gasto > limite:
                status, cor = "excedida", VERMELHO
                excesso = gasto - limite
                total_excedente += excesso
                excedidas.append({"id": str(l.id), "nome": l.name, "excesso": fmt_moeda(excesso)})
            else:
                status, cor = ("alerta", LARANJA) if pct >= 80 else ("ok", VERDE)
                dentro.append({"id": str(l.id), "nome": l.name})
            cards.append({
                "id": str(l.id),
                "nome": l.name,
                "inicial": (l.name or "?")[:1].upper(),
                "cor": l.avatar_color or VERMELHO,
                "gasto": fmt_moeda(gasto),
                "limite": fmt_moeda(limite) if limite > 0 else "não definido",
                "pago": fmt_moeda(pago),
                "falta": fmt_moeda(max(gasto - pago, 0.0)),
                "pct_barra": f"{min(pct, 100):.0f}",
                "pct_txt": f"{pct:.0f}%" if limite > 0 else "—",
                "pct_num": f"{pct:.4f}",
                "barra_cor": cor,
                "status": status,
            })
        ordem = {"excedida": 0, "alerta": 1, "ok": 2, "sem_limite": 3}
        cards.sort(key=lambda c: (ordem[c["status"]], -float(c["pct_num"])))
        self.lojas_excedidas = excedidas
        self.lojas_dentro = dentro
        self.lojas_sem_limite = sem_limite
        self.lojas_cards = cards
        self.n_excedente = (
            f"{fmt_moeda(total_excedente)} acima dos limites" if excedidas else "Nenhuma loja acima do limite"
        )

        # --- alertas de vencimento ---
        qtd_venc = qtd_prox = 0
        val_venc = val_prox = 0.0
        for b in boletos:
            if b.is_paid:
                continue
            if b.boleto_date < hoje:
                qtd_venc += 1
                val_venc += b.amount
            elif b.boleto_date <= limite_alerta:
                qtd_prox += 1
                val_prox += b.amount
        meses = {(hoje.year, hoje.month), (limite_alerta.year, limite_alerta.month)}
        for f in fixas:
            for a, m in meses:
                venc = _dia_venc(f.due_day, a, m)
                if venc is None or (f.id, date(a, m, 1)) in pagos_fixa:
                    continue
                if (a, m) == (hoje.year, hoje.month) and venc < hoje:
                    qtd_venc += 1
                    val_venc += f.amount
                elif hoje <= venc <= limite_alerta:
                    qtd_prox += 1
                    val_prox += f.amount
        self.qtd_vencidas = qtd_venc
        self.valor_vencidas = fmt_moeda(val_venc)
        self.qtd_proximas = qtd_prox
        self.valor_proximas = fmt_moeda(val_prox)

        # --- atividade recente ---
        self.atividade = [
            {
                "acao": TITULOS.get(
                    (log.action, log.entity_type),
                    ACOES.get(log.action, log.action or "Registro"),
                ),
                "descricao": log.description or "",
                "usuario": log.username or "sistema",
                "quando": (log.timestamp - timedelta(hours=3)).strftime("%d/%m %H:%M") if log.timestamp else "",
            }
            for log in logs
        ]

        # --- gráfico de uso do limite ---
        com_limite = [c for c in cards if c["status"] != "sem_limite"]
        com_limite.sort(key=lambda c: float(c["pct_num"]))
        self.tem_limites = bool(com_limite)
        fig = go.Figure()
        if com_limite:
            fig.add_bar(
                x=[round(float(c["pct_num"]), 1) for c in com_limite],
                y=[c["nome"] for c in com_limite],
                orientation="h",
                marker_color=[c["barra_cor"] for c in com_limite],
                text=[c["pct_txt"] for c in com_limite],
                textposition="outside",
                hovertemplate="%{y}: %{x:.1f}% do limite<extra></extra>",
            )
            fig.add_vline(x=100, line_width=2, line_dash="dash", line_color=VERMELHO)
        fig.update_layout(
            height=max(220, 44 * len(com_limite) + 80),
            margin=dict(t=10, l=10, r=40, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter, sans-serif", "color": CINZA},
            showlegend=False,
        )
        fig.update_xaxes(ticksuffix="%", gridcolor="rgba(148,163,184,0.18)", zeroline=False)
        fig.update_yaxes(automargin=True)
        self.figura_limites = travar(fig)