"""Página de Lançamentos: sugestão automática, confirmação e aviso visual."""
import calendar
import re
import uuid
from datetime import date, datetime

import reflex as rx
from sqlmodel import select

from ..models import Store, Distributor, ExpenseType, BoletoEntry, FixedExpense
from ..state import LancamentosState
from ..components.navbar import page_shell
from ..components.cards import card_container
from ..components.ux import aviso_sucesso, aviso_erro
from ..utils.helpers import fmt_moeda, periodo_semana_str
from ..theme import PRIMARY, PRIMARY_HOVER, TEXT_MUTED, TEXT_TITLE, BORDER, SUCCESS, WARNING

FORMAS = ["PIX", "BOLETO", "DINHEIRO", "CARTÃO", "CAJU", "TRANSFERÊNCIA"]


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def _norm(texto: str) -> str:
    """Remove espaços extras e converte para maiúsculas."""
    return " ".join((texto or "").split()).upper()


def _valor(texto: str):
    """Aceita 1.234,56 / 1234,56 / 1234.56. Retorna None se for inválido."""
    t = (texto or "").upper().replace("R$", "").replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return round(float(t), 2)
    except ValueError:
        return None


def _data(texto: str):
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _dia_de(due_day: str) -> str:
    m = re.search(r"(\d{1,2})", due_day or "")
    return m.group(1) if m else ""


def _ts(dt) -> float:
    try:
        return dt.timestamp() if dt else 0.0
    except (ValueError, OSError):
        return 0.0


def _somar_meses(base: date, n: int) -> date:
    m = base.month - 1 + n
    ano = base.year + m // 12
    mes = m % 12 + 1
    dia = min(base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


# ---------------------------------------------------------------------------
# Estado da tela (herda o LancamentosState: a loja escolhida é compartilhada)
# ---------------------------------------------------------------------------
class LancamentoState(LancamentosState):
    modo: str = "outros"  # outros | fixa

    # Outras despesas
    o_gasto: str = ""
    o_tipo: str = ""
    o_valor: str = ""
    o_forma: str = "PIX"
    o_pago: bool = False
    o_venc: str = ""
    o_data: str = ""
    o_obs: str = ""
    o_parcelado: bool = False
    o_nparc: str = "2"
    o_datas: list[dict[str, str]] = []

    # Conta fixa
    f_nome: str = ""
    f_valor: str = ""
    f_dia: str = ""
    f_forma: str = "PIX"
    f_pago: bool = False

    # Sugestões e listas
    sug_gasto: list[str] = []
    sug_tipo: list[str] = []
    sug_fixa: list[str] = []
    fixas_loja: list[dict[str, str]] = []
    recentes: list[dict] = []

    # Confirmação
    confirma_aberta: bool = False
    resumo: list[str] = []

    # --- carregamento ---
    def carregar(self):
        if not self.o_data:
            self.o_data = date.today().isoformat()
        with rx.session() as s:
            lojas = s.exec(select(Store).where(Store.active == True)).all()  # noqa: E712
            self.stores = [{"id": str(x.id), "name": x.name} for x in lojas]
            ids = [x["id"] for x in self.stores]
            if self.stores and self.selected_store_id not in ids:
                self.selected_store_id = self.stores[0]["id"]
            self.sug_gasto = sorted({_norm(d.name) for d in s.exec(select(Distributor)).all() if d.active})
            self.sug_tipo = sorted({_norm(t.name) for t in s.exec(select(ExpenseType)).all() if t.active})
        self._carregar_fixas_loja()
        self._carregar_recentes()

    def _carregar_fixas_loja(self):
        if not self.selected_store_id:
            self.fixas_loja = []
            self.sug_fixa = []
            return
        with rx.session() as s:
            fixas = s.exec(
                select(FixedExpense).where(
                    FixedExpense.store_id == int(self.selected_store_id),
                    FixedExpense.active == True,  # noqa: E712
                )
            ).all()
        self.fixas_loja = [
            {
                "nome": _norm(f.name),
                "valor": f"{f.amount:.2f}".replace(".", ","),
                "dia": _dia_de(f.due_day),
            }
            for f in fixas
        ]
        self.sug_fixa = sorted({f["nome"] for f in self.fixas_loja})

    def _carregar_recentes(self):
        with rx.session() as s:
            lojas = {x.id: x.name for x in s.exec(select(Store)).all()}
            dists = {d.id: _norm(d.name) for d in s.exec(select(Distributor)).all()}
            tipos = {t.id: _norm(t.name) for t in s.exec(select(ExpenseType)).all()}
            boletos = s.exec(
                select(BoletoEntry).order_by(BoletoEntry.created_at.desc()).limit(10)
            ).all()
            fixas = s.exec(
                select(FixedExpense)
                .where(FixedExpense.active == True)  # noqa: E712
                .order_by(FixedExpense.created_at.desc())
                .limit(10)
            ).all()

        itens = []
        for b in boletos:
            gasto = dists.get(b.distributor_id, "SEM NOME")
            if b.total_parcelas and b.total_parcelas > 1:
                gasto += f" ({b.parcela_num}/{b.total_parcelas})"
            tipo = tipos.get(b.expense_type_id, "SEM TIPO")
            if b.is_paid and b.data_lancamento and b.boleto_date == b.data_lancamento:
                data_txt = f"Lançado em {_br(b.data_lancamento)}"
            else:
                data_txt = f"Venc. {_br(b.boleto_date)}" + (" ✓" if b.is_paid else "")
            itens.append({
                "gasto": gasto,
                "detalhe": f"{tipo} · {lojas.get(b.store_id, '?')}",
                "valor": fmt_moeda(b.amount),
                "data": data_txt,
                "pago": bool(b.is_paid),
                "ts": _ts(b.created_at),
            })
        for f in fixas:
            dia = _dia_de(f.due_day)
            data_txt = (f"Vence todo dia {dia}" if dia else "Conta fixa") + (" ✓" if f.is_paid else "")
            itens.append({
                "gasto": _norm(f.name),
                "detalhe": f"CONTA FIXA · {lojas.get(f.store_id, '?')}",
                "valor": fmt_moeda(f.amount),
                "data": data_txt,
                "pago": bool(f.is_paid),
                "ts": _ts(f.created_at),
            })
        itens.sort(key=lambda x: x["ts"], reverse=True)
        for i in itens:
            i.pop("ts", None)
        self.recentes = itens[:10]

    # --- campos ---
    def escolher_loja(self, v: str):
        self.selected_store_id = v
        self._carregar_fixas_loja()

    def set_modo(self, v):
        self.modo = v[0] if isinstance(v, list) else v

    def set_o_gasto(self, v: str):
        self.o_gasto = v

    def set_o_tipo(self, v: str):
        self.o_tipo = v

    def set_o_valor(self, v: str):
        self.o_valor = v

    def set_o_forma(self, v: str):
        self.o_forma = v

    def set_o_pago(self, v: bool):
        self.o_pago = bool(v)

    def set_o_data(self, v: str):
        self.o_data = v

    def set_o_obs(self, v: str):
        self.o_obs = v

    def set_o_venc(self, v: str):
        self.o_venc = v
        if self.o_parcelado:
            self._gerar_parcelas()

    def set_o_parcelado(self, v: bool):
        self.o_parcelado = bool(v)
        if self.o_parcelado:
            self.o_pago = False
        self._gerar_parcelas()

    def set_o_nparc(self, v: str):
        self.o_nparc = v
        self._gerar_parcelas()

    def set_parcela(self, idx: int, v: str):
        if idx == 0:
            self.o_venc = v
            self._gerar_parcelas()
            return
        datas = [dict(p) for p in self.o_datas]
        if idx < len(datas):
            datas[idx]["data"] = v
            self.o_datas = datas

    def set_f_nome(self, v: str):
        self.f_nome = v
        alvo = _norm(v)
        for f in self.fixas_loja:
            if f["nome"] == alvo:
                self.f_valor = f["valor"]
                self.f_dia = f["dia"]
                break

    def set_f_valor(self, v: str):
        self.f_valor = v

    def set_f_dia(self, v: str):
        self.f_dia = v

    def set_f_forma(self, v: str):
        self.f_forma = v

    def set_f_pago(self, v: bool):
        self.f_pago = bool(v)

    # --- parcelas ---
    def _n_parcelas(self) -> int:
        try:
            return min(max(int(self.o_nparc or 2), 2), 60)
        except ValueError:
            return 2

    def _gerar_parcelas(self):
        base = _data(self.o_venc)
        if not self.o_parcelado or base is None:
            self.o_datas = []
            return
        self.o_datas = [
            {"label": f"{i + 1}ª parcela", "data": _somar_meses(base, i).isoformat()}
            for i in range(self._n_parcelas())
        ]

    @rx.var
    def o_valor_parcela(self) -> str:
        v = _valor(self.o_valor)
        if not v or not self.o_parcelado:
            return ""
        return fmt_moeda(round(v / self._n_parcelas(), 2))

    def _loja_nome(self) -> str:
        return next((x["name"] for x in self.stores if x["id"] == self.selected_store_id), "?")

    # --- validação ---
    def _validar(self):
        if not self.selected_store_id:
            return "Escolha a loja.", {}
        if self.modo == "fixa":
            return self._validar_fixa()
        return self._validar_outros()

    def _validar_outros(self):
        gasto = _norm(self.o_gasto)
        if not gasto:
            return "Informe o gasto (ex.: LUZ, REFORMA).", {}
        tipo = _norm(self.o_tipo)
        valor = _valor(self.o_valor)
        if valor is None:
            return "Valor inválido. Use o formato 1.234,56.", {}
        if valor <= 0:
            return "O valor precisa ser maior que zero.", {}
        if self.o_data and _data(self.o_data) is None:
            return "Data de lançamento inválida.", {}
        data_lanc = _data(self.o_data) or date.today()

        if self.o_parcelado:
            n = self._n_parcelas()
            if not self.o_venc:
                return "Informe o vencimento da 1ª parcela.", {}
            datas = [_data(p["data"]) for p in self.o_datas[:n]]
            if len(datas) != n or any(d is None for d in datas):
                return "Confira as datas das parcelas.", {}
            base = round(valor / n, 2)
            valores = [base] * n
            valores[-1] = round(valor - base * (n - 1), 2)
            pago = False
            venc_txt = f"{n} parcelas de {fmt_moeda(base)}, de {_br(datas[0])} a {_br(datas[-1])}"
        else:
            venc = _data(self.o_venc)
            if self.o_venc and venc is None:
                return "Data de vencimento inválida.", {}
            if venc is None:
                if not self.o_pago:
                    return "Informe o vencimento: ele é obrigatório para despesas ainda não pagas.", {}
                venc = data_lanc
                venc_txt = f"Sem vencimento (conta em {data_lanc:%m/%Y})"
            else:
                venc_txt = _br(venc)
            datas = [venc]
            valores = [valor]
            pago = self.o_pago

        resumo = [
            f"Loja: {self._loja_nome()}",
            f"Gasto: {gasto}",
            f"Tipo de despesa: {tipo or 'NÃO INFORMADO'}",
            f"Valor: {fmt_moeda(valor)}",
            f"Vencimento: {venc_txt}",
            f"Data de lançamento: {_br(data_lanc)}",
            f"Forma de pagamento: {self.o_forma}",
            f"Situação: {'DESPESA PAGA' if pago else 'A PAGAR'}",
        ]
        return "", {
            "loja_id": int(self.selected_store_id),
            "gasto": gasto,
            "tipo": tipo,
            "valor": valor,
            "datas": datas,
            "valores": valores,
            "pago": pago,
            "data_lanc": data_lanc,
            "resumo": resumo,
        }

    def _validar_fixa(self):
        nome = _norm(self.f_nome)
        if not nome:
            return "Informe o nome da conta fixa (ex.: ALUGUEL).", {}
        valor = _valor(self.f_valor)
        if valor is None or valor <= 0:
            return "Informe um valor mensal válido, no formato 1.234,56.", {}
        try:
            dia = int(self.f_dia)
        except ValueError:
            return "Informe o dia de vencimento (1 a 31).", {}
        if not 1 <= dia <= 31:
            return "O dia de vencimento precisa estar entre 1 e 31.", {}
        existente = any(f["nome"] == nome for f in self.fixas_loja)
        resumo = [
            f"Loja: {self._loja_nome()}",
            f"Conta fixa: {nome} " + ("(já cadastrada, será atualizada)" if existente else "(nova)"),
            f"Valor mensal: {fmt_moeda(valor)}",
            f"Vence todo dia {dia}",
            f"Forma de pagamento: {self.f_forma}",
            f"Situação neste mês: {'PAGA' if self.f_pago else 'A PAGAR'}",
        ]
        return "", {
            "loja_id": int(self.selected_store_id),
            "nome": nome,
            "valor": valor,
            "dia": dia,
            "pago": self.f_pago,
            "resumo": resumo,
        }

    # --- confirmação e gravação ---
    def revisar(self):
        if self.role not in ("admin", "operator"):
            return aviso_erro("Seu nível de acesso não permite lançar despesas.")
        erro, dados = self._validar()
        if erro:
            return aviso_erro(erro)
        self.resumo = dados["resumo"]
        self.confirma_aberta = True

    def fechar_confirma(self):
        self.confirma_aberta = False

    def confirmar_salvar(self):
        if self.role not in ("admin", "operator"):
            self.confirma_aberta = False
            return aviso_erro("Seu nível de acesso não permite lançar despesas.")
        erro, dados = self._validar()
        if erro:
            self.confirma_aberta = False
            return aviso_erro(erro)
        msg = self._salvar_fixa(dados) if self.modo == "fixa" else self._salvar_outros(dados)
        self.confirma_aberta = False
        self._limpar()
        self.carregar()
        return aviso_sucesso(msg)

    def _achar_ou_criar(self, s, modelo, nome: str, **extra):
        for obj in s.exec(select(modelo)).all():
            if _norm(obj.name) == nome:
                if not obj.active:
                    obj.active = True
                    s.add(obj)
                return obj
        novo = modelo(
            name=nome,
            created_by=self.user_id,
            created_by_operator=(self.role == "operator"),
            **extra,
        )
        s.add(novo)
        s.flush()
        return novo

    def _salvar_outros(self, d: dict) -> str:
        n = len(d["datas"])
        grupo = uuid.uuid4().hex if n > 1 else None
        with rx.session() as s:
            dist = self._achar_ou_criar(s, Distributor, d["gasto"])
            tipo_id = None
            if d["tipo"]:
                tipo_id = self._achar_ou_criar(s, ExpenseType, d["tipo"], category="Variável").id
            for i, (venc, val) in enumerate(zip(d["datas"], d["valores"]), start=1):
                b = BoletoEntry(
                    store_id=d["loja_id"],
                    distributor_id=dist.id,
                    boleto_date=venc,
                    amount=val,
                    payment_method=self.o_forma,
                    expense_type_id=tipo_id,
                    notes=_norm(self.o_obs),
                    operator_id=self.user_id,
                    week_period=periodo_semana_str(venc),
                    data_lancamento=d["data_lanc"],
                    parcela_num=i if n > 1 else None,
                    total_parcelas=n if n > 1 else None,
                    grupo_parcelas=grupo,
                    is_paid=d["pago"],
                    paid_at=datetime.utcnow() if d["pago"] else None,
                    paid_by=self.user_id if d["pago"] else None,
                )
                s.add(b)
                s.flush()
                self.log_auditoria(
                    s, "create", "boleto_entry", b.id,
                    f"{d['gasto']} {i}/{n} {fmt_moeda(val)}" if n > 1 else f"{d['gasto']} {fmt_moeda(val)}",
                )
            s.commit()
        if n > 1:
            return f"Despesa lançada: {d['gasto']} — {fmt_moeda(d['valor'])} em {n} parcelas"
        return f"Despesa lançada: {d['gasto']} — {fmt_moeda(d['valor'])}"

    def _salvar_fixa(self, d: dict) -> str:
        with rx.session() as s:
            conta = None
            for f in s.exec(
                select(FixedExpense).where(
                    FixedExpense.store_id == d["loja_id"],
                    FixedExpense.active == True,  # noqa: E712
                )
            ).all():
                if _norm(f.name) == d["nome"]:
                    conta = f
                    break
            nova = conta is None
            if nova:
                conta = FixedExpense(
                    store_id=d["loja_id"],
                    name=d["nome"],
                    created_by=self.user_id,
                    created_by_operator=(self.role == "operator"),
                )
            conta.name = d["nome"]
            conta.amount = d["valor"]
            conta.due_day = f"DIA {d['dia']}"
            conta.payment_method = self.f_forma
            conta.is_paid = d["pago"]
            conta.paid_at = datetime.utcnow() if d["pago"] else None
            conta.paid_by = self.user_id if d["pago"] else None
            s.add(conta)
            s.flush()
            self.log_auditoria(
                s, "create" if nova else "update", "fixed_expense", conta.id,
                f"Conta fixa {d['nome']} {fmt_moeda(d['valor'])}",
            )
            s.commit()
        acao = "cadastrada" if nova else "atualizada"
        return f"Conta fixa {acao}: {d['nome']} — {fmt_moeda(d['valor'])}"

    def _limpar(self):
        self.o_gasto = ""
        self.o_tipo = ""
        self.o_valor = ""
        self.o_pago = False
        self.o_venc = ""
        self.o_data = date.today().isoformat()
        self.o_obs = ""
        self.o_parcelado = False
        self.o_nparc = "2"
        self.o_datas = []
        self.f_nome = ""
        self.f_valor = ""
        self.f_dia = ""
        self.f_pago = False
        self.resumo = []


# ---------------------------------------------------------------------------
# Componentes da tela
# ---------------------------------------------------------------------------
LS = LancamentoState

CAMPO_CSS = {
    "width": "100%",
    "height": "40px",
    "padding": "0 12px",
    "border": f"1px solid {BORDER}",
    "border_radius": "8px",
    "font_size": "15px",
    "background": "white",
    "text_transform": "uppercase",
    "outline": "none",
}
FOCO = {"border_color": PRIMARY, "box_shadow": "0 0 0 3px rgba(220,38,38,0.15)"}


def _rotulo(texto) -> rx.Component:
    return rx.text(texto, size="2", weight="medium", color=TEXT_TITLE)


def _campo(rotulo, componente, ajuda=None) -> rx.Component:
    return rx.vstack(
        _rotulo(rotulo),
        componente,
        rx.text(ajuda, size="1", color=TEXT_MUTED) if ajuda is not None else rx.fragment(),
        spacing="1",
        width="100%",
    )


def _campo_sugestao(id_lista: str, valor, ao_mudar, sugestoes, exemplo: str) -> rx.Component:
    """Campo de texto que sugere nomes já usados enquanto você digita."""
    return rx.box(
        rx.el.input(
            value=valor,
            on_change=ao_mudar,
            placeholder=exemplo,
            custom_attrs={"list": id_lista, "autoComplete": "off"},
            style=CAMPO_CSS,
            _focus=FOCO,
        ),
        rx.el.datalist(
            rx.foreach(sugestoes, lambda s: rx.el.option(value=s)),
            id=id_lista,
        ),
        width="100%",
    )


def _card_loja() -> rx.Component:
    return card_container(
        _campo(
            "Loja",
            rx.select.root(
                rx.select.trigger(placeholder="Selecione a loja", width="100%"),
                rx.select.content(
                    rx.foreach(LS.stores, lambda x: rx.select.item(x["name"], value=x["id"])),
                ),
                value=LS.selected_store_id,
                on_change=LS.escolher_loja,
                size="3",
            ),
        ),
    )


def _bloco_vencimento() -> rx.Component:
    return _campo(
        rx.cond(LS.o_pago, "Vencimento (opcional)", "Vencimento *"),
        rx.input(type="date", value=LS.o_venc, on_change=LS.set_o_venc, size="3", width="100%"),
        rx.cond(
            LS.o_pago,
            "Sem vencimento, a despesa conta no mês da data de lançamento.",
            "Obrigatório para despesas que ainda não foram pagas.",
        ),
    )


def _linha_parcela(p, i) -> rx.Component:
    return rx.hstack(
        rx.text(p["label"], size="2", width="110px"),
        rx.input(
            type="date",
            value=p["data"],
            on_change=lambda v: LS.set_parcela(i, v),
            width="100%",
        ),
        width="100%",
        align="center",
    )


def _bloco_parcelas() -> rx.Component:
    return rx.vstack(
        rx.grid(
            _campo(
                "Nº de parcelas",
                rx.input(type="number", value=LS.o_nparc, on_change=LS.set_o_nparc, size="3", width="100%"),
            ),
            _campo(
                "Vencimento da 1ª parcela *",
                rx.input(type="date", value=LS.o_venc, on_change=LS.set_o_venc, size="3", width="100%"),
            ),
            columns=rx.breakpoints(initial="1", sm="2"),
            spacing="3",
            width="100%",
        ),
        rx.cond(
            LS.o_valor_parcela != "",
            rx.text("Valor de cada parcela: ", LS.o_valor_parcela, size="2", weight="bold"),
        ),
        rx.text(
            "As datas seguintes são sugeridas mês a mês. Você pode alterar qualquer uma.",
            size="1",
            color=TEXT_MUTED,
        ),
        rx.foreach(LS.o_datas, _linha_parcela),
        spacing="2",
        width="100%",
    )


def _form_outros() -> rx.Component:
    return rx.vstack(
        _campo(
            "Gasto *",
            _campo_sugestao("lista-gastos", LS.o_gasto, LS.set_o_gasto, LS.sug_gasto, "Ex.: LUZ, REFORMA, DISTRIBUIDORA"),
            "Comece a digitar: os nomes já usados aparecem como sugestão.",
        ),
        _campo(
            "Tipo de despesa",
            _campo_sugestao("lista-tipos", LS.o_tipo, LS.set_o_tipo, LS.sug_tipo, "Ex.: MANUTENÇÃO, MATERIAL"),
        ),
        rx.grid(
            _campo(
                "Valor *",
                rx.input(
                    placeholder="0,00",
                    value=LS.o_valor,
                    on_change=LS.set_o_valor,
                    size="3",
                    width="100%",
                    custom_attrs={"inputMode": "decimal"},
                ),
            ),
            _campo(
                "Forma de pagamento",
                rx.select(FORMAS, value=LS.o_forma, on_change=LS.set_o_forma, size="3", width="100%"),
            ),
            columns=rx.breakpoints(initial="1", sm="2"),
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.cond(
                LS.o_parcelado,
                rx.fragment(),
                rx.checkbox("Já está pago", checked=LS.o_pago, on_change=LS.set_o_pago, size="2"),
            ),
            rx.checkbox("Parcelado", checked=LS.o_parcelado, on_change=LS.set_o_parcelado, size="2"),
            spacing="5",
            wrap="wrap",
        ),
        rx.cond(LS.o_parcelado, _bloco_parcelas(), _bloco_vencimento()),
        _campo(
            "Data de lançamento",
            rx.input(type="date", value=LS.o_data, on_change=LS.set_o_data, size="3", width="100%"),
            "Já vem com a data de hoje. Altere se precisar.",
        ),
        _campo(
            "Observações",
            rx.text_area(
                value=LS.o_obs,
                on_change=LS.set_o_obs,
                placeholder="Opcional",
                width="100%",
                style={"text_transform": "uppercase"},
            ),
        ),
        spacing="4",
        width="100%",
    )


def _form_fixa() -> rx.Component:
    return rx.vstack(
        _campo(
            "Conta fixa *",
            _campo_sugestao("lista-fixas", LS.f_nome, LS.set_f_nome, LS.sug_fixa, "Ex.: ALUGUEL, LUZ, INTERNET"),
            "Ao escolher uma conta já cadastrada, o valor e o dia são preenchidos sozinhos.",
        ),
        rx.grid(
            _campo(
                "Valor mensal *",
                rx.input(
                    placeholder="0,00",
                    value=LS.f_valor,
                    on_change=LS.set_f_valor,
                    size="3",
                    width="100%",
                    custom_attrs={"inputMode": "decimal"},
                ),
            ),
            _campo(
                "Dia de vencimento *",
                rx.input(type="number", placeholder="1 a 31", value=LS.f_dia, on_change=LS.set_f_dia, size="3", width="100%"),
            ),
            _campo(
                "Forma de pagamento",
                rx.select(FORMAS, value=LS.f_forma, on_change=LS.set_f_forma, size="3", width="100%"),
            ),
            columns=rx.breakpoints(initial="1", sm="3"),
            spacing="3",
            width="100%",
        ),
        rx.checkbox("Já está pago neste mês", checked=LS.f_pago, on_change=LS.set_f_pago, size="2"),
        spacing="4",
        width="100%",
    )


def _card_formulario() -> rx.Component:
    return card_container(
        rx.segmented_control.root(
            rx.segmented_control.item("Outras despesas", value="outros"),
            rx.segmented_control.item("Conta fixa", value="fixa"),
            value=LS.modo,
            on_change=LS.set_modo,
            width="100%",
            size="3",
            margin_bottom="1.2em",
        ),
        rx.cond(LS.modo == "fixa", _form_fixa(), _form_outros()),
        rx.button(
            rx.icon("clipboard-check", size=18),
            "Revisar e salvar",
            on_click=LS.revisar,
            size="3",
            width="100%",
            margin_top="1.4em",
            style={"background": PRIMARY, "color": "white", "_hover": {"background": PRIMARY_HOVER}},
        ),
    )


def _linha_recente(r) -> rx.Component:
    return rx.hstack(
        rx.cond(
            r["pago"],
            rx.icon("circle-check", color=SUCCESS, size=20),
            rx.icon("clock", color=WARNING, size=20),
        ),
        rx.vstack(
            rx.text(r["gasto"], weight="bold", size="2"),
            rx.text(r["detalhe"], size="1", color=TEXT_MUTED),
            spacing="0",
            align="start",
            min_width="0",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(r["valor"], weight="bold", size="2"),
            rx.text(r["data"], size="1", color=TEXT_MUTED),
            rx.cond(
                r["pago"],
                rx.badge("Despesa paga", color_scheme="green", size="1"),
                rx.badge("A pagar", color_scheme="orange", size="1"),
            ),
            spacing="1",
            align="end",
        ),
        width="100%",
        align="center",
        padding="0.7em 0",
        border_bottom=f"1px solid {BORDER}",
    )


def _card_recentes() -> rx.Component:
    return card_container(
        rx.heading("Lançamentos recentes", size="4", margin_bottom="0.4em"),
        rx.cond(
            LS.recentes.length() == 0,
            rx.text("Nenhum lançamento ainda.", size="2", color=TEXT_MUTED),
            rx.vstack(rx.foreach(LS.recentes, _linha_recente), spacing="0", width="100%"),
        ),
    )


def _dialogo_confirmacao() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Confirme o lançamento"),
            rx.alert_dialog.description(
                "Confira os dados antes de salvar.", size="2", color=TEXT_MUTED,
            ),
            rx.vstack(
                rx.foreach(LS.resumo, lambda linha: rx.text(linha, size="2")),
                spacing="1",
                width="100%",
                padding="0.8em",
                margin_top="0.8em",
                border_radius="10px",
                bg="#F8FAFC",
                border=f"1px solid {BORDER}",
            ),
            rx.flex(
                rx.button("Voltar e corrigir", variant="soft", color_scheme="gray", on_click=LS.fechar_confirma),
                rx.button("Confirmar e salvar", color_scheme="green", on_click=LS.confirmar_salvar),
                spacing="3",
                justify="end",
                margin_top="1.2em",
            ),
            max_width="460px",
        ),
        open=LS.confirma_aberta,
    )


def lancamentos_page() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.heading("Lançamentos", size="6"),
            rx.text(
                "Preencha, revise o resumo e confirme. Tudo é salvo em letras maiúsculas.",
                size="2",
                color=TEXT_MUTED,
            ),
            _card_loja(),
            _card_formulario(),
            _card_recentes(),
            _dialogo_confirmacao(),
            spacing="4",
            width="100%",
            max_width="760px",
            margin="0 auto",
        ),
    )