"""Indicadores de pagamentos e disciplina das lojas (usados na página Relatórios)."""
from collections import defaultdict
from datetime import date, timedelta

from .contas_estado import _add_meses, _ultimo_dia, _dia_venc
from ..utils.helpers import fmt_moeda


def _data_brasilia(dt) -> date:
    """paid_at é gravado em UTC; converte para a data de Brasília."""
    return (dt - timedelta(hours=3)).date()


def pontualidade(d: dict, hoje: date, dias: int = 180) -> dict:
    """Pagamentos com vencimento nos últimos `dias`: % pago em dia e prazo médio.

    Ignora contas lançadas já pagas: nelas a data registrada é a do lançamento,
    não a do pagamento real.
    """
    corte = hoje - timedelta(days=dias)
    margem = timedelta(minutes=10)
    atrasos = []
    for b in d["boletos"]:
        if not (b.is_paid and b.paid_at and corte <= b.boleto_date <= hoje):
            continue
        if b.created_at and b.paid_at - b.created_at < margem:
            continue  # lançada já paga
        atrasos.append((_data_brasilia(b.paid_at) - b.boleto_date).days)
    fixas = {f.id: f for f in d["fixas"]}
    for p in d["pagamentos"]:
        f = fixas.get(p.fixed_expense_id)
        if not f or not p.paid_at:
            continue
        if f.created_at and p.paid_at - f.created_at < margem:
            continue  # conta fixa cadastrada já paga
        venc = _dia_venc(f.due_day, p.competencia.year, p.competencia.month) or p.competencia
        if corte <= venc <= hoje:
            atrasos.append((_data_brasilia(p.paid_at) - venc).days)
    if not atrasos:
        return {"qtd": 0, "pct": 0.0, "prazo": 0.0}
    em_dia = sum(1 for a in atrasos if a <= 0)
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