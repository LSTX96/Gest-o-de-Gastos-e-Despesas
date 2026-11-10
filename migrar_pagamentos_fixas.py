"""Registra, na tabela de pagamentos mensais, as contas fixas marcadas como pagas.

Regra aprovada: contam como pagas apenas no mês atual.
Pode ser rodado mais de uma vez: não duplica registros.
"""
import os
from datetime import date, datetime

from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select

from rps_passivo.models import FixedExpense, FixedExpensePayment

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

competencia = date.today().replace(day=1)
criados = 0
ja_existiam = 0

with Session(engine) as session:
    pagas = session.exec(
        select(FixedExpense).where(
            FixedExpense.is_paid == True,  # noqa: E712
            FixedExpense.active == True,  # noqa: E712
        )
    ).all()

    for conta in pagas:
        existe = session.exec(
            select(FixedExpensePayment).where(
                FixedExpensePayment.fixed_expense_id == conta.id,
                FixedExpensePayment.competencia == competencia,
            )
        ).first()
        if existe:
            ja_existiam += 1
            continue
        session.add(
            FixedExpensePayment(
                fixed_expense_id=conta.id,
                store_id=conta.store_id,
                competencia=competencia,
                amount=conta.amount,
                paid_at=conta.paid_at or datetime.utcnow(),
                paid_by=conta.paid_by,
            )
        )
        criados += 1

    session.commit()

print(f"Mês de referência: {competencia.strftime('%m/%Y')}")
print(f"Contas fixas pagas encontradas: {criados + ja_existiam}")
print(f"Pagamentos registrados agora: {criados}")
print(f"Já estavam registrados: {ja_existiam}")