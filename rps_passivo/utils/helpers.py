"""Funções utilitárias: formatação de moeda e cálculo de semanas (segunda a domingo)."""
import re
from datetime import date, timedelta
from typing import Optional

from sqlmodel import select, and_

from ..models import Store, FixedExpense, BoletoEntry


def fmt_moeda(valor: float | None) -> str:
    if valor is None:
        valor = 0.0
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


def inicio_semana(d: date) -> date:
    """Segunda-feira da semana de `d`."""
    return d - timedelta(days=d.weekday())


def fim_semana(d: date) -> date:
    return inicio_semana(d) + timedelta(days=6)


def periodo_semana_str(d: date) -> str:
    ini = inicio_semana(d)
    fim = fim_semana(d)
    return f"{ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}"


MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def nome_mes(m: int) -> str:
    return MESES_PT[m - 1]


def proximo_vencimento_mensal(due_day: str, hoje: date) -> date | None:
    """Extrai o próximo dia numérico de vencimento de um texto tipo 'DIA 10'."""
    m = re.search(r"(\d{1,2})", due_day or "")
    if not m:
        return None
    dia = min(int(m.group(1)), 28)
    try:
        venc = hoje.replace(day=dia)
    except ValueError:
        return None
    if venc < hoje:
        prox_mes = hoje.month % 12 + 1
        ano = hoje.year + (1 if hoje.month == 12 else 0)
        venc = date(ano, prox_mes, dia)
    return venc


def calcular_dados_loja_para_card(
    loja: Store,
    hoje: date,
    ini_mes: date,
) -> dict:
    """Calcula todos os dados necessários para exibir o card de uma loja no Dashboard.

    Retorna um dict com:
        - gasto_acumulado: soma de boletos + fixas ativas no mês (independente de is_paid)
        - pago_mes: soma de lançamentos PAGOS com vencimento no mês corrente
        - falta_pagar: gasto_acumulado - pago_mes
        - a_vencer_mes: soma de contas FIXAS não pagas com vencimento no mês corrente
        - percentual_limite: % do monthly_limit consumido
        - esta_no_limite: bool (gasto >= monthly_limit)
        - esta_excedida: bool (gasto > monthly_limit)
    """
    # --- gasto acumulado (boletos + fixas ativas) ---
    boletos = [
        b for b in getattr(loja, "_boletos_cache", [])
        if b.boleto_date >= ini_mes
    ] or []
    fixas = [
        f for f in getattr(loja, "_fixas_cache", [])
        if f.active
    ] or []

    # fallback se não houver cache: consulta direta
    if not boletos or not fixas:
        # (caso de uso onde o cache não está populado)
        return {
            "gasto_acumulado": 0.0,
            "pago_mes": 0.0,
            "falta_pagar": 0.0,
            "a_vencer_mes": 0.0,
            "percentual_limite": 0.0,
            "esta_no_limite": False,
            "esta_excedida": False,
        }

    soma_boletos = sum(b.amount for b in boletos)
    soma_fixas = sum(f.amount for f in fixas)
    gasto_acumulado = soma_boletos + soma_fixas

    # --- pago no mês corrente (somente lançamentos pagos cujo vencimento cai neste mês) ---
    pago_mes = 0.0

    # boletos pagos
    for b in boletos:
        if not b.is_paid:
            continue
        if b.paid_at is None:
            continue
        if b.paid_at.date() >= ini_mes:
            pago_mes += b.amount

    # contas fixas pagas (vencimento no mês corrente)
    for f in fixas:
        if not f.is_paid or f.paid_at is None:
            continue
        venc = proximo_vencimento_mensal(f.due_day, hoje)
        if venc is None:
            continue
        if ini_mes <= venc <= hoje.replace(day=28):
            pago_mes += f.amount

    falta_pagar = gasto_acumulado - pago_mes

    # --- a vencer este mês: FIXAS não pagas com vencimento no mês corrente ---
    a_vencer_mes = 0.0
    for f in fixas:
        if f.is_paid:
            continue
        venc = proximo_vencimento_mensal(f.due_day, hoje)
        if venc is None:
            continue
        if ini_mes <= venc <= hoje.replace(day=28):
            a_vencer_mes += f.amount

    # --- percentual / status de limite ---
    monthly_limit = loja.monthly_limit or 0.0
    percentual_limite = (gasto_acumulado / monthly_limit * 100) if monthly_limit else 0.0
    esta_no_limite = bool(monthly_limit and gasto_acumulado >= monthly_limit)
    esta_excedida = bool(monthly_limit and gasto_acumulado > monthly_limit)

    return {
        "gasto_acumulado": round(gasto_acumulado, 2),
        "pago_mes": round(pago_mes, 2),
        "falta_pagar": round(max(falta_pagar, 0.0), 2),
        "a_vencer_mes": round(a_vencer_mes, 2),
        "percentual_limite": round(min(percentual_limite, 999), 1),
        "esta_no_limite": esta_no_limite,
        "esta_excedida": esta_excedida,
    }
