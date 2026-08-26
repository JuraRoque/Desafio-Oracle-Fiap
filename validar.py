import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv("ORACLE_USER")
PASSWORD = os.getenv("ORACLE_PASSWORD")
DSN = os.getenv("ORACLE_DSN")

LIB_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1\instantclient_23_26"
WALLET_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1"

try:
    oracledb.init_oracle_client(lib_dir=LIB_DIR)
    connection = oracledb.connect(
        user=USER, password=PASSWORD, dsn=DSN,
        config_dir=WALLET_DIR, wallet_location=WALLET_DIR
    )
    cursor = connection.cursor()

    # Conta quantos registros temos na tabela
    cursor.execute("SELECT COUNT(*) FROM internacoes")
    total = cursor.fetchone()[0]
    print(f">> Total de registros na tabela da nuvem: {total}")

    # Pega as 3 primeiras linhas para conferir
    cursor.execute("SELECT municipio, tipo_internacao, tempo_permanencia FROM internacoes WHERE ROWNUM <= 3")
    print("\n>> Amostra de dados vindos do Oracle Cloud:")
    for row in cursor.fetchall():
        print(f"   Município: {row[0]} | Tipo: {row[1]} | Permanência: {row[2]} dias")

    cursor.close()
    connection.close()
    print("\n[SUCESSO] Validação concluída com excelência!")

except Exception as e:
    print(f"[ERRO]: {e}")