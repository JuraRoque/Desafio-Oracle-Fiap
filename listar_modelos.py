import oci
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    "user": os.getenv("OCI_USER"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY"),
    "region": os.getenv("OCI_REGION"),
    "key_file": os.getenv("OCI_KEY_FILE")
}

def listar_modelos():
    client = oci.generative_ai.GenerativeAiClient(config)
    try:
        # Lista todos os modelos disponíveis na sua conta
        response = client.list_models(compartment_id=os.getenv("OCI_TENANCY"))
        print("--- Modelos Disponíveis em São Paulo ---")
        for model in response.data.items:
            # Mostra o ID e o Nome de exibição
            print(f"ID: {model.id} | Nome: {model.display_name}")
    except Exception as e:
        print(f"Erro ao listar modelos: {e}")

if __name__ == "__main__":
    listar_modelos()
