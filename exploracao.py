import pandas as pd

arquivo = "INTERNACOES_DATA.csv"

try:
    print(f"Lendo o arquivo {arquivo}...\n")
    # Removendo o sep=';' para que o pandas use a vírgula corretamente
    df = pd.read_csv(arquivo, encoding='utf-8')

    print("--- INFORMAÇÕES DAS COLUNAS (Tipos e Nulos) ---")
    print(df.info())

    print("\n--- PRIMEIRAS 3 LINHAS ---")
    print(df.head(3))

except Exception as e:
    print(f"Erro ao ler o arquivo: {e}")