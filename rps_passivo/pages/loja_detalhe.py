"""Página de gastos de uma loja: indicadores, gráficos por mês e contas."""
from datetime import date, timedelta

import plotly.graph_objects as go
import reflex as rx
from sqlmodel import select

from ..models import Store, BoletoEntry, FixedExpense, ExpenseType, Distributor
from ..state import AppState, LancamentosState
from .contas_estado import ContasState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..utils.helpers import fmt_moeda, proximo_vencimento_mensal
from ..utils.graficos import travar

VERMELHO = "#E31E24"
VERDE = "#00A651"
AZUL = "#3B82F6"
TEXTO_GRAFICO = "#94A3B8"
GRADE_GRAFICO = "rgba(148,163,184,0.18)"
TRANSPARENTE = "rgba(0,0,0,0)"
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _add_meses(ano: int, mes: int, n: int) -> tuple[int, int]:
    """Soma n meses a (ano, mes)."""
    total = ano * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def _ultimo_dia(ano: int, mes: int) -> date:
    prox_ano, prox_mes = _add_meses(ano, mes, 1)
    return date(prox_ano, prox_mes, 1) - timedelta(days=1)


def _brl0(v: float) -> str:
    """Valor inteiro em reais no formato brasileiro, ex.: R$ 1.234."""
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def _layout_grafico(fig: go.Figure, **extra) -> None:
    """Fundo transparente, textos neutros e gráfico travado para todos os perfis."""
    fig.update_layout(
        paper_bgcolor=TRANSPARENTE,
        plot_bgcolor=TRANSPARENTE,
        font={"family": "Inter, sans-serif", "color": TEXTO_GRAFICO},
        **extra,
    )
    travar(fig)


def _itens_mes(boletos, fixas, tipos, dists, ini, fim, mes_atual, hoje) -> dict:
    """Soma e lista os lançamentos de um período.

    Contas fixas são recorrentes: entram em todos os meses. O status de pago
    das fixas vale só para o mês atual.
    """
    pendentes, pagas = [], []
    por_tipo: dict[str, float] = {}
    gasto = pago = 0.0

    for b in boletos:
        if not (ini <= b.boleto_date <= fim):
            continue
        nome = dists.get(b.distributor_id, "Distribuidora")
        if b.total_parcelas and b.total_parcelas > 1:
            nome = f"{nome} ({b.parcela_num}/{b.total_parcelas})"
        item = {
            "id": b.id,
            "tipo": "Despesa",
            "nome": nome,
            "valor": fmt_moeda(b.amount),
            "venc": b.boleto_date.strftime("%d/%m/%Y"),
        }
        gasto += b.amount
        cat = tipos.get(b.expense_type_id, "Outros")
        por_tipo[cat] = por_tipo.get(cat, 0.0) + b.amount
        if b.is_paid:
            pago += b.amount
            pagas.append(item)
        else:
            pendentes.append(item)

    for f in fixas:
        venc = proximo_vencimento_mensal(f.due_day, hoje)
        item = {
            "id": f.id,
            "tipo": "Conta Fixa",
            "nome": f.name,
            "valor": fmt_moeda(f.amount),
            "venc": venc.strftime("%d/%m/%Y") if venc else "-",
        }
        gasto += f.amount
        por_tipo["Contas fixas"] = por_tipo.get("Contas fixas", 0.0) + f.amount
        if mes_atual and f.is_paid:
            pago += f.amount
            pagas.append(item)
        else:
            pendentes.append(item)

    return {
        "pendentes": pendentes,
        "pagas": pagas,
        "por_tipo": por_tipo,
        "gasto": gasto,
        "pago": pago,
    }


class LojaDetalheState(AppState):
    loja_pk: int = 0
    loja_nome: str = ""
    limite_mensal: str = "R$ 0,00"
    gasto_mes: str = "R$ 0,00"
    pago_mes: str = "R$ 0,00"
    falta_mes: str = "R$ 0,00"
    contas_pendentes: list[dict] = []
    contas_pagas: list[dict] = []

    # Navegação de mês (0 = mês atual)
    mes_offset: int = 0
    mes_label: str = ""

    figura_mes: go.Figure = go.Figure()
    figura_tipos: go.Figure = go.Figure()
    figura_anual: go.Figure = go.Figure()

    def carregar(self):
        try:
            self.loja_pk = int(self.router.page.params.get("loja_id", "0"))
        except ValueError:
            self.loja_pk = 0

        hoje = date.today()
        ini_atual = hoje.replace(day=1)
        fim_atual = _ultimo_dia(hoje.year, hoje.month)

        ano_sel, mes_sel = _add_meses(hoje.year, hoje.month, self.mes_offset)
        ini_sel = date(ano_sel, mes_sel, 1)
        fim_sel = _ultimo_dia(ano_sel, mes_sel)
        self.mes_label = f"{MESES[mes_sel - 1]}/{ano_sel}"

        with rx.session() as session:
            loja = session.get(Store, self.loja_pk)
            if not loja:
                self.loja_nome = "Loja não encontrada"
                self.contas_pendentes = []
                self.contas_pagas = []
                return

            self.loja_nome = loja.name
            self.limite_mensal = fmt_moeda(loja.monthly_limit)

            tipos = {t.id: t.name for t in session.exec(select(ExpenseType)).all()}
            dists = {d.id: d.name for d in session.exec(select(Distributor)).all()}
            boletos_todos = session.exec(
                select(BoletoEntry).where(
                    BoletoEntry.store_id == loja.id,
                    BoletoEntry.deleted_at == None,  # noqa: E711 (fora da lixeira)
                )
            ).all()
            fixas = session.exec(
                select(FixedExpense).where(
                    FixedExpense.store_id == loja.id,
                    FixedExpense.active == True,  # noqa: E712
                    FixedExpense.deleted_at == None,  # noqa: E711
                )
            ).all()

            # Indicadores e abas: sempre o mês atual
            atual = _itens_mes(boletos_todos, fixas, tipos, dists, ini_atual, fim_atual, True, hoje)
            self.gasto_mes = fmt_moeda(atual["gasto"])
            self.pago_mes = fmt_moeda(atual["pago"])
            self.falta_mes = fmt_moeda(max(atual["gasto"] - atual["pago"], 0.0))
            self.contas_pendentes = atual["pendentes"]
            self.contas_pagas = atual["pagas"]

            # Gráficos de rosca e pizza: mês selecionado com as setas
            sel = _itens_mes(
                boletos_todos, fixas, tipos, dists, ini_sel, fim_sel,
                mes_sel == hoje.month and ano_sel == hoje.year, hoje,
            )
            pago_sel = sel["pago"]
            pend_sel = max(sel["gasto"] - sel["pago"], 0.0)
            total_sel = pago_sel + pend_sel

            fig_mes = go.Figure()
            fig_mes.add_pie(
                labels=["Pago", "A pagar"],
                values=[round(pago_sel, 2), round(pend_sel, 2)],
                hole=0.6,
                marker=dict(colors=[VERDE, VERMELHO]),
                textinfo="percent",
                texttemplate="%{percent}" if total_sel > 0 else "",
                sort=False,
            )
            _layout_grafico(
                fig_mes,
                height=260, margin=dict(t=10, l=10, r=10, b=30),
                legend={"orientation": "h", "y": -0.15, "x": 0.5, "xanchor": "center"},
                annotations=[
                    dict(
                        text=_brl0(total_sel),
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=15, color=TEXTO_GRAFICO),
                    )
                ],
            )
            self.figura_mes = fig_mes

            fig_tipos = go.Figure()
            if sel["por_tipo"]:
                fig_tipos.add_pie(
                    labels=list(sel["por_tipo"].keys()),
                    values=[round(v, 2) for v in sel["por_tipo"].values()],
                    hole=0.35,
                )
            _layout_grafico(
                fig_tipos,
                height=260, margin=dict(t=10, l=10, r=10, b=30),
                legend={"orientation": "h", "y": -0.15, "x": 0.5, "xanchor": "center"},
            )
            self.figura_tipos = fig_tipos

            # Próximos 12 meses a partir do mês atual
            labels, fixo_vals, var_vals, total_vals = [], [], [], []
            total_fixo = sum(f.amount for f in fixas)
            for k in range(12):
                a, m = _add_meses(hoje.year, hoje.month, k)
                ini_k = date(a, m, 1)
                fim_k = _ultimo_dia(a, m)
                var_k = sum(b.amount for b in boletos_todos if ini_k <= b.boleto_date <= fim_k)
                labels.append(f"{MESES[m - 1]}/{str(a)[2:]}")
                fixo_vals.append(round(total_fixo, 2))
                var_vals.append(round(var_k, 2))
                total_vals.append(round(total_fixo + var_k, 2))

            fig_anual = go.Figure()
            fig_anual.add_bar(name="Contas fixas", x=labels, y=fixo_vals, marker_color=AZUL)
            fig_anual.add_bar(name="Variáveis", x=labels, y=var_vals, marker_color=VERMELHO)
            fig_anual.add_scatter(
                name="Total",
                x=labels,
                y=total_vals,
                mode="lines+markers+text",
                text=[_brl0(v) for v in total_vals],
                textposition="top center",
                line=dict(color=TEXTO_GRAFICO),
                marker=dict(size=7),
            )
            _layout_grafico(
                fig_anual,
                barmode="group", bargap=0.55, bargroupgap=0.05,
                height=380, margin=dict(t=40, l=60, r=20, b=50),
                legend={"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
            )
            fig_anual.update_yaxes(tickprefix="R$ ", tickformat=",.0f", gridcolor=GRADE_GRAFICO)
            fig_anual.update_xaxes(gridcolor=GRADE_GRAFICO)
            self.figura_anual = fig_anual

    def mes_anterior(self):
        self.mes_offset -= 1
        self.carregar()

    def mes_proximo(self):
        self.mes_offset += 1
        self.carregar()

    def mes_atual(self):
        self.mes_offset = 0
        self.carregar()

    def pagar(self, tipo: str, conta_id: int):
        """Usa a mesma regra da página Contas (inclui o registro mensal das fixas)."""
        kind = "fixa" if tipo == "Conta Fixa" else "boleto"
        competencia = date.today().replace(day=1).isoformat()
        return [
            ContasState.pagar(kind, str(conta_id), competencia),
            LojaDetalheState.carregar,
        ]

    def novo_lancamento(self):
        return [
            LancamentosState.set_selected_store_id(str(self.loja_pk)),
            rx.redirect("/lancamentos"),
        ]

    def ver_contas_a_pagar(self):
        return rx.redirect(f"/contas?loja={self.loja_pk}")


def _linha_pendente(c: dict) -> rx.Component:
    return rx.hstack(
        rx.badge(c["tipo"], variant="soft"),
        rx.text(c["nome"], size="2", weight="bold"),
        rx.spacer(),
        rx.text(c["valor"], size="2"),
        rx.text(c["venc"], size="1", color=rx.color("gray", 9)),
        rx.button(
            "Pagar",
            size="1",
            variant="soft",
            color_scheme="green",
            on_click=lambda: LojaDetalheState.pagar(c["tipo"], c["id"]),
        ),
        width="100%",
        align="center",
        padding="0.5em 0",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
    )


def _linha_paga(c: dict) -> rx.Component:
    return rx.hstack(
        rx.badge(c["tipo"], variant="soft"),
        rx.text(c["nome"], size="2", weight="bold"),
        rx.spacer(),
        rx.text(c["valor"], size="2"),
        rx.text(c["venc"], size="1", color=rx.color("gray", 9)),
        rx.badge("Pago", color_scheme="green"),
        width="100%",
        align="center",
        padding="0.5em 0",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
    )


def _indicador(titulo: str, valor) -> rx.Component:
    return card_container(
        rx.text(titulo, size="1", color=rx.color("gray", 9)),
        rx.heading(valor, size="5"),
    )


def _cabecalho() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon("arrow-left", size=16), "Lojas",
            variant="soft",
            on_click=rx.redirect("/lojas"),
        ),
        rx.heading(LojaDetalheState.loja_nome, size="6"),
        rx.spacer(),
        rx.button(
            rx.icon("plus", size=16), "Novo lançamento",
            on_click=LojaDetalheState.novo_lancamento,
            style={"background": VERMELHO, "color": "white"},
        ),
        rx.button(
            "Ver contas da loja",
            variant="soft",
            on_click=LojaDetalheState.ver_contas_a_pagar,
        ),
        width="100%",
        align="center",
        wrap="wrap",
        spacing="2",
    )


def _indicadores() -> rx.Component:
    return rx.grid(
        _indicador("Limite mensal", LojaDetalheState.limite_mensal),
        _indicador("Gasto no mês", LojaDetalheState.gasto_mes),
        _indicador("Pago no mês", LojaDetalheState.pago_mes),
        _indicador("Falta pagar", LojaDetalheState.falta_mes),
        columns=rx.breakpoints(initial="2", md="4"),
        spacing="3",
        width="100%",
    )


def _card_mes() -> rx.Component:
    """Pago x a pagar do mês selecionado (rosca), com setas para trocar de mês."""
    return card_container(
        rx.hstack(
            rx.icon_button(
                rx.icon("chevron-left", size=16),
                variant="soft",
                on_click=LojaDetalheState.mes_anterior,
            ),
            rx.heading(LojaDetalheState.mes_label, size="3"),
            rx.icon_button(
                rx.icon("chevron-right", size=16),
                variant="soft",
                on_click=LojaDetalheState.mes_proximo,
            ),
            rx.spacer(),
            rx.cond(
                LojaDetalheState.mes_offset != 0,
                rx.button("Mês atual", size="1", variant="soft", on_click=LojaDetalheState.mes_atual),
            ),
            width="100%",
            align="center",
            spacing="2",
        ),
        rx.plotly(data=LojaDetalheState.figura_mes),
    )


def _card_tipos() -> rx.Component:
    return card_container(
        rx.heading("Gastos por tipo", size="3", margin_bottom="0.4em"),
        rx.plotly(data=LojaDetalheState.figura_tipos),
    )


def _graficos() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.box(_card_mes(), flex="3 1 380px", min_width="0"),
            rx.box(_card_tipos(), flex="2 1 260px", min_width="0"),
            wrap="wrap",
            spacing="3",
            width="100%",
            align="start",
        ),
        card_container(
            rx.heading("Contas a pagar nos próximos 12 meses", size="3", margin_bottom="0.4em"),
            rx.plotly(data=LojaDetalheState.figura_anual),
        ),
        spacing="3",
        width="100%",
    )


def _abas() -> rx.Component:
    return card_container(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("A pagar", value="pendentes"),
                rx.tabs.trigger("Pagas no mês", value="pagas"),
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.foreach(LojaDetalheState.contas_pendentes, _linha_pendente),
                    width="100%",
                ),
                value="pendentes",
                padding_top="1em",
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.foreach(LojaDetalheState.contas_pagas, _linha_paga),
                    width="100%",
                ),
                value="pagas",
                padding_top="1em",
            ),
            default_value="pendentes",
            width="100%",
        ),
    )


def loja_detalhe_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            _cabecalho(),
            _indicadores(),
            _graficos(),
            _abas(),
            spacing="4",
            width="100%",
        ),
    )