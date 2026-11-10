"""Copia todas as tabelas do banco para arquivos CSV em backups/AAAA-MM-DD_HHMM."""
import csv
import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

pasta = os.path.join("backups", datetime.now().strftime("%Y-%m-%d_%H%M"))
os.makedirs(pasta, exist_ok=True)

tabelas = inspect(engine).get_table_names()
with engine.connect() as conn:
    for tabela in tabelas:
        resultado = conn.execute(text(f'SELECT * FROM "{tabela}"'))
        colunas = list(resultado.keys())
        caminho = os.path.join(pasta, f"{tabela}.csv")
        total = 0
        with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(colunas)
            for linha in resultado:
                escritor.writerow(linha)
                total += 1
        print(f"{tabela}: {total} linhas")

print(f"\nBackup salvo em: {pasta}")