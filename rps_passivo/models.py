"""Modelos de dados (SQLModel) do sistema de Passivo - Drogarias Cumani."""
from datetime import datetime, date
from typing import Optional

import reflex as rx
import sqlalchemy
from sqlalchemy import UniqueConstraint
from sqlmodel import Field


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------
class User(rx.Model, table=True):
    __tablename__ = "users"

    username: str = Field(sa_column=sqlalchemy.Column(sqlalchemy.String, unique=True, index=True))
    password_hash: str
    role: str = Field(default="viewer")  # admin | operator | viewer
    display_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


# ---------------------------------------------------------------------------
# Lojas
# ---------------------------------------------------------------------------
class Store(rx.Model, table=True):
    __tablename__ = "stores"

    name: str = Field(index=True)
    weekly_limit: float = 0.0
    monthly_limit: float = 0.0
    cash_limit: float = 0.0  # Limite por Caixa (Mês de Pagamento)
    logo_b64: Optional[str] = None
    logo_filename: Optional[str] = None
    avatar_color: str = "#E31E24"
    created_by: Optional[int] = None
    created_by_operator: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


# ---------------------------------------------------------------------------
# Contas fixas (por loja). Valem todo mês; o pagamento de cada mês fica
# registrado em FixedExpensePayment.
# ---------------------------------------------------------------------------
class FixedExpense(rx.Model, table=True):
    __tablename__ = "fixed_expenses"

    store_id: int = Field(foreign_key="stores.id")
    name: str
    amount: float = 0.0
    due_day: str = ""  # texto: "DIA 10", "TODA SEGUNDA", "5° DIA UTIL"...
    payment_method: str = "PIX"
    notes: str = ""
    is_paid: bool = False          # legado: usado pelas telas antigas
    paid_at: Optional[datetime] = None
    paid_by: Optional[int] = None
    created_by: Optional[int] = None
    created_by_operator: bool = False
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Lixeira
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Pagamento mensal de conta fixa: um registro por conta, por mês pago
# ---------------------------------------------------------------------------
class FixedExpensePayment(rx.Model, table=True):
    __tablename__ = "fixed_expense_payments"
    __table_args__ = (
        UniqueConstraint("fixed_expense_id", "competencia", name="uq_pagamento_fixa_mes"),
    )

    fixed_expense_id: int = Field(foreign_key="fixed_expenses.id", index=True)
    store_id: int = Field(foreign_key="stores.id", index=True)
    competencia: date = Field(index=True)  # primeiro dia do mês pago
    amount: float = 0.0                    # valor pago naquele mês
    paid_at: datetime = Field(default_factory=datetime.utcnow)
    paid_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Distribuidoras / nomes de gasto
# ---------------------------------------------------------------------------
class Distributor(rx.Model, table=True):
    __tablename__ = "distributors"

    name: str = Field(index=True)
    created_by: Optional[int] = None
    created_by_operator: bool = False
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Tipos de despesa
# ---------------------------------------------------------------------------
class ExpenseType(rx.Model, table=True):
    __tablename__ = "expense_types"

    name: str = Field(index=True)
    category: str = "Variável"  # Fixa | Variável
    created_by: Optional[int] = None
    created_by_operator: bool = False
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Lançamentos de "Outras despesas" (compras, boletos, pagamentos diversos)
# ---------------------------------------------------------------------------
class BoletoEntry(rx.Model, table=True):
    __tablename__ = "boleto_entries"

    store_id: int = Field(foreign_key="stores.id")
    distributor_id: int = Field(foreign_key="distributors.id")
    boleto_date: date  # VENCIMENTO: define em qual mês o valor conta no limite
    amount: float = 0.0
    payment_method: str = "PIX"
    expense_type_id: Optional[int] = Field(default=None, foreign_key="expense_types.id")
    notes: str = ""
    is_paid: bool = False
    paid_at: Optional[datetime] = None
    paid_by: Optional[int] = None
    operator_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    week_period: str = ""
    # Parcelamento e data de lançamento
    data_lancamento: Optional[date] = None
    parcela_num: Optional[int] = None
    total_parcelas: Optional[int] = None
    grupo_parcelas: Optional[str] = None
    # Lixeira
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Relatórios cacheados (não usados na versão atual)
# ---------------------------------------------------------------------------
class WeeklyReport(rx.Model, table=True):
    __tablename__ = "weekly_reports"

    store_id: int = Field(foreign_key="stores.id")
    week_start: date
    week_end: date
    boleto_total: float = 0.0
    fixed_total: float = 0.0
    combined_total: float = 0.0
    limit_status: str = "dentro"


class MonthlyReport(rx.Model, table=True):
    __tablename__ = "monthly_reports"

    store_id: int = Field(foreign_key="stores.id")
    year: int
    month: int
    boleto_total: float = 0.0
    fixed_total: float = 0.0
    combined_total: float = 0.0
    limit_status: str = "dentro"


# ---------------------------------------------------------------------------
# Log de auditoria
# ---------------------------------------------------------------------------
class AuditLog(rx.Model, table=True):
    __tablename__ = "audit_log"

    user_id: Optional[int] = None
    username: str = ""
    action: str = ""  # create | update | delete | pay | unpay | restore
    entity_type: str = ""
    entity_id: Optional[int] = None
    description: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)