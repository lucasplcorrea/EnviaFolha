import pandas as pd
import os
import logging
import requests
from dotenv import load_dotenv
import time

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_holerites_to_api(excel_path, pdf_dir, api_url, auth_token, external_key, month_year_str):
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        logging.error(f"Erro: Planilha de colaboradores não encontrada em {excel_path}")
        return

    logging.info(f"Iniciando o envio de holerites para {len(df)} colaboradores.")

    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    def send_text_message(number, message_body, is_closed=False):
        message_data = {
            "body": message_body,
            "number": number,
            "externalKey": external_key,
            "isClosed": str(is_closed).lower()
        }
        try:
            response = requests.post(api_url, headers=headers, json=message_data)
            response.raise_for_status()
            logging.info(f"Mensagem para {number} enviada com sucesso! Resposta: {response.status_code} - {response.text}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logging.error(f"Erro 403 Forbidden ao enviar mensagem para {number}. Verifique o token de autorização ou permissões da API.")
            else:
                logging.error(f"Erro HTTP ao enviar mensagem para {number}: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição ao enviar mensagem para {number}: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao enviar mensagem para {number}: {e}")
        return False

    for index, row in df.iterrows():
        unique_id = str(row["ID_Unico"]).zfill(9)
        employee_name = row["Nome_Colaborador"]
        phone_number = str(row["Telefone"])

        if phone_number == "nan" or not phone_number.strip():
            logging.warning(f"Número de telefone inválido ou vazio para {employee_name} (ID: {unique_id}). Pulando envio.")
            continue

        pdf_filename = f"{unique_id}_holerite_{month_year_str}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        if not os.path.exists(pdf_path):
            logging.warning(f"Holerite não encontrado para {employee_name} (ID: {unique_id}) em {pdf_path}. Pulando...")
            continue

        # Mensagem de saudação
        greeting_message = f"Olá {employee_name}, segue seu holerite referente ao mês de {month_year_str.replace('_', ' ')}, a senha para abrir são os 4 primeiros dígitos do seu cpf."
        logging.info(f"Enviando mensagem de saudação para {employee_name}...")
        send_text_message(phone_number, greeting_message)
        time.sleep(15)

        logging.info(f"Enviando holerite para {employee_name} (ID: {unique_id}) no número {phone_number}...")

        try:
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

            files = {"media": (pdf_filename, pdf_content, "application/pdf")}
            data = {
                "number": phone_number,
                "externalKey": external_key,
                "isClosed": "false",
                "body": "Holerite anexo"
            }

            response = requests.post(api_url, headers=headers, files=files, data=data)
            response.raise_for_status()  # Levanta um erro para status codes 4xx/5xx

            logging.info(f"Holerite de {employee_name} enviado com sucesso! Resposta da API: {response.status_code} - {response.text}")
            time.sleep(15)

            # Mensagem de finalização
            conclusion_message = "Essa é uma mensagem automática, em caso de dúvidas contate o RH."
            logging.info(f"Enviando mensagem de finalização para {employee_name}...")
            send_text_message(phone_number, conclusion_message, is_closed=True)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logging.error(f"Erro 403 Forbidden ao enviar holerite de {employee_name} (ID: {unique_id}). Verifique o token de autorização ou permissões da API.")
            else:
                logging.error(f"Erro HTTP ao enviar holerite de {employee_name} (ID: {unique_id}) para a API: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição ao enviar holerite de {employee_name} (ID: {unique_id}) para a API: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao processar holerite de {employee_name} (ID: {unique_id}): {e}")
            
            if index < len(df) - 1:
                time.sleep(60)

    logging.info("Processamento concluído.")

if __name__ == "__main__":
    excel_file = "./Colaboradores.xlsx"
    holerites_directory = "./holerites_formatados_final/"
    api_url = os.getenv("API_URL")
    auth_token = os.getenv("AUTH_TOKEN")
    external_key = os.getenv("EXTERNAL_KEY")
    current_month_year = "junho_2025" 

    if not all([api_url, auth_token, external_key]):
        logging.error("Erro: Variáveis de ambiente API_URL, AUTH_TOKEN e EXTERNAL_KEY devem ser definidas.")
        exit(1)

    send_holerites_to_api(excel_file, holerites_directory, api_url, auth_token, external_key, current_month_year)