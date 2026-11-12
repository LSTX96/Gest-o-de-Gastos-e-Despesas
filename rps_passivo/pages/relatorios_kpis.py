"""Indicadores de pagamentos e disciplina das lojas (usados na página Relatórios)."""
from collections import defaultdict
from datetime import date, timedelta

from .contas_estado import _add_meses, _ultimo_dia, _dia_venc
from ..utils.helpers import fmt_moeda

# A partir desta data o sistema registra a data real do pagamento.
# Contas que vencem antes dela são consideradas pagas em dia.
INICIO_MEDICAO = date(2026, 11, 12)

# Pagamento registrado até 4 horas depois do lançamento é considerado
# "lançado já pago" (a folga cobre a diferença de fuso entre os horários gravados).
FOLGA_LANCAMENTO = timedelta(hours=4)


def _data_brasilia(dt) -> date:
    """paid_at é gravado em UTC; converte para a data de Brasília."""
    return (dt - timedelta(hours=3)).date()


def _atraso(venc: date, pago_em, criado_em) -> int:
    """Dias de atraso de um pagamento (0 = em dia).

    - Conta lançada já paga: em dia.
    - Conta com vencimento antes de INICIO_MEDICAO: em dia.
    - Demais: data do pagamento menos o vencimento (nunca negativo).
    """
    if venc < INICIO_MEDICAO:
        return 0
    if criado_em and pago_em <= criado_em + FOLGA_LANCAMENTO:
        return 0
    return max((_data_brasilia(pago_em) - venc).days, 0)


def pontualidade(d: dict, hoje: date, dias: int = 180) -> dict:
    """Pagamentos com vencimento nos últimos `dias`: % pago em dia e prazo médio de atraso."""
    corte = hoje - timedelta(days=dias)
    atrasos = []

    for b in d["boletos"]:
        if not (b.is_paid and b.paid_at and corte <= b.boleto_date <= hoje):
            continue
        atrasos.append(_atraso(b.boleto_date, b.paid_at, b.created_at))

    fixas = {f.id: f for f in d["fixas"]}
    for p in d["pagamentos"]:
        f = fixas.get(p.fixed_expense_id)
        if not f or not p.paid_at:
            continue
        venc = _dia_venc(f.due_day, p.competencia.year, p.competencia.month) or p.competencia
        if not (corte <= venc <= hoje):
            continue
        atrasos.append(_atraso(venc, p.paid_at, f.created_at))

    if not atrasos:
        return {"qtd": 0, "pct": 0.0, "prazo": 0.0}
    em_dia = sum(1 for a in atrasos if a == 0)
    return {
        "qtd": len(atrasos),
        "pct": em_dia / len(atrasos) * 100,
        "prazo": sum(atrasos) / len(atrasos),
    }


def aging(d: dict, hoje: date) -> list[tuple[str, float, int]]:
    """Valor e quantidade em atraso por faixa de dias."""
    faixas = {"1 a 7 dias": [0.0, 0], "8 a 30 dias": [0.0, 0], "Mais de 30 dias": [0.0, 0]}

    def somar(venc: date, valor: float) -> None:
        atraso = (hoje - venc).days
        if atraso <= 0:
            return
        if atraso <= 7:
            chave = "1 a 7 dias"
        elif atraso <= 30:
            chave = "8 a 30 dias"
        else:
            chave = "Mais de 30 dias"
        faixas[chave][0] += valor
        faixas[chave][1] += 1

    for b in d["boletos"]:
        if not b.is_paid and b.boleto_date < hoje:
            somar(b.boleto_date, b.amount)

    competencia = hoje.replace(day=1)
    for f in d["fixas"]:
        venc = _dia_venc(f.due_day, hoje.year, hoje.month)
        if venc is None or venc >= hoje or (f.id, competencia) in d["pagos"]:
            continue
        if f.created_at and f.created_at.date() > venc:
            continue  # cadastrada depois do vencimento deste mês
        somar(venc, f.amount)

    return [(nome, valores[0], valores[1]) for nome, valores in faixas.items()]


def disciplina(d: dict, hoje: date, itens_mes: list[dict], itens_6m: list[dict], loja_f) -> tuple[list, list]:
    """Uso do limite, projeção de fechamento e estouros nos últimos 6 meses, por loja.

    Projeção = compromissos do mês + ritmo diário das despesas variáveis até hoje
    aplicado aos dias que faltam.
    """
    fim = _ultimo_dia(hoje.year, hoje.month)
    dias_passados = hoje.day
    dias_restantes = fim.day - hoje.day

    gasto = defaultdict(float)
    var_ate_hoje = defaultdict(float)
    for i in itens_mes:
        gasto[i["loja"]] += i["valor"]
        if i["cat"] == "VARIÁVEL" and i["data"] <= hoje:
            var_ate_hoje[i["loja"]] += i["valor"]

    por_mes = defaultdict(float)
    for i in itens_6m:
        por_mes[(i["loja"], i["data"].year, i["data"].month)] += i["valor"]
    meses6 = [_add_meses(hoje.year, hoje.month, -k) for k in range(1, 7)]

    linhas, contexto = [], []
    for l in d["lojas"].values():
        if loja_f and l.id != loja_f:
            continue
        limite = l.monthly_limit or 0.0
        g = gasto[l.id]
        ritmo = var_ate_hoje[l.id] / max(dias_passados, 1)
        projecao = g + ritmo * dias_restantes
        estouros = sum(1 for a, m in meses6 if limite > 0 and por_mes[(l.id, a, m)] > limite)
        uso = g / limite * 100 if limite else 0.0
        proj_pct = projecao / limite * 100 if limite else 0.0

        if limite <= 0:
            situacao, cor, cor_hex, ordem = "Sem limite", "gray", "#94A3B8", 4
        elif g > limite:
            situacao, cor, cor_hex, ordem = "Estourada", "red", "#EF4444", 0
        elif projecao > limite:
            situacao, cor, cor_hex, ordem = "Vai estourar", "orange", "#F97316", 1
        elif projecao >= limite * 0.9:
            situacao, cor, cor_hex, ordem = "Atenção", "amber", "#F59E0B", 2
        else:
            situacao, cor, cor_hex, ordem = "No ritmo", "green", "#10B981", 3

        linhas.append({
            "loja": l.name,
            "limite": fmt_moeda(limite) if limite else "—",
            "gasto": fmt_moeda(g),
            "uso_txt": f"{uso:.0f}%" if limite else "—",
            "uso_barra": f"{min(uso, 100):.0f}",
            "projecao": fmt_moeda(projecao),
            "projecao_txt": f"{proj_pct:.0f}% do limite" if limite else "—",
            "estouros": f"{estouros} de 6",
            "situacao": situacao,
            "cor": cor,
            "cor_hex": cor_hex,
            "_ordem": ordem,
            "_pct": proj_pct,
        })
        contexto.append({"nome": l.name, "limite": limite, "gasto": g, "projecao": projecao})

    linhas.sort(key=lambda x: (x["_ordem"], -x["_pct"]))
    for linha in linhas:
        linha.pop("_ordem")
        linha.pop("_pct")
    return linhas, contexto


# ---------------------------------------------------------------------------
# Curva ABC e variação de gastos recorrentes
# ---------------------------------------------------------------------------
def curva_abc(itens: list[dict]) -> list[dict]:
    """Classifica os tipos de gasto: A (até ~80% do total), B (até ~95%), C (restante)."""
    grupos = defaultdict(float)
    for i in itens:
        grupos[i["chave"]] += i["valor"]
    total = sum(grupos.values())
    if total <= 0:
        return []
    linhas = []
    acumulado = 0.0
    for nome, valor in sorted(grupos.items(), key=lambda x: -x[1]):
        pct = valor / total * 100
        antes = acumulado
        acumulado += pct
        classe = "A" if antes < 80 else ("B" if antes < 95 else "C")
        linhas.append({"tipo": nome, "valor": valor, "pct": pct, "acum": acumulado, "classe": classe})
    return linhas


def variacao_precos(d: dict, hoje: date, meses: int = 12) -> list[dict]:
    """Compara os dois últimos meses em que cada gasto recorrente apareceu, por loja.

    Contas fixas: usa o valor pago em cada mês (mostra aumento de preço).
    Despesas variáveis: soma do mês (volume e preço juntos). Parcelas ficam de fora.
    """
    from .contas_estado import _norm

    corte = hoje - timedelta(days=meses * 31)
    series = defaultdict(lambda: defaultdict(float))
    tipo_serie = {}

    for b in d["boletos"]:
        if not (corte <= b.boleto_date <= hoje):
            continue
        if b.total_parcelas and b.total_parcelas > 1:
            continue
        nome = d["dists"].get(b.distributor_id, "")
        if not nome:
            continue
        chave = (nome, b.store_id)
        series[chave][(b.boleto_date.year, b.boleto_date.month)] += b.amount
        tipo_serie.setdefault(chave, "VARIÁVEL")

    fixas = {f.id: f for f in d["fixas"]}
    for p in d["pagamentos"]:
        f = fixas.get(p.fixed_expense_id)
        if not f or p.competencia < corte:
            continue
        chave = (_norm(f.name), f.store_id)
        series[chave][(p.competencia.year, p.competencia.month)] += p.amount
        tipo_serie[chave] = "FIXA"

    linhas = []
    for (nome, loja_id), por_mes in series.items():
        if len(por_mes) < 2:
            continue
        mes_ant, mes_atu = sorted(por_mes)[-2:]
        anterior, atual = por_mes[mes_ant], por_mes[mes_atu]
        if anterior <= 0:
            continue
        variacao = (atual / anterior - 1) * 100
        if abs(variacao) < 1:
            continue
        linhas.append({
            "gasto": nome,
            "loja": d["lojas"][loja_id].name if loja_id in d["lojas"] else "?",
            "categoria": tipo_serie.get((nome, loja_id), "VARIÁVEL"),
            "anterior": anterior,
            "mes_ant": f"{mes_ant[1]:02d}/{mes_ant[0]}",
            "atual": atual,
            "mes_atu": f"{mes_atu[1]:02d}/{mes_atu[0]}",
            "var": variacao,
        })
    linhas.sort(key=lambda x: -abs(x["var"]))
    return linhas[:12]