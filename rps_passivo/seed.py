"""Popula o banco com os dados iniciais (lojas, contas fixas, distribuidoras,
tipos de despesa e os 3 usuários padrão).

Uso (após `reflex db init` e `reflex db migrate`):
    $ python -m rps_passivo.seed
"""
import reflex as rx
from sqlmodel import select

from .models import User, Store, FixedExpense, Distributor, ExpenseType
from .auth import hash_senha
from .utils.avatar import cor_por_nome
from .seed_data import LOJAS, CONTAS_FIXAS, DISTRIBUIDORAS, TIPOS_DESPESA


def seed():
    with rx.session() as session:
        if session.exec(select(User)).first():
            print("Banco já populado — nada a fazer.")
            return

        # --- usuários padrão ---
        admin = User(username="admin", password_hash=hash_senha("admin123"), role="admin", display_name="Administrador")
        operador = User(username="operador", password_hash=hash_senha("operador123"), role="operator", display_name="Operador")
        visualizador = User(username="visualizador", password_hash=hash_senha("visual123"), role="viewer", display_name="Visualizador")
        session.add_all([admin, operador, visualizador])
        session.commit()

        # --- lojas ---
        store_ids = {}
        for nome, limite_sem, limite_mes in LOJAS:
            loja = Store(
                name=nome,
                weekly_limit=limite_sem,
                monthly_limit=limite_mes,
                avatar_color=cor_por_nome(nome),
                created_by=admin.id,
            )
            session.add(loja)
            session.commit()
            session.refresh(loja)
            store_ids[nome] = loja.id

        # --- contas fixas por loja ---
        for nome_loja, contas in CONTAS_FIXAS.items():
            store_id = store_ids.get(nome_loja)
            if not store_id:
                continue
            for nome, valor, dia, forma in contas:
                session.add(
                    FixedExpense(
                        store_id=store_id, name=nome, amount=valor,
                        due_day=dia, payment_method=forma, created_by=admin.id,
                    )
                )
        session.commit()

        # --- distribuidoras ---
        for nome in DISTRIBUIDORAS:
            session.add(Distributor(name=nome, created_by=admin.id))
        session.commit()

        # --- tipos de despesa ---
        for nome, categoria in TIPOS_DESPESA:
            session.add(ExpenseType(name=nome, category=categoria, created_by=admin.id))
        session.commit()

        print("Seed concluído: 3 usuários, 7 lojas, contas fixas, distribuidoras e tipos de despesa criados.")


if __name__ == "__main__":
    seed()
