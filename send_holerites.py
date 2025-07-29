import pandas as pd
import os
import logging
import requests
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_single_holerite(pdf_path, api_url, auth_token, external_key, target_phone_number):
    logging.info(f"Iniciando o envio de um único holerite para {target_phone_number}.")

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    pdf_filename = os.path.basename(pdf_path)

    if not os.path.exists(pdf_path):
        logging.error(f"Erro: Holerite não encontrado em {pdf_path}. Abortando envio.")
        return

    logging.info(f"Enviando holerite {pdf_filename} para o número {target_phone_number}...")

    try:
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

        files = {"media": (pdf_filename, pdf_content, "application/pdf")}
        data = {
            "number": target_phone_number,
            "externalKey": external_key,
            "isClosed": "false",
            "body": "Mensagem"
        }

        response = requests.post(api_url, headers=headers, files=files, data=data)
        response.raise_for_status()  # Levanta um erro para status codes 4xx/5xx

        logging.info(f"Holerite {pdf_filename} enviado com sucesso! Resposta da API: {response.status_code} - {response.text}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.error(f"Erro 403 Forbidden ao enviar holerite {pdf_filename}. Verifique o token de autorização ou permissões da API.")
        else:
            logging.error(f"Erro HTTP ao enviar holerite {pdf_filename} para a API: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de requisição ao enviar holerite {pdf_filename} para a API: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado ao processar holerite {pdf_filename}: {e}")

    logging.info("Processamento concluído.")

if __name__ == "__main__":
    # Configurações para o teste de envio único
    test_pdf_path = "./holerites_formatados_final/006000130_holerite_junho_2025.pdf" # Escolha um holerite existente para teste
    target_phone_number = "554700000000" # Seu número de telefone

    api_url = os.getenv("API_URL")
    auth_token = os.getenv("AUTH_TOKEN")
    external_key = os.getenv("EXTERNAL_KEY")

    if not all([api_url, auth_token, external_key]):
        logging.error("Erro: Variáveis de ambiente API_URL, AUTH_TOKEN e EXTERNAL_KEY devem ser definidas.")
        exit(1)

    send_single_holerite(test_pdf_path, api_url, auth_token, external_key, target_phone_number)