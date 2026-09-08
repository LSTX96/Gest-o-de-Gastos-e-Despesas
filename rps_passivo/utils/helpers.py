"""Funções utilitárias: formatação de moeda e cálculo de semanas (segunda a domingo)."""
import re
from datetime import date, timedelta


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
