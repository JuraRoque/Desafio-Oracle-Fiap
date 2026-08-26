from database import perguntar_ao_nexus_ai, obter_conexao


def validar_integracao():
    print("Iniciando validação técnica...")

    conn = obter_conexao()
    if conn:
        print("Status da Conexão: Estabelecida")
        conn.close()
    else:
        print("Status da Conexão: Falha")
        return

    print("Testando Oracle Select AI...")
    pergunta = "Qual o total de internações registradas?"

    try:
        resultado = perguntar_ao_nexus_ai(pergunta)
        print(f"Resposta da IA: {resultado}")
    except Exception as e:
        print(f"Erro no teste: {e}")


if __name__ == "__main__":
    validar_integracao()
