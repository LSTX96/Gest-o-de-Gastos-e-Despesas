"""Estado central da aplicação Reflex — Passivo Drogarias Cumani."""
from __future__ import annotations

import base64
import functools
from datetime import date, datetime, timedelta
from typing import Optional

import reflex as rx
from sqlmodel import select
import plotly.graph_objects as go

from .models import (
    User, Store, FixedExpense, Distributor, ExpenseType, BoletoEntry, AuditLog,
)
from .auth import hash_senha, verificar_senha, pode_editar_item
from .utils.semaforo import cor_semaforo, status_semaforo, nivel_semaforo, dias_restantes
from .utils.avatar import cor_por_nome, iniciais as gerar_iniciais
from .utils.helpers import fmt_moeda, inicio_semana, fim_semana, periodo_semana_str, nome_mes, proximo_vencimento_mensal


def role_allowed(role_var: rx.Var, allowed: tuple[str, ...]) -> rx.Var:
    """Expressão Var: role_var está dentro da tupla `allowed`."""
    exprs = [role_var == r for r in allowed]
    return functools.reduce(lambda a, b: a | b, exprs)


def _formatar_figura_moeda(fig: go.Figure, titulo_vazio: str = "Sem lançamentos neste período") -> None:
    """Aplica formatação R$ (milhar com ponto, decimal com vírgula) e um
    aviso quando o gráfico não tiver nenhuma série de dados."""
    fig.update_layout(
        barmode="group", height=340, margin=dict(t=30, l=50, r=10, b=40),
        separators=".,",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter, sans-serif", "color": "#475569"},
        hoverlabel={"bgcolor": "#1E293B", "font": {"color": "white", "family": "Inter, sans-serif"}},
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")
    fig.update_yaxes(tickprefix="R$ ", tickformat=",.2f", gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")
    if not fig.data:
        fig.add_annotation(
            text=titulo_vazio,
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=13, color="#94A3B8"),
        )


def _tempo_relativo(dt: datetime) -> str:
    """Converte um datetime em texto relativo: 'há 2h', 'há 3 dias'."""
    if dt is None:
        return ""
    delta = datetime.utcnow() - dt
    if delta.days >= 1:
        return f"há {delta.days} dia(s)"
    horas = delta.seconds // 3600
    if horas >= 1:
        return f"há {horas}h"
    minutos = max(delta.seconds // 60, 1)
    return f"há {minutos}min"


ACAO_ICONES = {
    "create": "plus-circle",
    "update": "pencil",
    "delete": "trash-2",
    "pay": "banknote",
}


# ---------------------------------------------------------------------------
# Estado base — autenticação
# ---------------------------------------------------------------------------
class AppState(rx.State):
    user_id: int = 0
    username: str = ""
    display_name: str = ""
    role: str = ""  # admin | operator | viewer
    is_logged_in: bool = False

    login_username: str = ""
    login_password: str = ""
    login_error: str = ""

    # Toast de notificação (sucesso/erro)
    toast_message: str = ""
    toast_status: str = ""  # "success" | "error"
    toast_open: bool = False
    mobile_menu_open: bool = False

    # Confirmação de exclusão
    confirm_open: bool = False
    confirm_title: str = ""
    confirm_message: str = ""
    confirm_action: str = ""  # nome do método a chamar
    confirm_data: dict = {}

    def toggle_mobile_menu(self):
        self.mobile_menu_open = not self.mobile_menu_open

    def fechar_mobile_menu(self):
        self.mobile_menu_open = False

    @rx.var
    def current_route(self) -> str:
        """Rota atual da URL — usada para highlight na navegação."""
        try:
            return self.router.page.path or ""
        except Exception:
            return ""

    @rx.var
    def role_label(self) -> str:
        return {"admin": "Administrador", "operator": "Operador", "viewer": "Visualizador"}.get(
            self.role, ""
        )

    def role_in(self, roles: tuple) -> bool:
        return self.role in roles

    def set_login_username(self, value: str):
        self.login_username = value

    def set_login_password(self, value: str):
        self.login_password = value

    def do_login(self):
        with rx.session() as session:
            user = session.exec(
                select(User).where(User.username == self.login_username.strip())
            ).first()
            if not user or not user.active or not verificar_senha(self.login_password, user.password_hash):
                self.login_error = "Usuário ou senha inválidos."
                return
            self.user_id = user.id
            self.username = user.username
            self.display_name = user.display_name or user.username
            self.role = user.role
            self.is_logged_in = True
            self.login_error = ""
            self.login_password = ""
        return rx.redirect("/dashboard")

    def logout(self):
        self.reset()
        return rx.redirect("/login")

    def check_auth(self):
        if not self.is_logged_in:
            return rx.redirect("/login")

    def route_index(self):
        return rx.redirect("/dashboard") if self.is_logged_in else rx.redirect("/login")

    def log_auditoria(self, session, action: str, entity_type: str, entity_id: int | None, desc: str):
        session.add(
            AuditLog(
                user_id=self.user_id, username=self.username, action=action,
                entity_type=entity_type, entity_id=entity_id, description=desc,
            )
        )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardState(AppState):
    total_mes: str = "R$ 0,00"
    total_boletos: str = "R$ 0,00"
    total_fixas: str = "R$ 0,00"
    lojas_no_limite: int = 0
    lojas_excedidas: int = 0
    contas_a_vencer: int = 0
    figura_lojas: go.Figure = go.Figure()
    figura_tipos: go.Figure = go.Figure()
    proximos_vencimentos: list[dict] = []
    lojas_resumo: list[dict] = []
    atividade_recente: list[dict] = []

    def carregar(self):
        with rx.session() as session:
            lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            hoje = date.today()
            ini_mes = hoje.replace(day=1)
            fim_mes = (ini_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            total_boletos = 0.0
            total_fixas = 0.0
            barras = []
            vencendo = []
            resumo = []
            n_limite = 0
            n_excedido = 0

            for loja in lojas:
                # BOLETOS: soma os lançamentos cujo VENCIMENTO cai no mês atual,
                # independentemente de is_paid (o status é só visual).
                boletos = session.exec(
                    select(BoletoEntry).where(
                        BoletoEntry.store_id == loja.id,
                        BoletoEntry.boleto_date >= ini_mes,
                        BoletoEntry.boleto_date <= fim_mes,
                    )
                ).all()
                soma_boletos = sum(b.amount for b in boletos)

                # CONTAS FIXAS: soma todas as contas fixas ATIVAS, independentemente de is_paid.
                fixas = session.exec(
                    select(FixedExpense).where(
                        FixedExpense.store_id == loja.id, FixedExpense.active == True  # noqa: E712
                    )
                ).all()
                soma_fixas = sum(f.amount for f in fixas)

                total_boletos += soma_boletos
                total_fixas += soma_fixas
                combinado = soma_boletos + soma_fixas
                barras.append({"loja": loja.name, "valor": round(combinado, 2)})

                # PAGOS NO MÊS CORRENTE
                pago_mes = 0.0
                for b in boletos:
                    if b.is_paid and b.paid_at and b.paid_at.date() >= ini_mes:
                        pago_mes += b.amount

                for f in fixas:
                    if f.is_paid and f.paid_at:
                        venc = proximo_vencimento_mensal(f.due_day, hoje)
                        if venc and ini_mes <= venc <= hoje.replace(day=28):
                            pago_mes += f.amount

                falta_pagar = combinado - pago_mes

                # A VENCER ESTE MÊS (fixas não pagas com vencimento neste mês)
                a_vencer_mes = 0.0
                for f in fixas:
                    if not f.is_paid:
                        venc = proximo_vencimento_mensal(f.due_day, hoje)
                        if venc and ini_mes <= venc <= hoje.replace(day=28):
                            a_vencer_mes += f.amount

                excedeu = bool(loja.monthly_limit and combinado > loja.monthly_limit)
                if excedeu:
                    n_excedido += 1
                else:
                    n_limite += 1

                percentual = (combinado / loja.monthly_limit * 100) if loja.monthly_limit else 0.0
                resumo.append(
                    {
                        "loja_id": loja.id,
                        "loja": loja.name,
                        "cor": loja.avatar_color,
                        "logo_b64": str(loja.logo_b64) if loja.logo_b64 else "",
                        "gasto": round(combinado, 2),
                        "gasto_str": fmt_moeda(combinado),
                        "monthly_limit": round(loja.monthly_limit, 2),
                        "cash_limit": round(loja.cash_limit, 2),
                        "a_vencer_mes": round(a_vencer_mes, 2),
                        "pago_mes": round(pago_mes, 2),
                        "falta_pagar": round(max(falta_pagar, 0.0), 2),
                        "percentual": round(min(percentual, 999), 1),
                        "excedido": excedeu,
                        "no_limite": bool(loja.monthly_limit and combinado >= loja.monthly_limit),
                    }
                )

                for f in fixas:
                    vencendo.append(
                        {
                            "loja": loja.name,
                            "nome": f.name,
                            "valor": fmt_moeda(f.amount),
                            "cor": "#6C757D",
                        }
                    )

            self.lojas_resumo = resumo
            self.total_boletos = fmt_moeda(total_boletos)
            self.total_fixas = fmt_moeda(total_fixas)
            self.total_mes = fmt_moeda(total_boletos + total_fixas)
            self.lojas_no_limite = n_limite
            self.lojas_excedidas = n_excedido

            fig1 = go.Figure()
            fig1.add_bar(
                x=[b["loja"] for b in barras],
                y=[b["valor"] for b in barras],
                marker_color="#DC2626",
            )
            fig1.update_layout(
                height=320, margin=dict(t=10, l=40, r=10, b=40),
                bargap=0.3,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font={"family": "Inter, sans-serif", "color": "#475569"},
            )
            fig1.update_xaxes(tickangle=-20, gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")
            fig1.update_yaxes(tickprefix="R$ ", tickformat=",.2f", gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")
            self.figura_lojas = fig1

            tipos = session.exec(select(ExpenseType)).all()
            dist_tipo = {}
            todos_boletos = session.exec(
                select(BoletoEntry).where(
                    BoletoEntry.boleto_date >= ini_mes,
                    BoletoEntry.boleto_date <= fim_mes,
                )
            ).all()
            tipo_map = {t.id: t.name for t in tipos}
            for b in todos_boletos:
                nome_tipo = tipo_map.get(b.expense_type_id, "Outros")
                dist_tipo[nome_tipo] = dist_tipo.get(nome_tipo, 0.0) + b.amount

            fig2 = go.Figure()
            fig2.add_pie(labels=list(dist_tipo.keys()), values=[round(v, 2) for v in dist_tipo.values()])
            fig2.update_layout(
                height=320, margin=dict(t=10, l=10, r=10, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font={"family": "Inter, sans-serif", "color": "#475569"},
                legend={"orientation": "h", "yanchor": "bottom", "y": -0.3, "xanchor": "center", "x": 0.5},
            )
            self.figura_tipos = fig2

            self.contas_a_vencer = 0
            proximos = []
            todas_fixas = session.exec(select(FixedExpense).where(FixedExpense.active == True)).all()  # noqa: E712
            loja_nomes = {s.id: s.name for s in lojas}
            count_vencer = 0
            for f in todas_fixas:
                if f.is_paid:
                    continue
                venc = proximo_vencimento_mensal(f.due_day, hoje)
                if venc is None:
                    continue
                dias = (venc - hoje).days
                if dias <= 5:
                    count_vencer += 1
                    proximos.append({"nome": f.name, "loja": loja_nomes.get(f.store_id, "")})
            self.contas_a_vencer = count_vencer
            self.proximos_vencimentos = proximos[:5]

    def ver_loja(self, nome: str):
        return [ContasPagarState.set_filtro_loja(nome), rx.redirect("/contas-pagar")]


# ---------------------------------------------------------------------------
# Lançamentos (Operador)
# ---------------------------------------------------------------------------
class LancamentosState(AppState):
    stores: list[dict] = []
    selected_store_id: str = ""

    tipo_lancamento: str = "fixa"  # fixa | boleto

    fixed_expenses_options: list[dict] = []
    selected_fixed_expense_id: str = ""
    fixa_valor: str = ""
    fixa_mes_ref: str = ""
    fixa_pago: bool = False

    distributor_options: list[dict] = []
    selected_distributor_id: str = ""
    expense_type_options: list[dict] = []
    selected_expense_type_id: str = ""
    boleto_data: str = ""
    boleto_valor: str = ""
    boleto_forma_pgto: str = "PIX"
    boleto_obs: str = ""

    # Parcelamento e status do lançamento de "Outros"
    parcelado: bool = False
    num_parcelas: str = "1"
    parcela_datas: list[dict] = []
    boleto_pago: bool = False

    ultimos_lancamentos: list[dict] = []
    msg_sucesso: str = ""

    # --- modais de cadastro rápido ---
    show_modal_loja: bool = False
    nova_loja_nome: str = ""
    nova_loja_limite_semanal: str = ""
    nova_loja_limite_mensal: str = ""
    nova_loja_logo_b64: str = ""

    show_modal_conta_fixa: bool = False
    nova_conta_nome: str = ""
    nova_conta_valor: str = ""
    nova_conta_dia: str = ""
    nova_conta_forma: str = "PIX"

    show_modal_distribuidora: bool = False
    nova_distribuidora_nome: str = ""

    show_modal_tipo: bool = False
    novo_tipo_nome: str = ""
    novo_tipo_categoria: str = "Variável"

    def carregar(self):
        with rx.session() as session:
            lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            self.stores = [{"id": str(s.id), "name": s.name} for s in lojas]
            if lojas and not self.selected_store_id:
                self.selected_store_id = str(lojas[0].id)

            dists = session.exec(select(Distributor).where(Distributor.active == True)).all()  # noqa: E712
            self.distributor_options = [{"id": str(d.id), "name": d.name} for d in dists]

            tipos = session.exec(select(ExpenseType).where(ExpenseType.active == True)).all()  # noqa: E712
            self.expense_type_options = [{"id": str(t.id), "name": t.name} for t in tipos]

        self._carregar_contas_fixas_da_loja()
        self._carregar_ultimos()

    def set_selected_store_id(self, value: str):
        self.selected_store_id = value
        self._carregar_contas_fixas_da_loja()

    def set_tipo_lancamento(self, value: str | list[str]):
        self.tipo_lancamento = value if isinstance(value, str) else (value[0] if value else "fixa")

    def _carregar_contas_fixas_da_loja(self):
        if not self.selected_store_id:
            self.fixed_expenses_options = []
            return
        with rx.session() as session:
            contas = session.exec(
                select(FixedExpense).where(
                    FixedExpense.store_id == int(self.selected_store_id),
                    FixedExpense.active == True,  # noqa: E712
                )
            ).all()
            self.fixed_expenses_options = [
                {"id": str(c.id), "name": c.name, "amount": c.amount}
                for c in contas
            ]

    def set_selected_fixed_expense_id(self, value: str):
        self.selected_fixed_expense_id = value
        for c in self.fixed_expenses_options:
            if c["id"] == value:
                self.fixa_valor = str(c["amount"])

    def set_fixa_valor(self, value: str):
        self.fixa_valor = value

    def set_fixa_pago(self, value: bool):
        self.fixa_pago = value

    def set_selected_distributor_id(self, value: str):
        self.selected_distributor_id = value

    def set_selected_expense_type_id(self, value: str):
        self.selected_expense_type_id = value

    def set_boleto_valor(self, value: str):
        self.boleto_valor = value

    def set_boleto_forma_pgto(self, value: str):
        self.boleto_forma_pgto = value

    def set_boleto_obs(self, value: str):
        self.boleto_obs = value

    # --- cadastros rápidos: campos dos modais ---
    def set_nova_loja_nome(self, value: str):
        self.nova_loja_nome = value

    def set_nova_loja_limite_semanal(self, value: str):
        self.nova_loja_limite_semanal = value

    def set_nova_loja_limite_mensal(self, value: str):
        self.nova_loja_limite_mensal = value

    def set_nova_conta_nome(self, value: str):
        self.nova_conta_nome = value

    def set_nova_conta_valor(self, value: str):
        self.nova_conta_valor = value

    def set_nova_conta_dia(self, value: str):
        self.nova_conta_dia = value

    def set_nova_conta_forma(self, value: str):
        self.nova_conta_forma = value

    def set_nova_distribuidora_nome(self, value: str):
        self.nova_distribuidora_nome = value

    def set_novo_tipo_nome(self, value: str):
        self.novo_tipo_nome = value

    def set_novo_tipo_categoria(self, value: str):
        self.novo_tipo_categoria = value

    # --- Outros (compras/pagamentos): vencimento, parcelas e status ---
    def set_boleto_data(self, value: str):
        self.boleto_data = value
        if self.parcelado:
            self._gerar_datas_parcelas()

    def set_boleto_parcelado(self, value: bool):
        self.parcelado = bool(value)
        if self.parcelado:
            self.boleto_pago = False
            self._gerar_datas_parcelas()
        else:
            self.parcela_datas = []

    def set_num_parcelas(self, value: str):
        self.num_parcelas = value
        self._gerar_datas_parcelas()

    def set_boleto_pago(self, value: bool):
        self.boleto_pago = bool(value)

    def set_parcela_data(self, idx: int, value: str):
        if idx == 0:
            # Mudar a 1ª parcela refaz as sugestões das demais
            self.boleto_data = value
            self._gerar_datas_parcelas()
            return
        datas = [dict(p) for p in self.parcela_datas]
        if idx < len(datas):
            datas[idx]["data"] = value
            self.parcela_datas = datas

    def _numero_parcelas(self) -> int:
        try:
            return max(int(self.num_parcelas or 1), 1)
        except ValueError:
            return 1

    def _gerar_datas_parcelas(self):
        import calendar

        if not self.parcelado or not self.boleto_data:
            self.parcela_datas = []
            return
        try:
            base = datetime.strptime(self.boleto_data, "%Y-%m-%d").date()
        except ValueError:
            self.parcela_datas = []
            return
        datas = []
        for i in range(self._numero_parcelas()):
            m = base.month - 1 + i
            ano = base.year + m // 12
            mes = m % 12 + 1
            dia = min(base.day, calendar.monthrange(ano, mes)[1])
            datas.append({
                "label": f"{i + 1}ª parcela",
                "data": date(ano, mes, dia).isoformat(),
            })
        self.parcela_datas = datas

    @rx.var
    def valor_parcela_str(self) -> str:
        try:
            total = float(self.boleto_valor.replace(",", "."))
        except ValueError:
            return ""
        return fmt_moeda(round(total / self._numero_parcelas(), 2))

    def _limpar_form_boleto(self):
        self.boleto_valor = ""
        self.boleto_obs = ""
        self.boleto_data = ""
        self.boleto_pago = False
        self.parcelado = False
        self.num_parcelas = "1"
        self.parcela_datas = []

    def salvar_boleto(self):
        import uuid

        if not (self.selected_store_id and self.selected_distributor_id and self.boleto_valor and self.boleto_data):
            self.msg_sucesso = "Preencha loja, distribuidora, vencimento e valor."
            return
        try:
            total = float(self.boleto_valor.replace(",", "."))
        except ValueError:
            self.msg_sucesso = "Valor inválido."
            return

        n = self._numero_parcelas() if self.parcelado else 1
        if self.parcelado:
            datas_txt = [p["data"] for p in self.parcela_datas[:n]]
        else:
            datas_txt = [self.boleto_data]
        if len(datas_txt) != n:
            self.msg_sucesso = "Confira as datas das parcelas."
            return
        try:
            datas = [datetime.strptime(d, "%Y-%m-%d").date() for d in datas_txt]
        except ValueError:
            self.msg_sucesso = "Alguma data de vencimento está inválida."
            return

        # Valor total dividido; a última parcela recebe o ajuste de centavos
        valor_base = round(total / n, 2)
        valores = [valor_base] * n
        valores[-1] = round(total - valor_base * (n - 1), 2)

        grupo = uuid.uuid4().hex if n > 1 else None
        pago = self.boleto_pago and not self.parcelado
        hoje = date.today()

        with rx.session() as session:
            for i, (venc, valor) in enumerate(zip(datas, valores), start=1):
                novo = BoletoEntry(
                    store_id=int(self.selected_store_id),
                    distributor_id=int(self.selected_distributor_id),
                    boleto_date=venc,
                    amount=valor,
                    payment_method=self.boleto_forma_pgto,
                    expense_type_id=int(self.selected_expense_type_id) if self.selected_expense_type_id else None,
                    notes=self.boleto_obs,
                    operator_id=self.user_id,
                    week_period=periodo_semana_str(venc),
                    data_lancamento=hoje,
                    parcela_num=i if n > 1 else None,
                    total_parcelas=n if n > 1 else None,
                    grupo_parcelas=grupo,
                    is_paid=pago,
                    paid_at=datetime.utcnow() if pago else None,
                    paid_by=self.user_id if pago else None,
                )
                session.add(novo)
                session.commit()
                session.refresh(novo)
                desc = f"Lançamento {i}/{n}" if n > 1 else "Novo lançamento"
                self.log_auditoria(session, "create", "boleto_entry", novo.id, desc)
                session.commit()

        self._limpar_form_boleto()
        self.msg_sucesso = f"{n} lançamento(s) salvo(s) com sucesso!"
        self._carregar_ultimos()

    def _carregar_ultimos(self):
        with rx.session() as session:
            boletos = session.exec(
                select(BoletoEntry).order_by(BoletoEntry.created_at.desc()).limit(10)
            ).all()
            stores = {s.id: s.name for s in session.exec(select(Store)).all()}
            self.ultimos_lancamentos = []
            for b in boletos:
                desc = f"Boleto — {stores.get(b.store_id, '?')}"
                if b.total_parcelas and b.total_parcelas > 1:
                    desc += f" ({b.parcela_num}/{b.total_parcelas})"
                status = "Pago" if b.is_paid else "A pagar"
                self.ultimos_lancamentos.append({
                    "descricao": f"{desc} · {status}",
                    "valor": fmt_moeda(b.amount),
                    "data": f"Venc. {b.boleto_date.strftime('%d/%m/%Y')}",
                })

    def salvar_conta_fixa_lancamento(self):
        if not self.selected_store_id or not self.selected_fixed_expense_id:
            self.msg_sucesso = "Selecione a loja e a conta fixa."
            return
        with rx.session() as session:
            conta = session.get(FixedExpense, int(self.selected_fixed_expense_id))
            if conta:
                try:
                    conta.amount = float(self.fixa_valor.replace(",", "."))
                except ValueError:
                    pass
                conta.is_paid = self.fixa_pago
                if self.fixa_pago:
                    conta.paid_at = datetime.utcnow()
                    conta.paid_by = self.user_id
                session.add(conta)
                self.log_auditoria(session, "update", "fixed_expense", conta.id, f"Lançamento: {conta.name}")
                session.commit()
        self.msg_sucesso = "Lançamento de conta fixa salvo com sucesso!"
        self._carregar_ultimos()

    # --- cadastros rápidos ---
    def toggle_modal_loja(self):
        self.show_modal_loja = not self.show_modal_loja

    def upload_logo_loja(self, files: list[str]):
        # placeholder simples: recebe base64 já processado no client
        pass

    def salvar_nova_loja(self):
        if not self.nova_loja_nome.strip():
            return
        with rx.session() as session:
            nova = Store(
                name=self.nova_loja_nome.strip().upper(),
                weekly_limit=float(self.nova_loja_limite_semanal or 0),
                monthly_limit=float(self.nova_loja_limite_mensal or 0),
                avatar_color=cor_por_nome(self.nova_loja_nome),
                logo_b64=self.nova_loja_logo_b64 or None,
                created_by=self.user_id,
                created_by_operator=(self.role == "operator"),
            )
            session.add(nova)
            session.commit()
            session.refresh(nova)
            self.log_auditoria(session, "create", "store", nova.id, f"Loja criada: {nova.name}")
            session.commit()
        self.nova_loja_nome = ""
        self.nova_loja_limite_semanal = ""
        self.nova_loja_limite_mensal = ""
        self.nova_loja_logo_b64 = ""
        self.show_modal_loja = False
        self.carregar()

    def remover_loja(self, loja_id: str):
        if self.role not in ("admin", "operator"):
            return
        with rx.session() as session:
            loja = session.get(Store, int(loja_id))
            if loja:
                loja.active = False
                session.add(loja)
                self.log_auditoria(session, "delete", "store", loja.id, f"Loja removida: {loja.name}")
                session.commit()
        if self.selected_store_id == loja_id:
            self.selected_store_id = ""
        self.carregar()

    def remover_loja_selecionada(self):
        if not self.selected_store_id:
            return
        self.remover_loja(self.selected_store_id)

    def toggle_modal_conta_fixa(self):
        self.show_modal_conta_fixa = not self.show_modal_conta_fixa

    def salvar_nova_conta_fixa(self):
        if not (self.selected_store_id and self.nova_conta_nome.strip()):
            return
        with rx.session() as session:
            nova = FixedExpense(
                store_id=int(self.selected_store_id),
                name=self.nova_conta_nome.strip(),
                amount=float(self.nova_conta_valor or 0),
                due_day=self.nova_conta_dia,
                payment_method=self.nova_conta_forma,
                created_by=self.user_id,
                created_by_operator=(self.role == "operator"),
            )
            session.add(nova)
            session.commit()
            session.refresh(nova)
            self.log_auditoria(session, "create", "fixed_expense", nova.id, f"Conta fixa criada: {nova.name}")
            session.commit()
        self.nova_conta_nome = ""
        self.nova_conta_valor = ""
        self.nova_conta_dia = ""
        self.show_modal_conta_fixa = False
        self._carregar_contas_fixas_da_loja()

    def toggle_modal_distribuidora(self):
        self.show_modal_distribuidora = not self.show_modal_distribuidora

    def salvar_nova_distribuidora(self):
        if not self.nova_distribuidora_nome.strip():
            return
        with rx.session() as session:
            nova = Distributor(
                name=self.nova_distribuidora_nome.strip().upper(),
                created_by=self.user_id,
                created_by_operator=(self.role == "operator"),
            )
            session.add(nova)
            session.commit()
            session.refresh(nova)
            self.log_auditoria(session, "create", "distributor", nova.id, f"Distribuidora criada: {nova.name}")
            session.commit()
        self.nova_distribuidora_nome = ""
        self.show_modal_distribuidora = False
        self.carregar()

    def toggle_modal_tipo(self):
        self.show_modal_tipo = not self.show_modal_tipo

    def salvar_novo_tipo(self):
        if not self.novo_tipo_nome.strip():
            return
        with rx.session() as session:
            novo = ExpenseType(
                name=self.novo_tipo_nome.strip().upper(),
                category=self.novo_tipo_categoria,
                created_by=self.user_id,
                created_by_operator=(self.role == "operator"),
            )
            session.add(novo)
            session.commit()
            session.refresh(novo)
            self.log_auditoria(session, "create", "expense_type", novo.id, f"Tipo criado: {novo.name}")
            session.commit()
        self.novo_tipo_nome = ""
        self.show_modal_tipo = False
        self.carregar()


# ---------------------------------------------------------------------------
# Contas a Pagar
# ---------------------------------------------------------------------------
class ContasPagarState(AppState):
    filtro_loja: str = "Todas"
    filtro_status: str = "todas"  # todas | pendentes | pagas
    filtro_tipo: str = "todas"  # todas | fixas | boletos
    ordenar_por: str = "vencimento"  # vencimento | valor
    data_inicio: str = ""
    data_fim: str = ""
    lojas_options: list[str] = []
    lojas_full: list[dict] = []
    distribuidoras_options: list[dict] = []
    tipos_despesa_options: list[dict] = []
    contas: list[dict] = []
    contas_proximas: list[dict] = []

    show_drawer: bool = False
    conta_selecionada: dict = {}

    show_form_modal: bool = False
    form_modo: str = "novo"  # novo | editar
    form_tipo: str = "fixa"  # fixa | boleto
    form_id: int = 0
    form_loja_id: str = ""
    form_nome: str = ""
    form_valor: str = ""
    form_dia: str = ""
    form_data: str = ""
    form_forma: str = "PIX"
    form_distribuidor_id: str = ""
    form_tipo_despesa_id: str = ""
    form_obs: str = ""

    def carregar(self):
        with rx.session() as session:
            lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            loja_map = {s.id: s for s in lojas}
            self.lojas_options = ["Todas"] + [s.name for s in lojas]
            self.lojas_full = [{"id": str(s.id), "name": s.name} for s in lojas]
            self.distribuidoras_options = [
                {"id": str(d.id), "name": d.name}
                for d in session.exec(select(Distributor).where(Distributor.active == True)).all()  # noqa: E712
            ]
            self.tipos_despesa_options = [
                {"id": str(t.id), "name": t.name}
                for t in session.exec(select(ExpenseType).where(ExpenseType.active == True)).all()  # noqa: E712
            ]
            hoje = date.today()

            linhas = []

            # --- contas fixas ---
            if self.filtro_tipo in ("todas", "fixas"):
                fixas = session.exec(select(FixedExpense).where(FixedExpense.active == True)).all()  # noqa: E712
                for f in fixas:
                    loja = loja_map.get(f.store_id)
                    if not loja:
                        continue
                    if self.filtro_loja != "Todas" and loja.name != self.filtro_loja:
                        continue
                    if self.filtro_status == "pendentes" and f.is_paid:
                        continue
                    if self.filtro_status == "pagas" and not f.is_paid:
                        continue
                    venc = proximo_vencimento_mensal(f.due_day, hoje)
                    linhas.append(
                        {
                            "id": f.id,
                            "tipo": "Conta Fixa",
                            "loja": loja.name,
                            "loja_cor": loja.avatar_color,
                            "nome": f.name,
                            "valor": fmt_moeda(f.amount),
                            "valor_num": f.amount,
                            "vencimento": venc.strftime("%d/%m/%Y") if venc else "-",
                            "vencimento_iso": venc.isoformat() if venc else "",
                            "dias": dias_restantes(venc) if venc else 999,
                            "cor": cor_semaforo(venc) if venc else "#6C757D",
                            "status_txt": status_semaforo(venc) if venc else "sem data",
                            "forma_pgto": f.payment_method,
                            "pago": f.is_paid,
                            "observacoes": f.notes,
                        }
                    )

            # --- boletos de distribuidoras ---
            if self.filtro_tipo in ("todas", "boletos"):
                dists = {d.id: d.name for d in session.exec(select(Distributor)).all()}
                q = select(BoletoEntry)
                if self.data_inicio:
                    try:
                        q = q.where(BoletoEntry.boleto_date >= datetime.strptime(self.data_inicio, "%Y-%m-%d").date())
                    except ValueError:
                        pass
                if self.data_fim:
                    try:
                        q = q.where(BoletoEntry.boleto_date <= datetime.strptime(self.data_fim, "%Y-%m-%d").date())
                    except ValueError:
                        pass
                boletos = session.exec(q).all()
                for b in boletos:
                    loja = loja_map.get(b.store_id)
                    if not loja:
                        continue
                    if self.filtro_loja != "Todas" and loja.name != self.filtro_loja:
                        continue
                    if self.filtro_status == "pendentes" and b.is_paid:
                        continue
                    if self.filtro_status == "pagas" and not b.is_paid:
                        continue
                    venc = b.boleto_date
                    nome_base = dists.get(b.distributor_id, "Distribuidora")
                    if b.total_parcelas and b.total_parcelas > 1:
                        nome_base = f"{nome_base} ({b.parcela_num}/{b.total_parcelas})"
                    linhas.append(
                        {
                            "id": b.id,
                            "tipo": "Boleto",
                            "loja": loja.name,
                            "loja_cor": loja.avatar_color,
                            "nome": nome_base,
                            "valor": fmt_moeda(b.amount),
                            "valor_num": b.amount,
                            "vencimento": venc.strftime("%d/%m/%Y"),
                            "vencimento_iso": venc.isoformat(),
                            "dias": dias_restantes(venc),
                            "cor": cor_semaforo(venc),
                            "status_txt": status_semaforo(venc),
                            "forma_pgto": b.payment_method,
                            "pago": b.is_paid,
                            "observacoes": b.notes,
                        }
                    )

            # --- filtro de período também aplicado às contas fixas, se ambos preenchidos ---
            if self.data_inicio and self.data_fim:
                try:
                    di = datetime.strptime(self.data_inicio, "%Y-%m-%d").date()
                    dfim = datetime.strptime(self.data_fim, "%Y-%m-%d").date()
                    linhas = [
                        l for l in linhas
                        if l["tipo"] == "Boleto" or (l["vencimento_iso"] and di <= date.fromisoformat(l["vencimento_iso"]) <= dfim)
                    ]
                except ValueError:
                    pass

            if self.ordenar_por == "valor":
                linhas.sort(key=lambda x: x["valor_num"], reverse=True)
            else:
                linhas.sort(key=lambda x: x["dias"])

            self.contas = linhas
            self.contas_proximas = [c for c in linhas if c["dias"] <= 5 and not c["pago"]][:8]

    @staticmethod
    def _prox_vencimento(due_day: str, hoje: date) -> Optional[date]:
        return proximo_vencimento_mensal(due_day, hoje)

    def abrir_loja(self, nome_loja: str):
        """Usado por outras páginas (Dashboard/Lojas) para pular direto para
        as contas de uma loja específica, ao clicar no nome dela."""
        self.filtro_loja = nome_loja
        self.filtro_status = "todas"
        self.filtro_tipo = "todas"
        self.carregar()
        return rx.redirect("/contas-pagar")

    def set_filtro_loja(self, v: str):
        self.filtro_loja = v
        self.carregar()

    def set_filtro_status(self, v: str):
        self.filtro_status = v
        self.carregar()

    def set_filtro_tipo(self, v: str):
        self.filtro_tipo = v
        self.carregar()

    def set_ordenar_por(self, v: str):
        self.ordenar_por = v
        self.carregar()

    def set_data_inicio(self, v: str):
        self.data_inicio = v
        self.carregar()

    def set_data_fim(self, v: str):
        self.data_fim = v
        self.carregar()

    def abrir_detalhe(self, conta: dict):
        self.conta_selecionada = conta
        self.show_drawer = True

    def fechar_detalhe(self):
        self.show_drawer = False

    def marcar_como_pago(self, tipo: str, conta_id: int):
        """Marca como paga a conta indicada. O tipo ('Conta Fixa' ou 'Boleto')
        evita confundir IDs de tabelas diferentes."""
        with rx.session() as session:
            if tipo == "Conta Fixa":
                conta = session.get(FixedExpense, conta_id)
                if conta:
                    conta.is_paid = True
                    conta.paid_at = datetime.utcnow()
                    conta.paid_by = self.user_id
                    session.add(conta)
                    self.log_auditoria(session, "pay", "fixed_expense", conta.id, f"Pago: {conta.name}")
                    session.commit()
            else:
                boleto = session.get(BoletoEntry, conta_id)
                if boleto:
                    boleto.is_paid = True
                    boleto.paid_at = datetime.utcnow()
                    boleto.paid_by = self.user_id
                    session.add(boleto)
                    self.log_auditoria(session, "pay", "boleto_entry", boleto.id, "Boleto pago")
                    session.commit()
        self.show_drawer = False
        self.carregar()

    def set_form_loja_id(self, v: str):
        self.form_loja_id = v

    def set_form_tipo(self, v):
        if isinstance(v, list):
            self.form_tipo = v[0] if v else "fixa"
        else:
            self.form_tipo = v

    def set_form_nome(self, v: str):
        self.form_nome = v

    def set_form_valor(self, v: str):
        self.form_valor = v

    def set_form_dia(self, v: str):
        self.form_dia = v

    def set_form_data(self, v: str):
        self.form_data = v

    def set_form_forma(self, v: str):
        self.form_forma = v

    def set_form_distribuidor_id(self, v: str):
        self.form_distribuidor_id = v

    def set_form_tipo_despesa_id(self, v: str):
        self.form_tipo_despesa_id = v

    def set_form_obs(self, v: str):
        self.form_obs = v

    def abrir_novo(self):
        self.form_modo = "novo"
        self.form_tipo = "fixa"
        self.form_id = 0
        self.form_loja_id = self.lojas_full[0]["id"] if self.lojas_full else ""
        self.form_nome = ""
        self.form_valor = ""
        self.form_dia = ""
        self.form_data = ""
        self.form_forma = "PIX"
        self.form_distribuidor_id = ""
        self.form_tipo_despesa_id = ""
        self.form_obs = ""
        self.show_form_modal = True

    def abrir_edicao_form(self, conta: dict):
        self.form_modo = "editar"
        self.form_id = conta["id"]
        self.form_valor = str(conta["valor_num"])
        self.form_obs = conta["observacoes"]
        if conta["tipo"] == "Conta Fixa":
            self.form_tipo = "fixa"
            self.form_nome = conta["nome"]
            self.form_forma = conta["forma_pgto"]
            with rx.session() as session:
                fixa = session.get(FixedExpense, conta["id"])
                if fixa:
                    self.form_dia = fixa.due_day
                    self.form_loja_id = str(fixa.store_id)
        else:
            self.form_tipo = "boleto"
            self.form_forma = conta["forma_pgto"]
            with rx.session() as session:
                boleto = session.get(BoletoEntry, conta["id"])
                if boleto:
                    self.form_data = boleto.boleto_date.isoformat()
                    self.form_distribuidor_id = str(boleto.distributor_id)
                    self.form_tipo_despesa_id = str(boleto.expense_type_id) if boleto.expense_type_id else ""
                    self.form_loja_id = str(boleto.store_id)
        self.show_form_modal = True

    def fechar_form(self):
        self.show_form_modal = False

    def salvar_form(self):
        if not self.form_loja_id:
            return
        try:
            valor = float(self.form_valor.replace(",", "."))
        except ValueError:
            valor = 0.0
        with rx.session() as session:
            if self.form_tipo == "fixa":
                if self.form_modo == "editar" and self.form_id:
                    obj = session.get(FixedExpense, self.form_id)
                else:
                    obj = FixedExpense(
                        store_id=int(self.form_loja_id),
                        created_by=self.user_id,
                        created_by_operator=(self.role == "operator"),
                    )
                if obj:
                    obj.name = self.form_nome.strip() or obj.name
                    obj.amount = valor
                    obj.due_day = self.form_dia
                    obj.payment_method = self.form_forma
                    obj.notes = self.form_obs
                    session.add(obj)
                    session.commit()
                    session.refresh(obj)
                    self.log_auditoria(session, "update" if self.form_modo == "editar" else "create", "fixed_expense", obj.id, obj.name)
                    session.commit()
            else:
                if not self.form_distribuidor_id or not self.form_data:
                    self.show_form_modal = False
                    self.carregar()
                    return
                try:
                    data_boleto = datetime.strptime(self.form_data, "%Y-%m-%d").date()
                except ValueError:
                    self.show_form_modal = False
                    return
                if self.form_modo == "editar" and self.form_id:
                    obj = session.get(BoletoEntry, self.form_id)
                else:
                    obj = BoletoEntry(store_id=int(self.form_loja_id), operator_id=self.user_id)
                if obj:
                    obj.store_id = int(self.form_loja_id)
                    obj.distributor_id = int(self.form_distribuidor_id)
                    obj.boleto_date = data_boleto
                    obj.amount = valor
                    obj.payment_method = self.form_forma
                    obj.expense_type_id = int(self.form_tipo_despesa_id) if self.form_tipo_despesa_id else None
                    obj.notes = self.form_obs
                    obj.week_period = periodo_semana_str(data_boleto)
                    session.add(obj)
                    session.commit()
                    session.refresh(obj)
                    self.log_auditoria(session, "update" if self.form_modo == "editar" else "create", "boleto_entry", obj.id, "Boleto")
                    session.commit()
        self.show_form_modal = False
        self.carregar()

    def excluir_conta(self, tipo: str, conta_id: int):
        """Exclui (desativa) a conta indicada. O tipo evita confundir IDs."""
        with rx.session() as session:
            if tipo == "Conta Fixa":
                conta = session.get(FixedExpense, conta_id)
                if conta:
                    conta.active = False
                    session.add(conta)
                    self.log_auditoria(session, "delete", "fixed_expense", conta.id, f"Removida: {conta.name}")
                    session.commit()
            else:
                boleto = session.get(BoletoEntry, conta_id)
                if boleto:
                    session.delete(boleto)
                    self.log_auditoria(session, "delete", "boleto_entry", conta_id, "Boleto removido")
                    session.commit()
        self.show_drawer = False
        self.carregar()

    def exportar_excel(self):
        import io
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Contas a Pagar"
        ws.append(["Loja", "Tipo", "Conta/Distribuidora", "Valor", "Vencimento", "Forma de Pagamento", "Status"])
        for c in self.contas:
            ws.append([
                c["loja"], c["tipo"], c["nome"], c["valor_num"], c["vencimento"],
                c["forma_pgto"], "Pago" if c["pago"] else "Pendente",
            ])
        for col in ws.columns:
            largura = max(len(str(cell.value)) for cell in col if cell.value is not None) + 2
            ws.column_dimensions[col[0].column_letter].width = min(largura, 40)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return rx.download(data=buf.getvalue(), filename="contas_a_pagar.xlsx")


# ---------------------------------------------------------------------------
# Contas Fixas (cadastro/gestão)
# ---------------------------------------------------------------------------
class ContasFixasState(AppState):
    lojas_options: list[dict] = []
    filtro_loja_id: str = ""
    contas: list[dict] = []

    show_modal: bool = False
    edit_id: int = 0
    form_nome: str = ""
    form_valor: str = ""
    form_dia: str = ""
    form_forma: str = "PIX"

    def carregar(self):
        with rx.session() as session:
            lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            self.lojas_options = [{"id": str(s.id), "name": s.name} for s in lojas]
            if lojas and not self.filtro_loja_id:
                self.filtro_loja_id = str(lojas[0].id)
        self._carregar_contas()

    def set_filtro_loja_id(self, v: str):
        self.filtro_loja_id = v
        self._carregar_contas()

    def _carregar_contas(self):
        if not self.filtro_loja_id:
            self.contas = []
            return
        with rx.session() as session:
            contas = session.exec(
                select(FixedExpense).where(
                    FixedExpense.store_id == int(self.filtro_loja_id),
                    FixedExpense.active == True,  # noqa: E712
                )
            ).all()
            self.contas = [
                {
                    "id": c.id,
                    "nome": c.name,
                    "valor": fmt_moeda(c.amount),
                    "valor_num": c.amount,
                    "dia": c.due_day,
                    "forma": c.payment_method,
                    "pago": c.is_paid,
                    "criado_por_operador": c.created_by_operator,
                    "pode_editar": pode_editar_item(self.role, self.user_id, c.created_by),
                }
                for c in contas
            ]

    def set_form_nome(self, v: str):
        self.form_nome = v

    def set_form_valor(self, v: str):
        self.form_valor = v

    def set_form_dia(self, v: str):
        self.form_dia = v

    def set_form_forma(self, v: str):
        self.form_forma = v

    def abrir_novo(self):
        self.edit_id = 0
        self.form_nome = ""
        self.form_valor = ""
        self.form_dia = ""
        self.form_forma = "PIX"
        self.show_modal = True

    def abrir_edicao(self, conta: dict):
        self.edit_id = conta["id"]
        self.form_nome = conta["nome"]
        self.form_valor = str(conta["valor_num"])
        self.form_dia = conta["dia"]
        self.form_forma = conta["forma"]
        self.show_modal = True

    def fechar_modal(self):
        self.show_modal = False

    def salvar(self):
        if not self.filtro_loja_id or not self.form_nome.strip():
            return
        with rx.session() as session:
            if self.edit_id:
                conta = session.get(FixedExpense, self.edit_id)
            else:
                conta = FixedExpense(
                    store_id=int(self.filtro_loja_id),
                    created_by=self.user_id,
                    created_by_operator=(self.role == "operator"),
                )
            if conta:
                conta.name = self.form_nome.strip()
                try:
                    conta.amount = float(self.form_valor.replace(",", "."))
                except ValueError:
                    pass
                conta.due_day = self.form_dia
                conta.payment_method = self.form_forma
                session.add(conta)
                session.commit()
                session.refresh(conta)
                acao = "update" if self.edit_id else "create"
                self.log_auditoria(session, acao, "fixed_expense", conta.id, conta.name)
                session.commit()
        self.show_modal = False
        self._carregar_contas()

    def excluir(self, conta_id: int):
        with rx.session() as session:
            conta = session.get(FixedExpense, conta_id)
            if conta:
                conta.active = False
                session.add(conta)
                self.log_auditoria(session, "delete", "fixed_expense", conta.id, f"Removida: {conta.name}")
                session.commit()
        self._carregar_contas()


# ---------------------------------------------------------------------------
# Lojas (gestão)
# ---------------------------------------------------------------------------
class LojasState(AppState):
    lojas: list[dict] = []

    show_modal: bool = False
    edit_id: int = 0
    form_nome: str = ""
    form_limite_semanal: str = ""
    form_limite_mensal: str = ""
    erro: str = ""

    def carregar(self):
        hoje = date.today()
        ini_mes = hoje.replace(day=1)
        fim_mes = (ini_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        with rx.session() as session:
            lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            resultado = []
            for s in lojas:
                # Gasto do mês: lançamentos com vencimento no mês + contas fixas ativas
                boletos = session.exec(
                    select(BoletoEntry).where(
                        BoletoEntry.store_id == s.id,
                        BoletoEntry.boleto_date >= ini_mes,
                        BoletoEntry.boleto_date <= fim_mes,
                    )
                ).all()
                fixas = session.exec(
                    select(FixedExpense).where(
                        FixedExpense.store_id == s.id,
                        FixedExpense.active == True,  # noqa: E712
                    )
                ).all()
                gasto = sum(b.amount for b in boletos) + sum(f.amount for f in fixas)
                percentual = (gasto / s.monthly_limit * 100) if s.monthly_limit else 0.0

                resultado.append(
                    {
                        "id": s.id,
                        "nome": s.name,
                        "limite_semanal": fmt_moeda(s.weekly_limit),
                        "limite_mensal": fmt_moeda(s.monthly_limit),
                        "limite_semanal_raw": s.weekly_limit or 0,
                        "limite_mensal_raw": s.monthly_limit or 0,
                        "iniciais": gerar_iniciais(s.name),
                        "cor": s.avatar_color,
                        "logo_b64": s.logo_b64 or "",
                        "criado_por_operador": s.created_by_operator,
                        "pode_editar": pode_editar_item(self.role, self.user_id, s.created_by),
                        "gasto_mes": fmt_moeda(gasto),
                        "percentual": round(percentual, 1),
                        "cor_barra": "red" if percentual >= 100 else ("amber" if percentual >= 80 else "green"),
                        "barra": int(min(percentual, 100)),
                        "largura_barra": f"{min(percentual, 100):.1f}%",
                        "excedido": bool(s.monthly_limit and gasto > s.monthly_limit),
                        "restante": fmt_moeda(max((s.monthly_limit or 0) - gasto, 0)),
                    }
                )
            self.lojas = resultado

    def set_form_nome(self, value: str):
        self.form_nome = value

    def set_form_limite_semanal(self, value: str):
        self.form_limite_semanal = value

    def set_form_limite_mensal(self, value: str):
        self.form_limite_mensal = value

    def abrir_novo(self):
        self.edit_id = 0
        self.form_nome = ""
        self.form_limite_semanal = ""
        self.form_limite_mensal = ""
        self.erro = ""
        self.show_modal = True

    def abrir_edicao(self, loja: dict):
        self.edit_id = loja["id"]
        self.form_nome = loja["nome"]
        self.form_limite_semanal = str(loja["limite_semanal_raw"])
        self.form_limite_mensal = str(loja["limite_mensal_raw"])
        self.erro = ""
        self.show_modal = True

    def fechar_modal(self):
        self.show_modal = False
        self.erro = ""

    def salvar(self):
        nome = self.form_nome.strip().upper()
        if not nome:
            self.erro = "Informe o nome da loja."
            return
        try:
            semanal = float((self.form_limite_semanal or "0").replace(",", "."))
            mensal = float((self.form_limite_mensal or "0").replace(",", "."))
        except ValueError:
            self.erro = "Os limites precisam ser números."
            return

        with rx.session() as session:
            duplicada = session.exec(
                select(Store).where(Store.name == nome, Store.id != (self.edit_id or 0))
            ).first()
            if duplicada:
                self.erro = "Já existe uma loja com esse nome."
                return

            if self.edit_id:
                loja = session.get(Store, self.edit_id)
            else:
                loja = Store(created_by=self.user_id, created_by_operator=(self.role == "operator"))

            loja.name = nome
            loja.weekly_limit = semanal
            loja.monthly_limit = mensal
            if not loja.avatar_color:
                loja.avatar_color = cor_por_nome(nome)
            session.add(loja)
            session.commit()
            session.refresh(loja)
            self.log_auditoria(
                session, "update" if self.edit_id else "create", "store", loja.id, loja.name
            )
            session.commit()

        self.erro = ""
        self.show_modal = False
        self.carregar()

    def ver_loja(self, nome: str):
        return [ContasPagarState.set_filtro_loja(nome), rx.redirect("/contas-pagar")]


# ---------------------------------------------------------------------------
# Relatório Semanal
# ---------------------------------------------------------------------------
class RelatorioSemanalState(AppState):
    lojas_options: list[dict] = []
    lojas_selecionadas: list[str] = []
    data_ref: str = ""
    periodo_label: str = ""
    linhas: list[dict] = []
    total_limite: str = "R$ 0,00"
    total_boletos: str = "R$ 0,00"
    total_fixas: str = "R$ 0,00"
    total_geral: str = "R$ 0,00"
    figura_tipos: go.Figure = go.Figure()
    figura_formas: go.Figure = go.Figure()

    def carregar(self):
        if not self.data_ref:
            self.data_ref = date.today().isoformat()
        hoje = date.fromisoformat(self.data_ref)
        ini = inicio_semana(hoje)
        fim = fim_semana(hoje)
        self.periodo_label = f"{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"

        with rx.session() as session:
            todas_lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            self.lojas_options = [{"id": str(s.id), "name": s.name} for s in todas_lojas]
            if not self.lojas_selecionadas:
                self.lojas_selecionadas = [str(s.id) for s in todas_lojas]

            selecionadas_ids = {int(i) for i in self.lojas_selecionadas}
            lojas = [s for s in todas_lojas if s.id in selecionadas_ids] or todas_lojas

            tipos = session.exec(select(ExpenseType)).all()
            tipo_map = {t.id: t.name for t in tipos}

            linhas = []
            t_limite = t_bol = t_fix = 0.0
            fig_tipos = go.Figure()
            fig_formas = go.Figure()

            for loja in lojas:
                boletos = session.exec(
                    select(BoletoEntry).where(
                        BoletoEntry.store_id == loja.id,
                        BoletoEntry.boleto_date >= ini,
                        BoletoEntry.boleto_date <= fim,
                    )
                ).all()
                soma_boletos = sum(b.amount for b in boletos)
                fixas = session.exec(
                    select(FixedExpense).where(
                        FixedExpense.store_id == loja.id, FixedExpense.active == True  # noqa: E712
                    )
                ).all()
                soma_fixas_semanais = sum(
                    f.amount for f in fixas
                    if any(p in (f.due_day or "").upper() for p in ("SEMANAL", "SEGUNDA", "SEXTA"))
                )
                combinado = soma_boletos + soma_fixas_semanais
                status = "Excedido" if loja.weekly_limit and combinado > loja.weekly_limit else "Dentro do limite"
                linhas.append(
                    {
                        "loja": loja.name,
                        "cor": loja.avatar_color,
                        "limite": fmt_moeda(loja.weekly_limit),
                        "boletos": fmt_moeda(soma_boletos),
                        "fixas": fmt_moeda(soma_fixas_semanais),
                        "total": fmt_moeda(combinado),
                        "status": status,
                        "excedido": status == "Excedido",
                    }
                )
                t_limite += loja.weekly_limit
                t_bol += soma_boletos
                t_fix += soma_fixas_semanais

                dist_tipo: dict[str, float] = {}
                for b in boletos:
                    nome_tipo = tipo_map.get(b.expense_type_id, "Outros")
                    dist_tipo[nome_tipo] = dist_tipo.get(nome_tipo, 0.0) + b.amount
                if dist_tipo:
                    fig_tipos.add_bar(name=loja.name, x=list(dist_tipo.keys()), y=list(dist_tipo.values()))

                dist_forma: dict[str, float] = {}
                for f in fixas:
                    dist_forma[f.payment_method] = dist_forma.get(f.payment_method, 0.0) + f.amount
                if dist_forma:
                    fig_formas.add_bar(name=loja.name, x=list(dist_forma.keys()), y=list(dist_forma.values()))

            _formatar_figura_moeda(fig_tipos, "Sem boletos lançados nesta semana")
            _formatar_figura_moeda(fig_formas, "Sem contas fixas cadastradas nas lojas selecionadas")

            self.linhas = linhas
            self.total_limite = fmt_moeda(t_limite)
            self.total_boletos = fmt_moeda(t_bol)
            self.total_fixas = fmt_moeda(t_fix)
            self.total_geral = fmt_moeda(t_bol + t_fix)
            self.figura_tipos = fig_tipos
            self.figura_formas = fig_formas

    def toggle_loja(self, loja_id: str):
        if loja_id in self.lojas_selecionadas:
            self.lojas_selecionadas = [i for i in self.lojas_selecionadas if i != loja_id]
        else:
            self.lojas_selecionadas = self.lojas_selecionadas + [loja_id]
        self.carregar()

    def set_data_ref(self, v: str):
        if v:
            self.data_ref = v
            self.carregar()

    def semana_anterior(self):
        self.data_ref = (date.fromisoformat(self.data_ref) - timedelta(weeks=1)).isoformat()
        self.carregar()

    def semana_proxima(self):
        self.data_ref = (date.fromisoformat(self.data_ref) + timedelta(weeks=1)).isoformat()
        self.carregar()

    def semana_atual(self):
        self.data_ref = date.today().isoformat()
        self.carregar()


# ---------------------------------------------------------------------------
# Relatório Mensal (versão simplificada)
# ---------------------------------------------------------------------------
class RelatorioMensalState(AppState):
    lojas_options: list[dict] = []
    lojas_selecionadas: list[str] = []
    ano_selecionado: int = date.today().year
    mes_selecionado: int = date.today().month
    anos_disponiveis: list[str] = [str(y) for y in range(date.today().year - 3, date.today().year + 2)]
    meses_disponiveis: list[str] = [nome_mes(m) for m in range(1, 13)]
    periodo_label: str = ""
    linhas: list[dict] = []
    figura_tipos: go.Figure = go.Figure()
    figura_formas: go.Figure = go.Figure()

    @rx.var
    def mes_selecionado_nome(self) -> str:
        return nome_mes(self.mes_selecionado)

    def carregar(self):
        ano, mes = self.ano_selecionado, self.mes_selecionado
        self.periodo_label = f"{nome_mes(mes)} de {ano}"
        ini_mes = date(ano, mes, 1)
        prox_mes = mes % 12 + 1
        prox_ano = ano + (1 if mes == 12 else 0)
        fim_mes = date(prox_ano, prox_mes, 1) - timedelta(days=1)

        with rx.session() as session:
            todas_lojas = session.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            self.lojas_options = [{"id": str(s.id), "name": s.name} for s in todas_lojas]
            if not self.lojas_selecionadas:
                self.lojas_selecionadas = [str(s.id) for s in todas_lojas]

            selecionadas_ids = {int(i) for i in self.lojas_selecionadas}
            lojas = [s for s in todas_lojas if s.id in selecionadas_ids] or todas_lojas

            tipos = session.exec(select(ExpenseType)).all()
            tipo_map = {t.id: t.name for t in tipos}

            linhas = []
            fig_tipos = go.Figure()
            fig_formas = go.Figure()

            for loja in lojas:
                boletos = session.exec(
                    select(BoletoEntry).where(
                        BoletoEntry.store_id == loja.id,
                        BoletoEntry.boleto_date >= ini_mes,
                        BoletoEntry.boleto_date <= fim_mes,
                    )
                ).all()
                fixas = session.exec(
                    select(FixedExpense).where(
                        FixedExpense.store_id == loja.id, FixedExpense.active == True  # noqa: E712
                    )
                ).all()
                combinado = sum(b.amount for b in boletos) + sum(f.amount for f in fixas)
                status = "Excedido" if loja.monthly_limit and combinado > loja.monthly_limit else "Dentro do limite"
                linhas.append(
                    {
                        "loja": loja.name,
                        "limite": fmt_moeda(loja.monthly_limit),
                        "mes_atual": fmt_moeda(combinado),
                        "mes_nome": self.periodo_label,
                        "status": status,
                        "excedido": status == "Excedido",
                    }
                )

                dist_tipo: dict[str, float] = {}
                for b in boletos:
                    nome_tipo = tipo_map.get(b.expense_type_id, "Outros")
                    dist_tipo[nome_tipo] = dist_tipo.get(nome_tipo, 0.0) + b.amount
                if dist_tipo:
                    fig_tipos.add_bar(name=loja.name, x=list(dist_tipo.keys()), y=list(dist_tipo.values()))

                dist_forma: dict[str, float] = {}
                for f in fixas:
                    dist_forma[f.payment_method] = dist_forma.get(f.payment_method, 0.0) + f.amount
                if dist_forma:
                    fig_formas.add_bar(name=loja.name, x=list(dist_forma.keys()), y=list(dist_forma.values()))

            _formatar_figura_moeda(fig_tipos, "Sem boletos lançados neste mês")
            _formatar_figura_moeda(fig_formas, "Sem contas fixas cadastradas nas lojas selecionadas")

            self.linhas = linhas
            self.figura_tipos = fig_tipos
            self.figura_formas = fig_formas

    def toggle_loja(self, loja_id: str):
        if loja_id in self.lojas_selecionadas:
            self.lojas_selecionadas = [i for i in self.lojas_selecionadas if i != loja_id]
        else:
            self.lojas_selecionadas = self.lojas_selecionadas + [loja_id]
        self.carregar()

    def set_ano_selecionado(self, v: str):
        self.ano_selecionado = int(v)
        self.carregar()

    def set_mes_selecionado(self, v: str):
        self.mes_selecionado = self.meses_disponiveis.index(v) + 1
        self.carregar()

    def mes_anterior(self):
        total = self.ano_selecionado * 12 + (self.mes_selecionado - 1) - 1
        self.ano_selecionado = total // 12
        self.mes_selecionado = total % 12 + 1
        self.carregar()

    def mes_proximo(self):
        total = self.ano_selecionado * 12 + (self.mes_selecionado - 1) + 1
        self.ano_selecionado = total // 12
        self.mes_selecionado = total % 12 + 1
        self.carregar()

    def mes_atual(self):
        hoje = date.today()
        self.ano_selecionado = hoje.year
        self.mes_selecionado = hoje.month
        self.carregar()


# ---------------------------------------------------------------------------
# Usuários (admin: cria logins; qualquer usuário: troca a própria senha)
# ---------------------------------------------------------------------------
class UsuariosState(AppState):
    usuarios: list[dict] = []

    senha_atual: str = ""
    nova_senha: str = ""
    confirmar_senha: str = ""
    msg_senha: str = ""

    novo_usuario_nome: str = ""
    novo_usuario_username: str = ""
    novo_usuario_senha: str = ""
    novo_usuario_role: str = "operator"
    msg_novo_usuario: str = ""

    def carregar(self):
        if self.role != "admin":
            self.usuarios = []
            return
        with rx.session() as session:
            users = session.exec(select(User).order_by(User.username)).all()
            self.usuarios = [
                {
                    "id": u.id,
                    "username": u.username,
                    "display_name": u.display_name or u.username,
                    "role": u.role,
                    "role_label": {"admin": "Administrador", "operator": "Operador", "viewer": "Visualizador"}.get(u.role, u.role),
                    "active": u.active,
                }
                for u in users
            ]

    def set_senha_atual(self, v: str):
        self.senha_atual = v

    def set_nova_senha(self, v: str):
        self.nova_senha = v

    def set_confirmar_senha(self, v: str):
        self.confirmar_senha = v

    def trocar_minha_senha(self):
        self.msg_senha = ""
        if not self.nova_senha or len(self.nova_senha) < 6:
            self.msg_senha = "A nova senha precisa ter pelo menos 6 caracteres."
            return
        if self.nova_senha != self.confirmar_senha:
            self.msg_senha = "As senhas não coincidem."
            return
        with rx.session() as session:
            user = session.get(User, self.user_id)
            if not user or not verificar_senha(self.senha_atual, user.password_hash):
                self.msg_senha = "Senha atual incorreta."
                return
            user.password_hash = hash_senha(self.nova_senha)
            session.add(user)
            session.commit()
        self.senha_atual = ""
        self.nova_senha = ""
        self.confirmar_senha = ""
        self.msg_senha = "Senha alterada com sucesso!"

    def set_novo_usuario_nome(self, v: str):
        self.novo_usuario_nome = v

    def set_novo_usuario_username(self, v: str):
        self.novo_usuario_username = v

    def set_novo_usuario_senha(self, v: str):
        self.novo_usuario_senha = v

    def set_novo_usuario_role(self, v: str):
        self.novo_usuario_role = v

    def criar_usuario(self):
        self.msg_novo_usuario = ""
        if self.role != "admin":
            return
        if not self.novo_usuario_username.strip() or not self.novo_usuario_senha:
            self.msg_novo_usuario = "Preencha usuário e senha."
            return
        if len(self.novo_usuario_senha) < 6:
            self.msg_novo_usuario = "A senha precisa ter pelo menos 6 caracteres."
            return
        if self.novo_usuario_role not in ("operator", "viewer"):
            self.msg_novo_usuario = "Nível de acesso inválido."
            return
        with rx.session() as session:
            existente = session.exec(
                select(User).where(User.username == self.novo_usuario_username.strip())
            ).first()
            if existente:
                self.msg_novo_usuario = "Já existe um usuário com esse login."
                return
            novo = User(
                username=self.novo_usuario_username.strip(),
                password_hash=hash_senha(self.novo_usuario_senha),
                role=self.novo_usuario_role,
                display_name=self.novo_usuario_nome.strip() or self.novo_usuario_username.strip(),
            )
            session.add(novo)
            session.commit()
            session.refresh(novo)
            self.log_auditoria(session, "create", "user", novo.id, f"Usuário criado: {novo.username}")
            session.commit()
        self.novo_usuario_nome = ""
        self.novo_usuario_username = ""
        self.novo_usuario_senha = ""
        self.msg_novo_usuario = "Usuário criado com sucesso!"
        self.carregar()

    def alternar_ativo(self, user_id: int):
        if self.role != "admin" or user_id == self.user_id:
            return
        with rx.session() as session:
            user = session.get(User, user_id)
            if user:
                user.active = not user.active
                session.add(user)
                self.log_auditoria(session, "update", "user", user.id, f"Ativo alterado: {user.username}")
                session.commit()
        self.carregar()


# ---------------------------------------------------------------------------
# Edição de limites de loja (Item 15) — modal usado pelo dashboard
# ---------------------------------------------------------------------------
class EditarLimitesState(AppState):
    loja_editar_id: int = 0
    loja_editar_nome: str = ""
    limite_mensal_atual: float = 0.0
    limite_caixa_atual: float = 0.0
    novo_limite_mensal: str = ""
    novo_limite_caixa: str = ""
    edit_error: str = ""
    show_edit_modal: bool = False

    def abrir_edicao_loja(self, loja_id: int, loja_nome: str, limite_mensal: float, limite_caixa: float):
        """Abre o modal de edição de limites para a loja especificada."""
        self.loja_editar_id = loja_id
        self.loja_editar_nome = loja_nome
        self.limite_mensal_atual = limite_mensal
        self.limite_caixa_atual = limite_caixa
        self.novo_limite_mensal = str(limite_mensal)
        self.novo_limite_caixa = str(limite_caixa)
        self.edit_error = ""
        self.show_edit_modal = True

    def fechar_edicao_loja(self):
        """Fecha o modal de edição sem salvar."""
        self.show_edit_modal = False
        self.edit_error = ""

    def set_novo_limite_mensal(self, value: str):
        self.novo_limite_mensal = value

    def set_novo_limite_caixa(self, value: str):
        self.novo_limite_caixa = value

    def salvar_limites_loja(self):
        """Salva os novos limites da loja com validação."""
        self.edit_error = ""

        if not self.novo_limite_mensal.strip():
            self.edit_error = "Limite mensal é obrigatório."
            return

        if not self.novo_limite_caixa.strip():
            self.edit_error = "Limite por Caixa é obrigatório."
            return

        try:
            novo_mes = float(self.novo_limite_mensal.replace(",", "."))
        except ValueError:
            self.edit_error = "Limite mensal deve ser um número válido."
            return

        try:
            novo_caixa = float(self.novo_limite_caixa.replace(",", "."))
        except ValueError:
            self.edit_error = "Limite por Caixa deve ser um número válido."
            return

        if novo_mes < 0:
            self.edit_error = "Limite mensal deve ser um valor positivo."
            return

        if novo_caixa < 0:
            self.edit_error = "Limite por Caixa deve ser um valor positivo."
            return

        if novo_caixa > novo_mes:
            self.edit_error = "Limite por Caixa não pode ser maior que o Limite mensal."
            return

        with rx.session() as session:
            loja = session.get(Store, self.loja_editar_id)
            if not loja:
                self.edit_error = "Loja não encontrada."
                return

            mudou_mes = novo_mes != loja.monthly_limit
            mudou_caixa = novo_caixa != loja.cash_limit

            if mudou_mes or mudou_caixa:
                desc_parts = [f"Edição de limites - {self.loja_editar_nome}"]
                if mudou_mes:
                    desc_parts.append(f"Limite mensal: R$ {loja.monthly_limit:,.2f} → R$ {novo_mes:,.2f}")
                if mudou_caixa:
                    desc_parts.append(f"Limite por Caixa: R$ {loja.cash_limit:,.2f} → R$ {novo_caixa:,.2f}")

                loja.monthly_limit = novo_mes
                loja.cash_limit = novo_caixa
                session.add(loja)
                session.commit()
                session.refresh(loja)

                self.log_auditoria(
                    session,
                    "update",
                    "store",
                    loja.id,
                    " | ".join(desc_parts),
                )
                session.commit()

        self.show_edit_modal = False
        self.edit_error = ""
        self.carregar()