"""Planilha analítica da página Relatórios (Excel)."""
import io
from collections import defaultdict
from datetime import date, datetime, timedelta

import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .relatorios_estado import _carregar_dados, _itens, _agrupar, _segunda, _br, _rotulo_mes, MESES
from .contas_estado import _add_meses, _ultimo_dia

VERMELHO = PatternFill("solid", fgColor="E31E24")
DESTAQUE = PatternFill("solid", fgColor="FDE2E2")
VERDE_CLARO = PatternFill("solid", fgColor="DCFCE7")
LARANJA_CLARO = PatternFill("solid", fgColor="FEF3C7")
CINZA_CLARO = PatternFill("solid", fgColor="F1F5F9")
BRANCO_NEGRITO = Font(color="FFFFFF", bold=True)
NEGRITO = Font(bold=True)
MOEDA = "R$ #,##0.00"
PCT = "0.0%"
DATA = "DD/MM/YYYY"
NIVEIS = {"alerta": "ALERTA", "atencao": "ATENÇÃO", "info": "SUGESTÃO", "positivo": "POSITIVO"}


def _titulo(ws, texto: str, subtitulo: str) -> None:
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=16, color="E31E24")
    ws["A2"] = subtitulo
    ws["A2"].font = Font(italic=True, color="64748B")


def _cabecalho(ws, linha: int, titulos: list[str], larguras: list[int]) -> None:
    for i, (titulo, largura) in enumerate(zip(titulos, larguras), start=1):
        c = ws.cell(row=linha, column=i, value=titulo)
        c.fill = VERMELHO
        c.font = BRANCO_NEGRITO
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = largura
    ws.freeze_panes = f"A{linha + 1}"


def _filtro(ws, linha: int, colunas: int) -> None:
    if ws.max_row > linha:
        ws.auto_filter.ref = f"A{linha}:{get_column_letter(colunas)}{ws.max_row}"


def _moeda(ws, linha: int, colunas: list[int]) -> None:
    for c in colunas:
        ws.cell(row=linha, column=c).number_format = MOEDA


def _linha_total(ws, linha_ini: int, linha_fim: int, colunas_soma: list[int], rotulo: str = "TOTAL") -> None:
    total = linha_fim + 1
    ws.cell(row=total, column=1, value=rotulo).font = NEGRITO
    for c in colunas_soma:
        letra = get_column_letter(c)
        cel = ws.cell(row=total, column=c, value=f"=SUM({letra}{linha_ini}:{letra}{linha_fim})")
        cel.number_format = MOEDA
        cel.font = NEGRITO
        cel.fill = CINZA_CLARO
    ws.cell(row=total, column=1).fill = CINZA_CLARO


def montar_planilha(st) -> tuple[bytes, str]:
    """Monta a planilha a partir do estado da página (filtros e períodos escolhidos)."""
    hoje = date.today()
    loja_f = int(st.filtro_loja) if st.filtro_loja not in ("", "todas") else None
    d = _carregar_dados(loja_f)
    escopo = d["lojas"][loja_f].name if loja_f in d["lojas"] else "Toda a rede"
    gerado = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y às %H:%M")
    subtitulo = f"{escopo} · gerado em {gerado}"
    wb = openpyxl.Workbook()

    # ------------------------------------------------------------------
    # Aba 1: Resumo
    # ------------------------------------------------------------------
    ws = wb.active
    ws.title = "Resumo"
    _titulo(ws, "Passivo Cumani — Relatório analítico", subtitulo)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 90

    _cabecalho(ws, 4, ["Indicador", "Valor", "Referência"], [34, 26, 90])
    indicadores = [
        ("Compromissos do mês", st.n_mes, ""),
        ("A pagar em 30 dias", st.n_30d, ""),
        ("Média mensal (passado)", st.n_media_hist, st.n_media_hist_label),
        ("Mês mais caro (passado)", st.n_caro, st.n_caro_label),
        ("Média mensal prevista", st.n_media, "Próximos 12 meses"),
        ("Mês mais carregado à frente", st.n_pico, st.n_pico_label),
    ]
    linha = 5
    for rotulo, valor, ref in indicadores:
        ws.cell(row=linha, column=1, value=rotulo)
        ws.cell(row=linha, column=2, value=valor).font = NEGRITO
        ws.cell(row=linha, column=3, value=ref)
        linha += 1

    linha += 1
    ws.cell(row=linha, column=1, value="A história do mês").font = Font(bold=True, size=13, color="E31E24")
    linha += 1
    for paragrafo in st.historia:
        ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=3)
        cel = ws.cell(row=linha, column=1, value=paragrafo)
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[linha].height = 48
        linha += 1

    linha += 1
    ws.cell(row=linha, column=1, value="Observações e sugestões").font = Font(bold=True, size=13, color="E31E24")
    linha += 1
    for i, titulo in enumerate(["Nível", "Observação", "Detalhe"], start=1):
        c = ws.cell(row=linha, column=i, value=titulo)
        c.fill = VERMELHO
        c.font = BRANCO_NEGRITO
    linha += 1
    cores_nivel = {"alerta": DESTAQUE, "atencao": LARANJA_CLARO, "positivo": VERDE_CLARO}
    for o in st.insights:
        ws.cell(row=linha, column=1, value=NIVEIS.get(o["nivel"], o["nivel"])).fill = cores_nivel.get(o["nivel"], CINZA_CLARO)
        ws.cell(row=linha, column=2, value=o["titulo"]).font = NEGRITO
        cel = ws.cell(row=linha, column=3, value=o["texto"])
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[linha].height = 36
        linha += 1

    # ------------------------------------------------------------------
    # Aba 2: Previsão mensal (próximos 12 meses)
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Previsão mensal")
    _titulo(ws, "Previsão mês a mês", f"Próximos 12 meses · {subtitulo}")
    _cabecalho(ws, 4, ["Mês", "Contas fixas", "Variáveis", "Total", "A pagar", "% dos 12 meses"], [12, 18, 18, 18, 18, 16])
    meses12 = [_add_meses(hoje.year, hoje.month, k) for k in range(12)]
    fix_m, var_m, ab_m = defaultdict(float), defaultdict(float), defaultdict(float)
    for i in _itens(d, date(meses12[0][0], meses12[0][1], 1), _ultimo_dia(*meses12[-1])):
        chave = (i["data"].year, i["data"].month)
        if i["cat"] == "FIXA":
            fix_m[chave] += i["valor"]
        else:
            var_m[chave] += i["valor"]
        if not i["pago"]:
            ab_m[chave] += i["valor"]
    soma12 = sum(fix_m[k] + var_m[k] for k in meses12) or 1
    for a, m in meses12:
        total = fix_m[(a, m)] + var_m[(a, m)]
        ws.append([
            _rotulo_mes(a, m), round(fix_m[(a, m)], 2), round(var_m[(a, m)], 2),
            round(total, 2), round(ab_m[(a, m)], 2), total / soma12,
        ])
        _moeda(ws, ws.max_row, [2, 3, 4, 5])
        ws.cell(row=ws.max_row, column=6).number_format = PCT
    _linha_total(ws, 5, ws.max_row, [2, 3, 4, 5])

    grafico = BarChart()
    grafico.type = "col"
    grafico.grouping = "stacked"
    grafico.overlap = 100
    grafico.title = "Compromissos por mês"
    grafico.y_axis.title = "R$"
    dados = Reference(ws, min_col=2, max_col=3, min_row=4, max_row=16)
    categorias = Reference(ws, min_col=1, min_row=5, max_row=16)
    grafico.add_data(dados, titles_from_data=True)
    grafico.set_categories(categorias)
    grafico.height, grafico.width = 9, 18
    ws.add_chart(grafico, "H4")

    # ------------------------------------------------------------------
    # Aba 3: Semanas do ano exibido na tela
    # ------------------------------------------------------------------
    ano_s = hoje.year + st.ano_semanal_offset
    ws = wb.create_sheet(f"Semanas {ano_s}")
    _titulo(ws, f"Semanas de {ano_s}", subtitulo)
    _cabecalho(ws, 4, ["Semana", "Contas fixas", "Variáveis", "Total", "A pagar"], [18, 18, 18, 18, 18])
    seg_ini = _segunda(date(ano_s, 1, 1))
    n_sem = (date(ano_s, 12, 31) - seg_ini).days // 7 + 1
    fix_s, var_s, ab_s = [0.0] * n_sem, [0.0] * n_sem, [0.0] * n_sem
    for i in _itens(d, seg_ini, seg_ini + timedelta(weeks=n_sem) - timedelta(days=1)):
        k = (i["data"] - seg_ini).days // 7
        if 0 <= k < n_sem:
            if i["cat"] == "FIXA":
                fix_s[k] += i["valor"]
            else:
                var_s[k] += i["valor"]
            if not i["pago"]:
                ab_s[k] += i["valor"]
    totais = [fix_s[k] + var_s[k] for k in range(n_sem)]
    k_pico = totais.index(max(totais)) if max(totais, default=0) > 0 else -1
    for k in range(n_sem):
        ini = seg_ini + timedelta(weeks=k)
        ws.append([
            f"{_br(ini)} a {_br(ini + timedelta(days=6))}",
            round(fix_s[k], 2), round(var_s[k], 2), round(totais[k], 2), round(ab_s[k], 2),
        ])
        _moeda(ws, ws.max_row, [2, 3, 4, 5])
        if k == k_pico:
            for c in range(1, 6):
                ws.cell(row=ws.max_row, column=c).fill = DESTAQUE
                ws.cell(row=ws.max_row, column=c).font = NEGRITO
    _linha_total(ws, 5, ws.max_row, [2, 3, 4, 5])
    if k_pico >= 0:
        ws.cell(row=3, column=1, value="Linha destacada: semana mais carregada do ano").font = Font(italic=True, color="E31E24")

    linha_graf = LineChart()
    linha_graf.title = f"Total por semana em {ano_s}"
    linha_graf.y_axis.title = "R$"
    linha_graf.add_data(Reference(ws, min_col=4, min_row=4, max_row=4 + n_sem), titles_from_data=True)
    linha_graf.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n_sem))
    linha_graf.height, linha_graf.width = 9, 22
    ws.add_chart(linha_graf, "G4")

    # ------------------------------------------------------------------
    # Aba 4: Por tipo (período "Geral" da tela)
    # ------------------------------------------------------------------
    ini_g, fim_g, rotulo_g = st._periodo_geral(hoje, d)
    itens_g = _itens(d, ini_g, fim_g)
    ws = wb.create_sheet("Por tipo")
    _titulo(ws, "Gastos por tipo", f"{rotulo_g} · {subtitulo}")
    _cabecalho(ws, 4, ["Tipo / gasto", "Valor", "% do período"], [36, 18, 14])
    grupos = sorted(_agrupar(itens_g).items(), key=lambda x: -x[1])
    total_g = sum(v for _, v in grupos) or 1
    for tipo, valor in grupos:
        ws.append([tipo, round(valor, 2), valor / total_g])
        _moeda(ws, ws.max_row, [2])
        ws.cell(row=ws.max_row, column=3).number_format = PCT
    if grupos:
        _linha_total(ws, 5, ws.max_row, [2])
    _filtro(ws, 4, 3)

    # ------------------------------------------------------------------
    # Aba 5: Por loja (mês atual)
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Por loja")
    _titulo(ws, f"Lojas em {MESES[hoje.month - 1]} de {hoje.year}", subtitulo)
    _cabecalho(
        ws, 4,
        ["Loja", "Limite mensal", "Gasto no mês", "% do limite", "Pago", "A pagar", "Situação"],
        [24, 18, 18, 14, 18, 18, 16],
    )
    itens_mes = _itens(d, hoje.replace(day=1), _ultimo_dia(hoje.year, hoje.month))
    gasto, pago = defaultdict(float), defaultdict(float)
    for i in itens_mes:
        gasto[i["loja"]] += i["valor"]
        if i["pago"]:
            pago[i["loja"]] += i["valor"]
    for l in sorted(d["lojas"].values(), key=lambda x: x.name):
        if loja_f and l.id != loja_f:
            continue
        limite = l.monthly_limit or 0.0
        pct = gasto[l.id] / limite if limite else 0.0
        if limite <= 0:
            situacao, cor = "SEM LIMITE", CINZA_CLARO
        elif pct > 1:
            situacao, cor = "EXCEDIDA", DESTAQUE
        elif pct >= 0.8:
            situacao, cor = "ATENÇÃO", LARANJA_CLARO
        else:
            situacao, cor = "DENTRO", VERDE_CLARO
        ws.append([
            l.name, round(limite, 2), round(gasto[l.id], 2), pct,
            round(pago[l.id], 2), round(gasto[l.id] - pago[l.id], 2), situacao,
        ])
        _moeda(ws, ws.max_row, [2, 3, 5, 6])
        ws.cell(row=ws.max_row, column=4).number_format = PCT
        ws.cell(row=ws.max_row, column=7).fill = cor
    _linha_total(ws, 5, ws.max_row, [2, 3, 5, 6])
    _filtro(ws, 4, 7)

    # ------------------------------------------------------------------
    # Aba 6: Lançamentos do período "Geral"
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Lançamentos")
    _titulo(ws, "Compromissos do período", f"{rotulo_g} · {subtitulo}")
    _cabecalho(ws, 4, ["Vencimento", "Loja", "Tipo / gasto", "Categoria", "Valor", "Situação"], [14, 22, 34, 12, 16, 12])
    for i in sorted(itens_g, key=lambda x: x["data"]):
        if i["pago"]:
            situacao = "PAGA"
        elif i["data"] < hoje:
            situacao = "VENCIDA"
        else:
            situacao = "A PAGAR"
        ws.append([
            i["data"], d["lojas"][i["loja"]].name, i["chave"], i["cat"],
            round(i["valor"], 2), situacao,
        ])
        ws.cell(row=ws.max_row, column=1).number_format = DATA
        _moeda(ws, ws.max_row, [5])
        if situacao == "VENCIDA":
            ws.cell(row=ws.max_row, column=6).fill = DESTAQUE
    _filtro(ws, 4, 6)

    buffer = io.BytesIO()
    wb.save(buffer)
    nome = f"relatorio_cumani_{hoje:%Y-%m-%d}.xlsx"
    return buffer.getvalue(), nome