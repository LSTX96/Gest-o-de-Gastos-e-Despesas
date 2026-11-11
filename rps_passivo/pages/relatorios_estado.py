"""Estado da página Relatórios: roscas por período, linhas do tempo, indicadores e análise."""
from collections import defaultdict
from datetime import date, timedelta

import plotly.graph_objects as go
import reflex as rx
from sqlmodel import select

from ..models import (
    Store, Distributor, ExpenseType, BoletoEntry, FixedExpense, FixedExpensePayment,
)
from ..state import AppState
from ..utils import analise
from ..utils.graficos import travar
from ..utils.helpers import fmt_moeda
from .contas_estado import _norm, _add_meses, _ultimo_dia, _dia_venc
from .relatorios_kpis import pontualidade, aging, disciplina

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
MESES_ABREV = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
CORES = ["#E31E24", "#F59E0B", "#3B82F6", "#10B981", "#8B5CF6", "#EC4899", "#14B8A6", "#64748B"]
AZUL = "#3B82F6"
VERMELHO = "#E31E24"
CINZA = "#94A3B8"
GRADE = "rgba(148,163,184,0.18)"
TRANSPARENTE = "rgba(0,0,0,0)"


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def _segunda(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _meses_entre(ini: date, fim: date):
    a, m = ini.year, ini.month
    while (a, m) <= (fim.year, fim.month):
        yield a, m
        a, m = _add_meses(a, m, 1)


def _br(d: date) -> str:
    return d.strftime("%d/%m")


def _rotulo_mes(a: int, m: int) -> str:
    return f"{MESES_ABREV[m - 1]}/{str(a)[2:]}"


def _brl0(v: float) -> str:
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def _carregar_dados(loja_f) -> dict:
    """Lê tudo do banco uma vez: lojas ativas, despesas fora da lixeira e pagamentos."""
    with rx.session() as s:
        lojas = {l.id: l for l in s.exec(select(Store)).all() if l.active}
        dists = {d.id: _norm(d.name) for d in s.exec(select(Distributor)).all()}
        tipos = {t.id: _norm(t.name) for t in s.exec(select(ExpenseType)).all()}

        def loja_ok(store_id: int) -> bool:
            return store_id in lojas and (loja_f is None or store_id == loja_f)

        boletos = [
            b for b in s.exec(select(BoletoEntry)).all()
            if b.deleted_at is None and loja_ok(b.store_id)
        ]
        fixas = [
            f for f in s.exec(select(FixedExpense)).all()
            if f.active and f.deleted_at is None and loja_ok(f.store_id)
        ]
        pagamentos = [
            p for p in s.exec(select(FixedExpensePayment)).all() if loja_ok(p.store_id)
        ]
    pagos = {(p.fixed_expense_id, p.competencia) for p in pagamentos}
    return {
        "lojas": lojas, "dists": dists, "tipos": tipos, "boletos": boletos,
        "fixas": fixas, "pagos": pagos, "pagamentos": pagamentos,
    }


def _itens(d: dict, ini: date, fim: date) -> list[dict]:
    """Compromissos (fixos e variáveis) com vencimento entre ini e fim."""
    saida = []
    for b in d["boletos"]:
        if ini <= b.boleto_date <= fim:
            tipo = d["tipos"].get(b.expense_type_id)
            saida.append({
                "data": b.boleto_date,
                "cat": "VARIÁVEL",
                "chave": tipo or d["dists"].get(b.distributor_id, "OUTROS"),
                "valor": b.amount,
                "loja": b.store_id,
                "sem_tipo": tipo is None,
                "pago": bool(b.is_paid),
            })
    for f in d["fixas"]:
        criada = f.created_at.date().replace(day=1) if f.created_at else date(2000, 1, 1)
        for a, m in _meses_entre(ini.replace(day=1), fim):
            competencia = date(a, m, 1)
            if competencia < criada:
                continue
            venc = _dia_venc(f.due_day, a, m) or competencia
            if ini <= venc <= fim:
                saida.append({
                    "data": venc,
                    "cat": "FIXA",
                    "chave": _norm(f.name),
                    "valor": f.amount,
                    "loja": f.store_id,
                    "sem_tipo": False,
                    "pago": (f.id, competencia) in d["pagos"],
                })
    return saida


def _agrupar(itens: list[dict]) -> dict:
    grupos = defaultdict(float)
    for i in itens:
        grupos[i["chave"]] += i["valor"]
    return dict(grupos)


def _top_n(grupos: dict, n: int = 7) -> tuple[list[str], list[float]]:
    ordenado = sorted(grupos.items(), key=lambda x: -x[1])
    principais = ordenado[:n]
    resto = sum(v for _, v in ordenado[n:])
    labels = [k for k, _ in principais]
    valores = [round(v, 2) for _, v in principais]
    if resto > 0:
        labels.append("OUTROS")
        valores.append(round(resto, 2))
    return labels, valores


def _fig_rosca(grupos: dict, centro: str) -> go.Figure:
    labels, valores = _top_n(grupos)
    fig = go.Figure()
    if valores:
        fig.add_pie(
            labels=labels,
            values=valores,
            hole=0.62,
            sort=True,
            marker=dict(colors=CORES[: len(labels)], line=dict(color=TRANSPARENTE, width=0)),
            textinfo="percent",
            textposition="inside",
            insidetextorientation="horizontal",
            pull=[0.05] + [0] * (len(labels) - 1),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        )
    fig.update_layout(
        height=320,
        separators=",.",
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor=TRANSPARENTE,
        plot_bgcolor=TRANSPARENTE,
        font={"family": "Inter, sans-serif", "color": CINZA},
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", font=dict(size=10)),
        annotations=[dict(
            text=centro if valores else "Sem dados",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color=CINZA),
        )],
    )
    return travar(fig)


def _fig_linha(
    x: list[str], fixas: list[float], variaveis: list[float], altura: int, passo_rotulo: int = 1,
) -> go.Figure:
    total = [round(a + b, 2) for a, b in zip(fixas, variaveis)]
    fig = go.Figure()
    fig.add_scatter(
        x=x, y=[round(v, 2) for v in fixas], name="Contas fixas", mode="lines",
        stackgroup="um", line=dict(width=2, color=AZUL, shape="spline"),
        fillcolor="rgba(59,130,246,0.25)",
        hovertemplate="Fixas: R$ %{y:,.2f}<extra></extra>",
    )
    fig.add_scatter(
        x=x, y=[round(v, 2) for v in variaveis], name="Variáveis", mode="lines",
        stackgroup="um", line=dict(width=2, color=VERMELHO, shape="spline"),
        fillcolor="rgba(227,30,36,0.25)",
        hovertemplate="Variáveis: R$ %{y:,.2f}<extra></extra>",
    )
    fig.add_scatter(
        x=x, y=total, name="Total", mode="lines+markers",
        line=dict(width=1.5, color=CINZA, dash="dot"), marker=dict(size=6),
        hovertemplate="<b>Total: R$ %{y:,.2f}</b><extra></extra>",
    )
    fig.update_layout(
        height=altura,
        separators=",.",
        hovermode="x unified",
        margin=dict(t=30, l=60, r=20, b=60),
        paper_bgcolor=TRANSPARENTE,
        plot_bgcolor=TRANSPARENTE,
        font={"family": "Inter, sans-serif", "color": CINZA},
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor="#151A21", font=dict(color="#F1F5F9")),
    )
    rotulos_visiveis = x[::max(passo_rotulo, 1)]
    fig.update_xaxes(
        showspikes=True, spikemode="across", spikethickness=1,
        spikedash="dot", spikecolor=CINZA, gridcolor=GRADE,
        tickmode="array", tickvals=rotulos_visiveis, ticktext=rotulos_visiveis,
        tickangle=-45 if passo_rotulo > 1 or len(x) > 14 else 0,
        tickfont=dict(size=12, color="#94A3B8", weight=600),
    )
    fig.update_yaxes(
        tickprefix="R$ ", tickformat=",.0f", gridcolor=GRADE, rangemode="tozero",
        tickfont=dict(size=12, color="#94A3B8"),
    )
    return travar(fig)


def _fig_aging(faixas: list[tuple[str, float, int]]) -> go.Figure:
    nomes = [f[0] for f in faixas]
    valores = [round(f[1], 2) for f in faixas]
    textos = [f"{_brl0(f[1])} · {f[2]} conta(s)" if f[2] else "Nada em atraso" for f in faixas]
    fig = go.Figure()
    fig.add_bar(
        x=valores, y=nomes, orientation="h",
        marker_color=["#F59E0B", "#F97316", "#EF4444"],
        text=textos, textposition="auto",
        hovertemplate="%{y}: R$ %{x:,.2f}<extra></extra>",
    )
    fig.update_layout(
        height=220,
        separators=",.",
        margin=dict(t=10, l=10, r=20, b=30),
        paper_bgcolor=TRANSPARENTE,
        plot_bgcolor=TRANSPARENTE,
        font={"family": "Inter, sans-serif", "color": CINZA},
        showlegend=False,
    )
    fig.update_xaxes(tickprefix="R$ ", tickformat=",.0f", gridcolor=GRADE, rangemode="tozero")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12, weight=600))
    return travar(fig)


def _marcar_pico(fig: go.Figure, rotulos: list[str], totais: list[float]) -> None:
    """Coloca a marcação 'Pico' no ponto mais alto do gráfico."""
    if max(totais, default=0) > 0:
        k = totais.index(max(totais))
        fig.add_annotation(
            x=rotulos[k], y=totais[k], text="Pico",
            showarrow=True, arrowhead=2, ay=-36,
            arrowcolor=VERMELHO, font=dict(color=VERMELHO, size=12),
        )


def _passo(n: int) -> int:
    """Quantas semanas pular entre os rótulos do eixo, para não embolar."""
    if n <= 16:
        return 1
    if n <= 32:
        return 2
    return 3


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
class RelatoriosState(AppState):
    # Filtros e períodos
    filtro_loja: str = "todas"
    lojas_opcoes: list[dict[str, str]] = []
    semana_offset: int = 0
    mes_offset: int = 0
    ano_semanal_offset: int = 0
    geral_preset: str = "ano"     # ano | 12m | tudo | custom
    geral_ini: str = ""
    geral_fim: str = ""
    horizonte: str = "ano"        # ano | 12m

    # Rótulos
    semana_label: str = ""
    mes_label: str = ""
    geral_label: str = ""
    titulo_mensal: str = ""
    titulo_semanal: str = ""
    titulo_futuro: str = ""

    # Análise das linhas do tempo
    analise_semanal: str = ""
    destaques_semanal: list[dict[str, str]] = []
    analise_mensal: str = ""
    destaques_mensal: list[dict[str, str]] = []
    analise_futuro: str = ""
    destaques_futuro: list[dict[str, str]] = []
    tem_futuro: bool = False

    # Gráficos
    fig_semana: go.Figure = go.Figure()
    fig_mes: go.Figure = go.Figure()
    fig_geral: go.Figure = go.Figure()
    fig_semanal: go.Figure = go.Figure()
    fig_futuro: go.Figure = go.Figure()
    fig_mensal: go.Figure = go.Figure()
    fig_aging: go.Figure = go.Figure()

    # Números do topo
    n_mes: str = "R$ 0,00"
    n_30d: str = "R$ 0,00"
    n_media: str = "R$ 0,00"
    n_media_detalhe: str = ""
    n_pico: str = "R$ 0,00"
    n_pico_label: str = ""
    n_caro: str = "Sem histórico"
    n_caro_label: str = ""
    n_media_hist: str = "Sem histórico"
    n_media_hist_label: str = ""

    # Saúde dos pagamentos
    n_pct_em_dia: str = "Sem dados"
    n_pct_em_dia_detalhe: str = ""
    n_prazo: str = "Sem dados"
    n_prazo_detalhe: str = ""
    n_vencido: str = "R$ 0,00"
    n_vencido_detalhe: str = ""

    # Disciplina das lojas
    disciplina: list[dict[str, str]] = []

    # Análise geral
    historia: list[str] = []
    insights: list[dict[str, str]] = []

    # --- abertura e filtros ---
    def abrir(self):
        try:
            loja_q = self.router.page.params.get("loja", "")
        except Exception:
            loja_q = ""
        if loja_q:
            self.filtro_loja = str(loja_q)
        self._montar()

    def set_filtro_loja(self, v: str):
        self.filtro_loja = v
        self._montar()

    def semana_anterior(self):
        self.semana_offset -= 1
        self._montar()

    def semana_proxima(self):
        self.semana_offset += 1
        self._montar()

    def semana_atual(self):
        self.semana_offset = 0
        self._montar()

    def mes_anterior(self):
        self.mes_offset -= 1
        self._montar()

    def mes_proximo(self):
        self.mes_offset += 1
        self._montar()

    def mes_atual(self):
        self.mes_offset = 0
        self._montar()

    def ano_semanal_anterior(self):
        self.ano_semanal_offset -= 1
        self._montar()

    def ano_semanal_proximo(self):
        self.ano_semanal_offset += 1
        self._montar()

    def ano_semanal_atual(self):
        self.ano_semanal_offset = 0
        self._montar()

    def set_geral_preset(self, v):
        self.geral_preset = v[0] if isinstance(v, list) else v
        self._montar()

    def set_geral_ini(self, v: str):
        self.geral_ini = v
        if self.geral_ini and self.geral_fim:
            self.geral_preset = "custom"
            self._montar()

    def set_geral_fim(self, v: str):
        self.geral_fim = v
        if self.geral_ini and self.geral_fim:
            self.geral_preset = "custom"
            self._montar()

    def set_horizonte(self, v):
        self.horizonte = v[0] if isinstance(v, list) else v
        self._montar()

    def exportar(self):
        """Gera a planilha analítica com os filtros e períodos escolhidos na tela."""
        from .relatorios_excel import montar_planilha
        from ..components.ux import aviso_sucesso, aviso_erro

        try:
            conteudo, nome = montar_planilha(self)
        except Exception as erro:
            return aviso_erro(f"Não foi possível gerar a planilha: {erro}")
        return [
            rx.download(data=conteudo, filename=nome),
            aviso_sucesso("Planilha gerada. Confira a pasta de downloads."),
        ]

    # --- período geral ---
    def _periodo_geral(self, hoje: date, d: dict) -> tuple[date, date, str]:
        if self.geral_preset == "tudo":
            datas = [b.boleto_date for b in d["boletos"]]
            datas += [f.created_at.date() for f in d["fixas"] if f.created_at]
            ini = min(datas) if datas else hoje.replace(day=1)
            return ini, hoje, f"Todo o histórico: {ini:%d/%m/%Y} a {hoje:%d/%m/%Y}"
        if self.geral_preset == "12m":
            a, m = _add_meses(hoje.year, hoje.month, -11)
            ini = date(a, m, 1)
            return ini, hoje, f"Últimos 12 meses: {ini:%m/%Y} a {hoje:%m/%Y}"
        if self.geral_preset == "custom":
            try:
                ini = date.fromisoformat(self.geral_ini)
                fim = date.fromisoformat(self.geral_fim)
                if ini <= fim:
                    return ini, fim, f"Período: {ini:%d/%m/%Y} a {fim:%d/%m/%Y}"
            except ValueError:
                pass
        ini = date(hoje.year, 1, 1)
        fim = date(hoje.year, 12, 31)
        return ini, fim, f"Ano de {hoje.year}, incluindo o que já está programado"

    # --- cálculo completo ---
    def _montar(self):
        hoje = date.today()
        loja_f = int(self.filtro_loja) if self.filtro_loja not in ("", "todas") else None
        d = _carregar_dados(loja_f)
        self.lojas_opcoes = [{"id": str(i), "nome": l.name} for i, l in d["lojas"].items()]
        nome_loja = d["lojas"][loja_f].name if loja_f in d["lojas"] else ""
        escopo = f"a loja {nome_loja}" if loja_f else "a rede"

        # Rosca da semana
        ini_s = _segunda(hoje) + timedelta(weeks=self.semana_offset)
        fim_s = ini_s + timedelta(days=6)
        grupos = _agrupar(_itens(d, ini_s, fim_s))
        self.semana_label = f"{_br(ini_s)} a {_br(fim_s)}"
        self.fig_semana = _fig_rosca(grupos, _brl0(sum(grupos.values())))

        # Rosca do mês
        a, m = _add_meses(hoje.year, hoje.month, self.mes_offset)
        grupos = _agrupar(_itens(d, date(a, m, 1), _ultimo_dia(a, m)))
        self.mes_label = f"{MESES[m - 1].capitalize()} de {a}"
        self.fig_mes = _fig_rosca(grupos, _brl0(sum(grupos.values())))

        # Rosca geral
        ini_g, fim_g, rotulo = self._periodo_geral(hoje, d)
        grupos = _agrupar(_itens(d, ini_g, fim_g))
        self.geral_label = rotulo
        self.fig_geral = _fig_rosca(grupos, _brl0(sum(grupos.values())))

        # Linha do tempo semanal: todas as semanas do ano escolhido
        ano_s = hoje.year + self.ano_semanal_offset
        seg_ini = _segunda(date(ano_s, 1, 1))
        fim_ano = date(ano_s, 12, 31)
        n_sem = (fim_ano - seg_ini).days // 7 + 1
        fix_s = [0.0] * n_sem
        var_s = [0.0] * n_sem
        aberto_s = [0.0] * n_sem
        for i in _itens(d, seg_ini, seg_ini + timedelta(weeks=n_sem) - timedelta(days=1)):
            k = (i["data"] - seg_ini).days // 7
            if 0 <= k < n_sem:
                if i["cat"] == "FIXA":
                    fix_s[k] += i["valor"]
                else:
                    var_s[k] += i["valor"]
                if not i["pago"]:
                    aberto_s[k] += i["valor"]
        rotulos_s = [_br(seg_ini + timedelta(weeks=k)) for k in range(n_sem)]
        totais_s = [fix_s[k] + var_s[k] for k in range(n_sem)]
        self.titulo_semanal = f"Semanas de {ano_s}"
        fig_s = _fig_linha(rotulos_s, fix_s, var_s, 380, passo_rotulo=2)
        seg_hoje = _segunda(hoje)
        k_hoje = (seg_hoje - seg_ini).days // 7
        if 0 <= k_hoje < n_sem:
            fig_s.add_vline(
                x=k_hoje, line_width=2, line_dash="dash", line_color=VERMELHO,
                annotation_text="Hoje", annotation_position="top",
                annotation_font_color=VERMELHO,
            )
        _marcar_pico(fig_s, rotulos_s, totais_s)
        self.fig_semanal = fig_s

        rotulos_faixa = [
            f"{_br(seg_ini + timedelta(weeks=k))} a {_br(seg_ini + timedelta(weeks=k, days=6))}"
            for k in range(n_sem)
        ]
        if ano_s < hoje.year:
            inicio_futuro_s = n_sem
        elif ano_s > hoje.year:
            inicio_futuro_s = 0
        else:
            inicio_futuro_s = max(k_hoje, 0)
        self.analise_semanal, self.destaques_semanal = analise.resumo_serie(
            rotulos_faixa, totais_s, inicio_futuro_s, "semana", f"Em {ano_s}", aberto_s,
        )

        # Contas a pagar à frente: da semana atual até a última conta em aberto (máx. 52 semanas)
        limite_52 = seg_hoje + timedelta(weeks=52) - timedelta(days=1)
        abertos_fut = [i for i in _itens(d, seg_hoje, limite_52) if not i["pago"]]
        if abertos_fut:
            ultima = max(i["data"] for i in abertos_fut)
            n_fut = (ultima - seg_hoje).days // 7 + 1
            fix_f = [0.0] * n_fut
            var_f = [0.0] * n_fut
            for i in abertos_fut:
                k = (i["data"] - seg_hoje).days // 7
                if 0 <= k < n_fut:
                    if i["cat"] == "FIXA":
                        fix_f[k] += i["valor"]
                    else:
                        var_f[k] += i["valor"]
            rotulos_f = [_br(seg_hoje + timedelta(weeks=k)) for k in range(n_fut)]
            faixas_f = [
                f"{_br(seg_hoje + timedelta(weeks=k))} a {_br(seg_hoje + timedelta(weeks=k, days=6))}"
                for k in range(n_fut)
            ]
            totais_f = [fix_f[k] + var_f[k] for k in range(n_fut)]
            fig_f = _fig_linha(rotulos_f, fix_f, var_f, 360, passo_rotulo=_passo(n_fut))
            _marcar_pico(fig_f, rotulos_f, totais_f)
            self.fig_futuro = fig_f
            self.tem_futuro = True
            self.titulo_futuro = (
                f"Contas a pagar à frente: {n_fut} semana(s), até {ultima:%d/%m/%Y}"
            )
            self.analise_futuro, self.destaques_futuro = analise.resumo_futuro(
                faixas_f, totais_f, fix_f,
            )
        else:
            self.fig_futuro = travar(go.Figure())
            self.tem_futuro = False
            self.titulo_futuro = "Contas a pagar à frente"
            self.analise_futuro, self.destaques_futuro = analise.resumo_futuro([], [], [])

        # Linha mensal: até dezembro ou 12 meses
        n_meses = (12 - hoje.month + 1) if self.horizonte == "ano" else 12
        meses = [_add_meses(hoje.year, hoje.month, k) for k in range(n_meses)]
        fix_m = defaultdict(float)
        var_m = defaultdict(float)
        aberto_m = defaultdict(float)
        for i in _itens(d, date(meses[0][0], meses[0][1], 1), _ultimo_dia(*meses[-1])):
            chave = (i["data"].year, i["data"].month)
            if i["cat"] == "FIXA":
                fix_m[chave] += i["valor"]
            else:
                var_m[chave] += i["valor"]
            if not i["pago"]:
                aberto_m[chave] += i["valor"]
        self.titulo_mensal = (
            "Previsão mês a mês até dezembro" if self.horizonte == "ano"
            else "Previsão dos próximos 12 meses"
        )
        rotulos_m = [_rotulo_mes(a, m) for a, m in meses]
        totais_m = [fix_m[k] + var_m[k] for k in meses]
        fig_m = _fig_linha(
            rotulos_m,
            [fix_m[k] for k in meses],
            [var_m[k] for k in meses],
            340,
        )
        _marcar_pico(fig_m, rotulos_m, totais_m)
        self.fig_mensal = fig_m
        self.analise_mensal, self.destaques_mensal = analise.resumo_serie(
            rotulos_m, totais_m, 0, "mês",
            "Até dezembro" if self.horizonte == "ano" else "Nos próximos 12 meses",
            [aberto_m[k] for k in meses],
        )

        # Próximos 12 meses (inclui o atual): total de compromissos
        meses12 = [_add_meses(hoje.year, hoje.month, k) for k in range(12)]
        tot12 = defaultdict(float)
        for i in _itens(d, date(meses12[0][0], meses12[0][1], 1), _ultimo_dia(*meses12[-1])):
            tot12[(i["data"].year, i["data"].month)] += i["valor"]
        futuro = [(_rotulo_mes(a, m), tot12[(a, m)]) for a, m in meses12]

        # Próximos 12 meses a partir do mês que vem: só o que está a pagar
        meses_prox = [_add_meses(hoje.year, hoje.month, k) for k in range(1, 13)]
        aberto12 = defaultdict(float)
        for i in _itens(d, date(meses_prox[0][0], meses_prox[0][1], 1), _ultimo_dia(*meses_prox[-1])):
            if not i["pago"]:
                aberto12[(i["data"].year, i["data"].month)] += i["valor"]
        futuro_aberto = [(_rotulo_mes(a, m), aberto12[(a, m)]) for a, m in meses_prox]

        # Mês atual, anterior e últimos 3 meses
        ini_atual = hoje.replace(day=1)
        fim_atual = _ultimo_dia(hoje.year, hoje.month)
        itens_atual = _itens(d, ini_atual, fim_atual)
        a_ant, m_ant = _add_meses(hoje.year, hoje.month, -1)
        itens_ant = _itens(d, date(a_ant, m_ant, 1), _ultimo_dia(a_ant, m_ant))
        a3, m3 = _add_meses(hoje.year, hoje.month, -3)
        itens_3m = _itens(d, date(a3, m3, 1), _ultimo_dia(a_ant, m_ant))
        media_tipo_3m = {k: v / 3 for k, v in _agrupar(itens_3m).items()}

        total_mes = sum(i["valor"] for i in itens_atual)
        fixas_mes = sum(i["valor"] for i in itens_atual if i["cat"] == "FIXA")
        var_mes = sum(i["valor"] for i in itens_atual if i["cat"] == "VARIÁVEL")
        self.n_mes = fmt_moeda(total_mes)
        self.n_30d = fmt_moeda(sum(
            i["valor"] for i in _itens(d, hoje, hoje + timedelta(days=30)) if not i["pago"]
        ))
        soma12 = sum(v for _, v in futuro)
        pico = max(futuro, key=lambda x: x[1])
        self.n_pico = fmt_moeda(pico[1])
        self.n_pico_label = pico[0]

        # Últimos 12 meses fechados (sem o mês atual)
        meses_passados = [_add_meses(hoje.year, hoje.month, -k) for k in range(12, 0, -1)]
        tot_passado = defaultdict(float)
        var_passado = defaultdict(float)
        ini_passado = date(meses_passados[0][0], meses_passados[0][1], 1)
        for i in _itens(d, ini_passado, _ultimo_dia(a_ant, m_ant)):
            chave = (i["data"].year, i["data"].month)
            tot_passado[chave] += i["valor"]
            if i["cat"] == "VARIÁVEL":
                var_passado[chave] += i["valor"]
        passado = [(_rotulo_mes(a, m), tot_passado[(a, m)]) for a, m in meses_passados]
        com_dados = [p for p in passado if p[1] > 0]
        if com_dados:
            caro = max(com_dados, key=lambda x: x[1])
            self.n_caro = fmt_moeda(caro[1])
            self.n_caro_label = caro[0]
            self.n_media_hist = fmt_moeda(sum(v for _, v in com_dados) / len(com_dados))
            self.n_media_hist_label = f"{len(com_dados)} mês(es) com lançamentos"
        else:
            self.n_caro = "Sem histórico"
            self.n_caro_label = ""
            self.n_media_hist = "Sem histórico"
            self.n_media_hist_label = ""

        # Previsão de gasto mensal: fixas do mês + média histórica das variáveis
        meses_var = [v for v in var_passado.values() if v > 0]
        media_var = sum(meses_var) / len(meses_var) if meses_var else var_mes
        previsao = fixas_mes + media_var
        self.n_media = fmt_moeda(previsao)
        self.n_media_detalhe = f"{fmt_moeda(soma12 / 12)} já programados por mês"

        # Saúde dos pagamentos
        pont = pontualidade(d, hoje)
        if pont["qtd"]:
            self.n_pct_em_dia = f"{pont['pct']:.0f}%"
            self.n_pct_em_dia_detalhe = f"{pont['qtd']} pagamento(s) nos últimos 6 meses"
            prazo = pont["prazo"]
            if abs(prazo) < 0.5:
                self.n_prazo = "No dia"
                self.n_prazo_detalhe = "em média, pago no vencimento"
            else:
                self.n_prazo = f"{abs(prazo):.1f} dia(s)".replace(".", ",")
                self.n_prazo_detalhe = "após o vencimento" if prazo > 0 else "antes do vencimento"
        else:
            self.n_pct_em_dia = "Sem dados"
            self.n_pct_em_dia_detalhe = "nenhum pagamento registrado nos últimos 6 meses"
            self.n_prazo = "Sem dados"
            self.n_prazo_detalhe = ""
        faixas = aging(d, hoje)
        total_vencido = sum(f[1] for f in faixas)
        qtd_vencida = sum(f[2] for f in faixas)
        self.n_vencido = fmt_moeda(total_vencido)
        self.n_vencido_detalhe = (
            f"{qtd_vencida} conta(s) em atraso" if qtd_vencida else "nenhuma conta em atraso"
        )
        self.fig_aging = _fig_aging(faixas)

        # Disciplina das lojas
        a6, m6 = _add_meses(hoje.year, hoje.month, -6)
        itens_6m = _itens(d, date(a6, m6, 1), _ultimo_dia(a_ant, m_ant))
        self.disciplina, lojas_projecao = disciplina(d, hoje, itens_atual, itens_6m, loja_f)

        # Lojas (gasto do mês x limite)
        gasto_loja = defaultdict(float)
        for i in itens_atual:
            gasto_loja[i["loja"]] += i["valor"]
        lojas_ctx = [
            {"nome": l.name, "gasto": gasto_loja[l.id], "limite": l.monthly_limit or 0.0}
            for l in d["lojas"].values()
            if loja_f is None or l.id == loja_f
        ]

        # Vencidas: despesas não pagas antes de hoje + fixas do mês já vencidas
        vencidas = [b for b in d["boletos"] if not b.is_paid and b.boleto_date < hoje]
        venc_qtd = len(vencidas)
        venc_valor = sum(b.amount for b in vencidas)
        for i in itens_atual:
            if i["cat"] == "FIXA" and not i["pago"] and i["data"] < hoje:
                venc_qtd += 1
                venc_valor += i["valor"]

        # Despesas sem tipo nos últimos 12 meses
        sem_tipo = [
            b for b in d["boletos"]
            if b.expense_type_id is None and b.boleto_date >= hoje - timedelta(days=365)
        ]

        # Próximas 8 semanas a partir de hoje: só o que está a pagar
        prox = [0.0] * 8
        for i in _itens(d, seg_hoje, seg_hoje + timedelta(weeks=8) - timedelta(days=1)):
            if i["pago"]:
                continue
            k = (i["data"] - seg_hoje).days // 7
            if 0 <= k < 8:
                prox[k] += i["valor"]
        semanas = [
            (f"{_br(seg_hoje + timedelta(weeks=k))} a {_br(seg_hoje + timedelta(weeks=k, days=6))}", prox[k])
            for k in range(8)
        ]

        contexto = {
            "escopo": escopo,
            "mes_nome": f"{MESES[hoje.month - 1]} de {hoje.year}",
            "mes_ant_nome": f"{MESES[m_ant - 1]} de {a_ant}",
            "total_mes": total_mes,
            "total_mes_ant": sum(i["valor"] for i in itens_ant),
            "fixas_mes": fixas_mes,
            "var_mes": var_mes,
            "por_tipo_mes": _agrupar(itens_atual),
            "media_tipo_3m": media_tipo_3m,
            "lojas": lojas_ctx,
            "dias_restantes": (fim_atual - hoje).days,
            "futuro": futuro,
            "futuro_aberto": futuro_aberto,
            "passado": passado,
            "semanas": semanas,
            "vencidas_qtd": venc_qtd,
            "vencidas_valor": venc_valor,
            "sem_tipo_qtd": len(sem_tipo),
            "sem_tipo_valor": sum(b.amount for b in sem_tipo),
            "previsao_mes": previsao,
            "pontualidade": pont,
            "vencidas_30": (faixas[2][2], faixas[2][1]),
            "lojas_projecao": lojas_projecao,
        }
        self.historia = analise.historia(contexto)
        self.insights = analise.observacoes(contexto)