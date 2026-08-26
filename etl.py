import os
import oracledb
import pandas as pd
import re
from dotenv import load_dotenv

# 1. Carrega as variáveis de segurança do arquivo .env
load_dotenv()

USER = os.getenv("ORACLE_USER")
PASSWORD = os.getenv("ORACLE_PASSWORD")
DSN = os.getenv("ORACLE_DSN")

# 2. Caminhos do Instant Client e da Wallet
LIB_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1\instantclient_23_26"
WALLET_DIR = r"C:\Users\judie\PycharmProjects\PythonProject1"


def executar_carga_completa():
    try:
        oracledb.init_oracle_client(lib_dir=LIB_DIR)
        print(">> Conectando ao Oracle Cloud com segurança...")

        connection = oracledb.connect(
            user=USER,
            password=PASSWORD,
            dsn=DSN,
            config_dir=WALLET_DIR,
            wallet_location=WALLET_DIR
        )

        cursor = connection.cursor()
        print(">> Conexão estabelecida com sucesso!")

        # Mapeamento oficial do Nexus Health
        tabelas_para_subir = {
            "INTERNACOES_DATA": "INTERNACOES_DATA.csv",
            "LEITOS_MUNICIPIO": "LEITOS_MUNICIPIO.csv",
            "QTD_INTER_DIA": "QTD_INTER_DIA.csv",
            "QTD_INTERNACOES_TPERMANENCIA": "QTD_INTERNACOES_TPERMANENCIA.csv",
            "TAB_CID": "TAB_CID.csv",
            "TIPO_INTERNACAO_CID": "TIPO_INTERNACAO_CID.csv"
        }

        for nome_tabela, arquivo_csv in tabelas_para_subir.items():
            if not os.path.exists(arquivo_csv):
                print(f"⚠️ Aviso: O arquivo '{arquivo_csv}' não foi encontrado na pasta. Pulando...")
                continue

            print(f"\n>> Processando tabela: {nome_tabela} a partir de {arquivo_csv}...")

            # Remove a tabela antiga se existir
            try:
                cursor.execute(f"DROP TABLE {nome_tabela}")
                connection.commit()
            except:
                pass

            # Lê o CSV
            df = pd.read_csv(arquivo_csv)

            # === BLINDAGEM DE COLUNAS (REGEX) ===
            colunas_limpas = []
            for col in df.columns:
                # Remove qualquer coisa que não seja letra ou número
                nome_limpo = re.sub(r'[^A-Z0-9]', '_', str(col).upper().strip())
                # Remove underlines duplicados
                nome_limpo = re.sub(r'_+', '_', nome_limpo).strip('_')
                # Oracle não aceita colunas começando com números
                if not nome_limpo or nome_limpo[0].isdigit():
                    nome_limpo = "C_" + nome_limpo
                colunas_limpas.append(nome_limpo)

            df.columns = colunas_limpas

            # Cria a query CREATE TABLE (Forçando VARCHAR2(4000) para garantir a ingestão de dados sem falhas)
            colunas_sql = [f"{col} VARCHAR2(4000)" for col in df.columns]
            sql_create = f"CREATE TABLE {nome_tabela} ({', '.join(colunas_sql)})"

            cursor.execute(sql_create)
            connection.commit()
            print(f">> Tabela '{nome_tabela}' criada na nuvem com colunas tratadas.")

            # Trata valores vazios (NaN) do Pandas para o padrão Null do Oracle e converte tudo pra string
            df = df.where(pd.notnull(df), None)
            dados = [tuple(str(x) if x is not None else None for x in row) for row in df.to_numpy()]

            placeholders = ", ".join([f":{i + 1}" for i in range(len(df.columns))])
            sql_insert = f"INSERT INTO {nome_tabela} ({', '.join(df.columns)}) VALUES ({placeholders})"

            print(f">> Inserindo {len(dados)} registros em {nome_tabela}...")
            cursor.executemany(sql_insert, dados)
            connection.commit()
            print(f">> '{nome_tabela}' carregada com sucesso!")

        print("\n[SUCESSO ABSOLUTO] Todas as tabelas oficiais do projeto foram sincronizadas com o Oracle Cloud!")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"\n[ERRO NA CARGA]: {e}")


if __name__ == "__main__":
    executar_carga_completa()