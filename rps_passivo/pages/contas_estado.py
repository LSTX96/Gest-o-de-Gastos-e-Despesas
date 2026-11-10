"""Estado da página Contas: cálculos, filtros, ações e exportação para Excel."""
import io
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

import reflex as rx
from sqlmodel import select

from ..models import (
    Store, Distributor, ExpenseType, BoletoEntry, FixedExpense, FixedExpensePayment,
)
from ..state import AppState
from ..components.ux import aviso_sucesso, aviso_erro
from ..utils.helpers import fmt_moeda

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
MESES_ABREV = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def _norm(texto: str) -> str:
    return " ".join((texto or "").split()).upper()


def _add_meses(ano: int, mes: int, n: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def _ultimo_dia(ano: int, mes: int) -> date:
    prox_ano, prox_mes = _add_meses(ano, mes, 1)
    return date(prox_ano, prox_mes, 1) - timedelta(days=1)


def _dia_venc(due_day: str, ano: int, mes: int):
    """Data de vencimento de uma conta fixa num mês (None se não tiver dia)."""
    m = re.search(r"(\d{1,2})", due_day or "")
    if not m:
        return None
    dia = min(max(int(m.group(1)), 1), _ultimo_dia(ano, mes).day)
    return date(ano, mes, dia)


def _status(pago: bool, venc, hoje: date) -> str:
    if pago:
        return "paga"
    if venc is None:
        return "a_pagar"
    if venc < hoje:
        return "vencida"
    if venc == hoje:
        return "hoje"
    return "a_pagar"


def _top(valores: dict) -> str:
    if not valores:
        return "Sem dados"
    nome = max(valores, key=valores.get)
    return f"{nome} · {fmt_moeda(valores[nome])}"


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
class ContasState(AppState):
    # Período e filtros
    mes_offset: int = 0
    mes_label: str = ""
    filtro_loja: str = "todas"
    filtro_situacao: str = "todas"   # todas | a_pagar | vencidas | pagas
    filtro_tipo: str = "todos"       # todos | fixas | variaveis
    busca: str = ""
    ver_lixeira: bool = False

    # Dados
    lojas_opcoes: list[dict[str, str]] = []
    contas_mes: list[dict[str, str]] = []
    lixeira: list[dict[str, str]] = []

    # Números do topo
    n_a_pagar: str = "R$ 0,00"
    n_pago: str = "R$ 0,00"
    n_fixas: str = "R$ 0,00"
    n_variaveis: str = "R$ 0,00"
    n_historico: str = "R$ 0,00"
    n_historico_pago: str = ""
    t_a_pagar: float = 0.0
    t_pago: float = 0.0
    t_fixas: float = 0.0
    t_variaveis: float = 0.0
    t_historico: float = 0.0
    t_historico_pago: float = 0.0

    # Destaques
    destaque_mes: str = "Sem dados"
    destaque_hist: str = "Sem dados"
    destaque_prev: str = "Sem dados"

    # --- permissões ---
    @rx.var
    def pode_agir(self) -> bool:
        return self.role in ("admin", "operator")

    def _pode(self) -> bool:
        return self.role in ("admin", "operator")

    # --- filtros instantâneos (sem consultar o banco) ---
    @rx.var
    def contas_filtradas(self) -> list[dict[str, str]]:
        termo = _norm(self.busca)
        saida = []
        for c in self.contas_mes:
            if self.filtro_situacao == "pagas" and c["status"] != "paga":
                continue
            if self.filtro_situacao == "a_pagar" and c["status"] == "paga":
                continue
            if self.filtro_situacao == "vencidas" and c["status"] != "vencida":
                continue
            if self.filtro_tipo == "fixas" and c["categoria"] != "FIXA":
                continue
            if self.filtro_tipo == "variaveis" and c["categoria"] != "VARIÁVEL":
                continue
            if termo and termo not in f"{c['gasto']} {c['tipo']} {c['loja']}":
                continue
            saida.append(c)
        return saida

    @rx.var
    def resumo_lista(self) -> str:
        itens = self.contas_filtradas
        total = sum(float(c["valor_num"]) for c in itens)
        return f"{len(itens)} conta(s) · {fmt_moeda(total)}"

    # --- carregamento ---
    def abrir(self):
        """Ao abrir a página. Aceita /contas?loja=ID para já filtrar uma loja."""
        try:
            loja_q = self.router.page.params.get("loja", "")
        except Exception:
            loja_q = ""
        self.filtro_loja = str(loja_q) if loja_q else "todas"
        self.ver_lixeira = False
        self._montar()

    def _montar(self):
        hoje = date.today()
        ano, mes = _add_meses(hoje.year, hoje.month, self.mes_offset)
        ini = date(ano, mes, 1)
        fim = _ultimo_dia(ano, mes)
        self.mes_label = f"{MESES[mes - 1]} de {ano}"

        with rx.session() as s:
            lojas_todas = s.exec(select(Store)).all()
            dists = {d.id: _norm(d.name) for d in s.exec(select(Distributor)).all()}
            tipos = {t.id: _norm(t.name) for t in s.exec(select(ExpenseType)).all()}
            boletos = s.exec(select(BoletoEntry)).all()
            fixas = s.exec(select(FixedExpense)).all()
            pagamentos = s.exec(select(FixedExpensePayment)).all()

        lojas_ativas = {x.id: x.name for x in lojas_todas if x.active}
        self.lojas_opcoes = [{"id": str(i), "nome": n} for i, n in lojas_ativas.items()]
        loja_f = int(self.filtro_loja) if self.filtro_loja not in ("", "todas") else None
        pag_map = {(p.fixed_expense_id, p.competencia) for p in pagamentos}
        nomes_fixas = {f.id: _norm(f.name) for f in fixas}

        def loja_ok(store_id: int) -> bool:
            return store_id in lojas_ativas and (loja_f is None or store_id == loja_f)

        # --- contas do mês selecionado ---
        itens = []
        for b in boletos:
            if b.deleted_at or not loja_ok(b.store_id):
                continue
            if not (ini <= b.boleto_date <= fim):
                continue
            venc = b.boleto_date
            parcela = (
                f"{b.parcela_num}/{b.total_parcelas}"
                if b.total_parcelas and b.total_parcelas > 1 else ""
            )
            itens.append({
                "kind": "boleto",
                "id": str(b.id),
                "comp": ini.isoformat(),
                "gasto": dists.get(b.distributor_id, "SEM NOME"),
                "tipo": tipos.get(b.expense_type_id, "SEM TIPO"),
                "loja": lojas_ativas.get(b.store_id, "?"),
                "categoria": "VARIÁVEL",
                "parcela": parcela,
                "valor": fmt_moeda(b.amount),
                "valor_num": f"{b.amount:.2f}",
                "dia": f"{venc.day:02d}",
                "mes_abrev": MESES_ABREV[venc.month - 1],
                "venc_iso": venc.isoformat(),
                "status": _status(b.is_paid, venc, hoje),
            })
        for f in fixas:
            if f.deleted_at or not f.active or not loja_ok(f.store_id):
                continue
            venc = _dia_venc(f.due_day, ano, mes)
            pago = (f.id, ini) in pag_map
            itens.append({
                "kind": "fixa",
                "id": str(f.id),
                "comp": ini.isoformat(),
                "gasto": _norm(f.name),
                "tipo": "CONTA FIXA",
                "loja": lojas_ativas.get(f.store_id, "?"),
                "categoria": "FIXA",
                "parcela": "",
                "valor": fmt_moeda(f.amount),
                "valor_num": f"{f.amount:.2f}",
                "dia": f"{venc.day:02d}" if venc else "--",
                "mes_abrev": MESES_ABREV[mes - 1],
                "venc_iso": venc.isoformat() if venc else "",
                "status": _status(pago, venc, hoje),
            })
        itens.sort(key=lambda c: (c["venc_iso"] or "9999-12-31", c["gasto"]))
        self.contas_mes = itens

        # --- números do mês ---
        total = sum(float(c["valor_num"]) for c in itens)
        pago = sum(float(c["valor_num"]) for c in itens if c["status"] == "paga")
        self.t_pago = pago
        self.t_a_pagar = max(total - pago, 0.0)
        self.t_fixas = sum(float(c["valor_num"]) for c in itens if c["categoria"] == "FIXA")
        self.t_variaveis = sum(float(c["valor_num"]) for c in itens if c["categoria"] == "VARIÁVEL")
        self.n_a_pagar = fmt_moeda(self.t_a_pagar)
        self.n_pago = fmt_moeda(self.t_pago)
        self.n_fixas = fmt_moeda(self.t_fixas)
        self.n_variaveis = fmt_moeda(self.t_variaveis)

        # --- histórico (tudo que já foi lançado e pago) ---
        hist = 0.0
        hist_pago = 0.0
        por_tipo_hist = defaultdict(float)
        for b in boletos:
            if b.deleted_at or not loja_ok(b.store_id):
                continue
            hist += b.amount
            if b.is_paid:
                hist_pago += b.amount
            chave = tipos.get(b.expense_type_id) or dists.get(b.distributor_id, "OUTROS")
            por_tipo_hist[chave] += b.amount
        for p in pagamentos:
            if not loja_ok(p.store_id):
                continue
            hist += p.amount
            hist_pago += p.amount
            por_tipo_hist[nomes_fixas.get(p.fixed_expense_id, "CONTA FIXA")] += p.amount
        self.t_historico = hist
        self.t_historico_pago = hist_pago
        self.n_historico = fmt_moeda(hist)
        self.n_historico_pago = f"({fmt_moeda(hist_pago)} pagos)"

        # --- destaques ---
        por_tipo_mes = defaultdict(float)
        for c in itens:
            if c["categoria"] == "FIXA":
                chave = c["gasto"]
            else:
                chave = c["tipo"] if c["tipo"] != "SEM TIPO" else c["gasto"]
            por_tipo_mes[chave] += float(c["valor_num"])

        limite = hoje + timedelta(days=30)
        por_tipo_prev = defaultdict(float)
        for b in boletos:
            if b.deleted_at or b.is_paid or not loja_ok(b.store_id):
                continue
            if hoje <= b.boleto_date <= limite:
                chave = tipos.get(b.expense_type_id) or dists.get(b.distributor_id, "OUTROS")
                por_tipo_prev[chave] += b.amount
        meses_janela = {(hoje.year, hoje.month), (limite.year, limite.month)}
        for f in fixas:
            if f.deleted_at or not f.active or not loja_ok(f.store_id):
                continue
            for a, m in meses_janela:
                venc = _dia_venc(f.due_day, a, m)
                if venc and hoje <= venc <= limite and (f.id, date(a, m, 1)) not in pag_map:
                    por_tipo_prev[_norm(f.name)] += f.amount

        self.destaque_mes = _top(por_tipo_mes)
        self.destaque_hist = _top(por_tipo_hist)
        self.destaque_prev = _top(por_tipo_prev)

        # --- lixeira ---
        lix = []
        for b in boletos:
            if not b.deleted_at or not loja_ok(b.store_id):
                continue
            lix.append({
                "kind": "boleto",
                "id": str(b.id),
                "gasto": dists.get(b.distributor_id, "SEM NOME"),
                "detalhe": (
                    f"{tipos.get(b.expense_type_id, 'SEM TIPO')} · "
                    f"{lojas_ativas.get(b.store_id, '?')} · venc. {b.boleto_date:%d/%m/%Y}"
                ),
                "valor": fmt_moeda(b.amount),
                "quando": f"Excluída em {b.deleted_at:%d/%m/%Y}",
            })
        for f in fixas:
            if not f.deleted_at or not loja_ok(f.store_id):
                continue
            lix.append({
                "kind": "fixa",
                "id": str(f.id),
                "gasto": _norm(f.name),
                "detalhe": f"CONTA FIXA · {lojas_ativas.get(f.store_id, '?')}",
                "valor": fmt_moeda(f.amount),
                "quando": f"Excluída em {f.deleted_at:%d/%m/%Y}",
            })
        self.lixeira = lix

    # --- navegação e filtros ---
    def mes_anterior(self):
        self.mes_offset -= 1
        self._montar()

    def mes_proximo(self):
        self.mes_offset += 1
        self._montar()

    def mes_atual(self):
        self.mes_offset = 0
        self._montar()

    def set_filtro_loja(self, v: str):
        self.filtro_loja = v
        self._montar()

    def set_filtro_situacao(self, v):
        self.filtro_situacao = v[0] if isinstance(v, list) else v

    def set_filtro_tipo(self, v: str):
        self.filtro_tipo = v

    def set_busca(self, v: str):
        self.busca = v

    def alternar_lixeira(self):
        self.ver_lixeira = not self.ver_lixeira

    # --- ações (todas exigem confirmação na tela) ---
    def pagar(self, kind: str, id_txt: str, comp: str):
        if not self._pode():
            return aviso_erro("Seu nível de acesso não permite alterar contas.")
        agora = datetime.utcnow()
        with rx.session() as s:
            if kind == "boleto":
                b = s.get(BoletoEntry, int(id_txt))
                if not b or b.deleted_at:
                    return aviso_erro("Conta não encontrada.")
                b.is_paid = True
                b.paid_at = agora
                b.paid_by = self.user_id
                s.add(b)
                self.log_auditoria(s, "pay", "boleto_entry", b.id, f"Despesa paga: {fmt_moeda(b.amount)}")
            else:
                f = s.get(FixedExpense, int(id_txt))
                if not f or f.deleted_at:
                    return aviso_erro("Conta não encontrada.")
                competencia = date.fromisoformat(comp)
                existe = s.exec(
                    select(FixedExpensePayment).where(
                        FixedExpensePayment.fixed_expense_id == f.id,
                        FixedExpensePayment.competencia == competencia,
                    )
                ).first()
                if not existe:
                    s.add(FixedExpensePayment(
                        fixed_expense_id=f.id,
                        store_id=f.store_id,
                        competencia=competencia,
                        amount=f.amount,
                        paid_at=agora,
                        paid_by=self.user_id,
                    ))
                if competencia == date.today().replace(day=1):
                    f.is_paid = True
                    f.paid_at = agora
                    f.paid_by = self.user_id
                    s.add(f)
                self.log_auditoria(
                    s, "pay", "fixed_expense", f.id,
                    f"Conta fixa paga ({competencia:%m/%Y}): {_norm(f.name)}",
                )
            s.commit()
        self._montar()
        return aviso_sucesso("Pagamento registrado.")

    def desfazer(self, kind: str, id_txt: str, comp: str):
        if not self._pode():
            return aviso_erro("Seu nível de acesso não permite alterar contas.")
        with rx.session() as s:
            if kind == "boleto":
                b = s.get(BoletoEntry, int(id_txt))
                if not b:
                    return aviso_erro("Conta não encontrada.")
                b.is_paid = False
                b.paid_at = None
                b.paid_by = None
                s.add(b)
                self.log_auditoria(s, "unpay", "boleto_entry", b.id, "Pagamento desfeito")
            else:
                f = s.get(FixedExpense, int(id_txt))
                if not f:
                    return aviso_erro("Conta não encontrada.")
                competencia = date.fromisoformat(comp)
                pag = s.exec(
                    select(FixedExpensePayment).where(
                        FixedExpensePayment.fixed_expense_id == f.id,
                        FixedExpensePayment.competencia == competencia,
                    )
                ).first()
                if pag:
                    s.delete(pag)
                if competencia == date.today().replace(day=1):
                    f.is_paid = False
                    f.paid_at = None
                    f.paid_by = None
                    s.add(f)
                self.log_auditoria(
                    s, "unpay", "fixed_expense", f.id,
                    f"Pagamento desfeito ({competencia:%m/%Y}): {_norm(f.name)}",
                )
            s.commit()
        self._montar()
        return aviso_sucesso("Pagamento desfeito. A conta voltou para A PAGAR.")

    def excluir(self, kind: str, id_txt: str):
        if not self._pode():
            return aviso_erro("Seu nível de acesso não permite excluir contas.")
        agora = datetime.utcnow()
        with rx.session() as s:
            modelo = BoletoEntry if kind == "boleto" else FixedExpense
            obj = s.get(modelo, int(id_txt))
            if not obj or obj.deleted_at:
                return aviso_erro("Conta não encontrada.")
            obj.deleted_at = agora
            obj.deleted_by = self.user_id
            if kind == "fixa":
                obj.active = False  # some também das telas antigas
            s.add(obj)
            self.log_auditoria(
                s, "delete", "boleto_entry" if kind == "boleto" else "fixed_expense",
                obj.id, "Enviada para a lixeira",
            )
            s.commit()
        self._montar()
        return aviso_sucesso("Conta enviada para a lixeira. Você pode restaurá-la quando quiser.")

    def restaurar(self, kind: str, id_txt: str):
        if not self._pode():
            return aviso_erro("Seu nível de acesso não permite restaurar contas.")
        with rx.session() as s:
            modelo = BoletoEntry if kind == "boleto" else FixedExpense
            obj = s.get(modelo, int(id_txt))
            if not obj or not obj.deleted_at:
                return aviso_erro("Conta não encontrada na lixeira.")
            obj.deleted_at = None
            obj.deleted_by = None
            if kind == "fixa":
                obj.active = True
            s.add(obj)
            self.log_auditoria(
                s, "restore", "boleto_entry" if kind == "boleto" else "fixed_expense",
                obj.id, "Restaurada da lixeira",
            )
            s.commit()
        self._montar()
        return aviso_sucesso("Conta restaurada.")

    # --- exportação para Excel ---
    def exportar(self):
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        vermelho = PatternFill("solid", fgColor="E31E24")
        branco = Font(color="FFFFFF", bold=True)
        moeda = "R$ #,##0.00"
        formato_data = "DD/MM/YYYY"

        def cabecalho(ws, linha, titulos, larguras):
            for i, (titulo, larg) in enumerate(zip(titulos, larguras), start=1):
                c = ws.cell(row=linha, column=i, value=titulo)
                c.fill = vermelho
                c.font = branco
                c.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions[get_column_letter(i)].width = larg
            ws.freeze_panes = f"A{linha + 1}"

        def finalizar(ws, linha_cab, n_colunas):
            ultima = get_column_letter(n_colunas)
            if ws.max_row > linha_cab:
                ws.auto_filter.ref = f"A{linha_cab}:{ultima}{ws.max_row}"

        nome_loja = next(
            (x["nome"] for x in self.lojas_opcoes if x["id"] == self.filtro_loja),
            "Todas as lojas",
        )
        wb = openpyxl.Workbook()

        # Aba 1: Resumo
        ws = wb.active
        ws.title = "Resumo"
        ws["A1"] = f"Passivo Cumani — Contas de {self.mes_label}"
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = f"Loja: {nome_loja}  ·  Gerado em {datetime.now():%d/%m/%Y %H:%M}"
        linhas = [
            ("A pagar no mês", self.t_a_pagar),
            ("Pago no mês", self.t_pago),
            ("Contas fixas no mês", self.t_fixas),
            ("Despesas variáveis no mês", self.t_variaveis),
            ("Total histórico", self.t_historico),
            ("Total histórico pago", self.t_historico_pago),
        ]
        cabecalho(ws, 4, ["Indicador", "Valor"], [34, 40])
        for i, (rotulo, valor) in enumerate(linhas, start=5):
            ws.cell(row=i, column=1, value=rotulo)
            ws.cell(row=i, column=2, value=round(valor, 2)).number_format = moeda
        base = 5 + len(linhas) + 1
        destaques = [
            ("Principal despesa do mês", self.destaque_mes),
            ("Principal despesa histórica", self.destaque_hist),
            ("Principal previsão (30 dias)", self.destaque_prev),
        ]
        for i, (rotulo, valor) in enumerate(destaques):
            ws.cell(row=base + i, column=1, value=rotulo).font = Font(bold=True)
            ws.cell(row=base + i, column=2, value=valor)

        # Aba 2: Contas do mês (como estão filtradas na tela)
        ws = wb.create_sheet("Contas")
        titulos = ["Vencimento", "Loja", "Gasto", "Tipo", "Categoria", "Parcela", "Valor", "Situação"]
        cabecalho(ws, 1, titulos, [14, 22, 32, 24, 13, 10, 16, 14])
        rotulos = {"paga": "PAGA", "vencida": "VENCIDA", "hoje": "VENCE HOJE", "a_pagar": "A PAGAR"}
        for c in self.contas_filtradas:
            venc = date.fromisoformat(c["venc_iso"]) if c["venc_iso"] else None
            ws.append([
                venc, c["loja"], c["gasto"], c["tipo"], c["categoria"],
                c["parcela"], float(c["valor_num"]), rotulos.get(c["status"], ""),
            ])
            ws.cell(row=ws.max_row, column=1).number_format = formato_data
            ws.cell(row=ws.max_row, column=7).number_format = moeda
        finalizar(ws, 1, len(titulos))

        # Aba 3: Histórico completo
        ws = wb.create_sheet("Histórico")
        titulos = [
            "Lançamento", "Vencimento", "Loja", "Gasto", "Tipo", "Parcela",
            "Valor", "Forma", "Situação", "Observações",
        ]
        cabecalho(ws, 1, titulos, [14, 14, 22, 32, 24, 10, 16, 16, 12, 40])
        loja_f = int(self.filtro_loja) if self.filtro_loja not in ("", "todas") else None
        with rx.session() as s:
            lojas = {x.id: x.name for x in s.exec(select(Store)).all() if x.active}
            dists = {d.id: _norm(d.name) for d in s.exec(select(Distributor)).all()}
            tipos = {t.id: _norm(t.name) for t in s.exec(select(ExpenseType)).all()}
            fixas = {f.id: _norm(f.name) for f in s.exec(select(FixedExpense)).all()}
            boletos = s.exec(select(BoletoEntry).order_by(BoletoEntry.boleto_date)).all()
            pagamentos = s.exec(
                select(FixedExpensePayment).order_by(FixedExpensePayment.competencia)
            ).all()
        for b in boletos:
            if b.deleted_at or b.store_id not in lojas or (loja_f and b.store_id != loja_f):
                continue
            parcela = (
                f"{b.parcela_num}/{b.total_parcelas}"
                if b.total_parcelas and b.total_parcelas > 1 else ""
            )
            ws.append([
                b.data_lancamento, b.boleto_date, lojas[b.store_id],
                dists.get(b.distributor_id, ""), tipos.get(b.expense_type_id, ""),
                parcela, round(b.amount, 2), b.payment_method,
                "PAGA" if b.is_paid else "A PAGAR", b.notes or "",
            ])
            ws.cell(row=ws.max_row, column=1).number_format = formato_data
            ws.cell(row=ws.max_row, column=2).number_format = formato_data
            ws.cell(row=ws.max_row, column=7).number_format = moeda
        for p in pagamentos:
            if p.store_id not in lojas or (loja_f and p.store_id != loja_f):
                continue
            ws.append([
                p.paid_at.date() if p.paid_at else None, p.competencia, lojas[p.store_id],
                fixas.get(p.fixed_expense_id, ""), "CONTA FIXA", "",
                round(p.amount, 2), "", "PAGA", "",
            ])
            ws.cell(row=ws.max_row, column=1).number_format = formato_data
            ws.cell(row=ws.max_row, column=2).number_format = formato_data
            ws.cell(row=ws.max_row, column=7).number_format = moeda
        finalizar(ws, 1, len(titulos))

        buf = io.BytesIO()
        wb.save(buf)
        nome = f"contas_cumani_{datetime.now():%Y-%m-%d}.xlsx"
        return [
            rx.download(data=buf.getvalue(), filename=nome),
            aviso_sucesso("Planilha gerada. Confira a pasta de downloads."),
        ]