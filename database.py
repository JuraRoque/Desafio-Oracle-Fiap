import os
import oracledb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv("ORACLE_USER")
PASSWORD = os.getenv("ORACLE_PASSWORD")
DSN = os.getenv("ORACLE_DSN")

LIB_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1\instantclient_23_26"
WALLET_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1"

# Inicializa o Oracle Client uma única vez ao importar o módulo
try:
    oracledb.init_oracle_client(lib_dir=LIB_DIR)
except Exception:
    pass

def obter_conexao():
    """Retorna uma conexão ativa e segura com o Oracle Cloud."""
    connection = oracledb.connect(
        user=USER,
        password=PASSWORD,
        dsn=DSN,
        config_dir=WALLET_DIR,
        wallet_location=WALLET_DIR
    )
    return connection

def carregar_dados_streamlit():
    """Busca os dados da tabela de internações e retorna um DataFrame limpo."""
    conn = obter_conexao()
    query = "SELECT data_reg, municipio, nome_estabelecimento, tipo_internacao, tempo_permanencia, cid FROM internacoes"
    df = pd.read_sql(query, con=conn)
    conn.close()
    return df