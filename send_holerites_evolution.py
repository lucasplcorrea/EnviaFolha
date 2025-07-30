import pandas as pd
import os
import logging
import requests
import time
import random
import base64
from datetime import datetime
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f'envio_holerites_evolution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class HoleritesSenderEvolution:
    def __init__(self, server_url, api_key, instance_name):
        """
        Inicializa o cliente Evolution API
        
        Args:
            server_url: URL do servidor Evolution API (ex: https://api.evolution.com)
            api_key: Chave de API para autenticação
            instance_name: Nome da instância do WhatsApp
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.instance_name = instance_name
        self.headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        self.success_count = 0
        self.failed_employees = []
        self.sent_employees = []
        
    def add_random_delay(self, base_delay=15, variation=5):
        """Adiciona delay aleatório para parecer mais humano"""
        delay = base_delay + random.uniform(-variation, variation)
        logging.info(f"Aguardando {delay:.1f} segundos...")
        time.sleep(delay)
    
    def format_phone_number(self, phone_number):
        """
        Formata o número de telefone para o padrão internacional
        Remove caracteres especiais e adiciona código do país se necessário
        """
        # Remove todos os caracteres não numéricos
        clean_number = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Se não começar com código do país, assume Brasil (55)
        if not clean_number.startswith('55') and len(clean_number) >= 10:
            clean_number = '55' + clean_number
        
        # Adiciona o 9 no celular se necessário (padrão brasileiro)
        if len(clean_number) == 12 and clean_number[4] != '9':
            clean_number = clean_number[:4] + '9' + clean_number[4:]
        
        return clean_number
    
    def send_text_message(self, number, text, delay=0, retry_count=3):
        """Envia mensagem de texto usando Evolution API"""
        url = f"{self.server_url}/message/sendText/{self.instance_name}"
        
        payload = {
            "number": number,
            "textMessage": {
                "text": text
            },
            "options": {
                "delay": delay,
                "presence": "composing"
            }
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                logging.info(f"Mensagem enviada com sucesso para {number}. ID: {result.get('key', {}).get('id', 'N/A')}")
                return True
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logging.error(f"Erro 401 Unauthorized - Verifique a API key")
                    return False
                elif e.response.status_code == 404:
                    logging.error(f"Erro 404 - Instância {self.instance_name} não encontrada")
                    return False
                elif e.response.status_code == 429:
                    logging.warning(f"Rate limit atingido. Aguardando 60 segundos...")
                    time.sleep(60)
                    continue
                else:
                    logging.error(f"Erro HTTP {e.response.status_code} ao enviar mensagem para {number}: {e}")
                    
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout na tentativa {attempt + 1} para {number}")
                if attempt < retry_count - 1:
                    time.sleep(10)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro de requisição ao enviar mensagem para {number}: {e}")
                
            except Exception as e:
                logging.error(f"Erro inesperado ao enviar mensagem para {number}: {e}")
            
            if attempt < retry_count - 1:
                logging.info(f"Tentativa {attempt + 1} falhou. Tentando novamente em 30 segundos...")
                time.sleep(30)
        
        return False
    
    def file_to_base64(self, file_path):
        """Converte arquivo para base64"""
        try:
            with open(file_path, "rb") as file:
                encoded_string = base64.b64encode(file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            logging.error(f"Erro ao converter arquivo para base64: {e}")
            return None
    
    def send_media_message(self, number, file_path, filename=None, caption=None, delay=0, retry_count=3):
        """Envia arquivo de mídia usando Evolution API"""
        url = f"{self.server_url}/message/sendMedia/{self.instance_name}"
        
        # Converte arquivo para base64
        base64_content = self.file_to_base64(file_path)
        if not base64_content:
            return False
        
        # Determina o tipo de mídia baseado na extensão
        file_extension = os.path.splitext(file_path)[1].lower()
        media_type_map = {
            '.pdf': 'document',
            '.doc': 'document',
            '.docx': 'document',
            '.xls': 'document',
            '.xlsx': 'document',
            '.txt': 'document',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.mp4': 'video',
            '.avi': 'video',
            '.mov': 'video',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.ogg': 'audio'
        }
        
        media_type = media_type_map.get(file_extension, 'document')
        
        payload = {
            "number": number,
            "mediaMessage": {
                "mediaType": media_type,
                "fileName": filename or os.path.basename(file_path),
                "caption": caption or "",
                "media": base64_content
            },
            "options": {
                "delay": delay,
                "presence": "composing"
            }
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.post(url, headers=self.headers, json=payload, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                logging.info(f"Mídia enviada com sucesso para {number}. ID: {result.get('key', {}).get('id', 'N/A')}")
                return True
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logging.error(f"Erro 401 Unauthorized - Verifique a API key")
                    return False
                elif e.response.status_code == 404:
                    logging.error(f"Erro 404 - Instância {self.instance_name} não encontrada")
                    return False
                elif e.response.status_code == 413:
                    logging.error(f"Arquivo muito grande para {number}. Pulando...")
                    return False
                elif e.response.status_code == 429:
                    logging.warning(f"Rate limit atingido. Aguardando 120 segundos...")
                    time.sleep(120)
                    continue
                else:
                    logging.error(f"Erro HTTP {e.response.status_code} ao enviar mídia para {number}: {e}")
                    
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout na tentativa {attempt + 1} para envio de mídia para {number}")
                if attempt < retry_count - 1:
                    time.sleep(20)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro de requisição ao enviar mídia para {number}: {e}")
                
            except Exception as e:
                logging.error(f"Erro inesperado ao enviar mídia para {number}: {e}")
            
            if attempt < retry_count - 1:
                logging.info(f"Tentativa {attempt + 1} falhou. Tentando novamente em 60 segundos...")
                time.sleep(60)
        
        return False
    
    def check_instance_status(self):
        """Verifica o status da instância"""
        url = f"{self.server_url}/instance/connectionState/{self.instance_name}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            status = result.get('instance', {}).get('state', 'unknown')
            logging.info(f"Status da instância {self.instance_name}: {status}")
            
            if status != 'open':
                logging.warning(f"Instância não está conectada. Status: {status}")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Erro ao verificar status da instância: {e}")
            return False
    
    def process_employee(self, row, pdf_dir, month_year_str):
        """Processa um funcionário individual"""
        unique_id = str(row["ID_Unico"]).zfill(9)
        employee_name = row["Nome_Colaborador"]
        phone_number = str(row["Telefone"])

        if phone_number == "nan" or not phone_number.strip():
            logging.warning(f"Número de telefone inválido para {employee_name} (ID: {unique_id}). Pulando...")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Telefone inválido"})
            return False

        # Formatar número de telefone
        formatted_phone = self.format_phone_number(phone_number)
        
        pdf_filename = f"{unique_id}_holerite_{month_year_str}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        if not os.path.exists(pdf_path):
            logging.warning(f"Holerite não encontrado para {employee_name} (ID: {unique_id}) em {pdf_path}. Pulando...")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Holerite não encontrado"})
            return False

        logging.info(f"Iniciando envio para {employee_name} (ID: {unique_id}) no número {formatted_phone}...")

        # Mensagem de saudação
        greeting_message = f"Olá {employee_name}, segue seu holerite referente ao mês de {month_year_str.replace('_', ' ')}, a senha para abrir são os 4 primeiros dígitos do seu CPF."
        
        if not self.send_text_message(formatted_phone, greeting_message):
            logging.error(f"Falha ao enviar mensagem de saudação para {employee_name}")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Falha na mensagem de saudação"})
            return False

        # Delay entre mensagem de saudação e arquivo
        self.add_random_delay(25, 10)

        # Envio do holerite
        if not self.send_media_message(formatted_phone, pdf_path, pdf_filename, "Holerite anexo"):
            logging.error(f"Falha ao enviar holerite para {employee_name}")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Falha no envio do holerite"})
            return False

        # Delay entre arquivo e mensagem de finalização
        self.add_random_delay(25, 10)

        # Mensagem de finalização
        conclusion_message = "Essa é uma mensagem automática, em caso de dúvidas contate o RH."
        
        if not self.send_text_message(formatted_phone, conclusion_message):
            logging.warning(f"Falha ao enviar mensagem de finalização para {employee_name} (holerite já foi enviado)")
            # Não considera como falha total, pois o holerite foi enviado

        self.success_count += 1
        self.sent_employees.append({"nome": employee_name, "id": unique_id, "telefone": formatted_phone})
        logging.info(f"✅ Processo completo para {employee_name}!")
        
        return True

    def send_holerites_to_api(self, excel_path, pdf_dir, month_year_str, start_from_index=0):
        """Função principal para envio dos holerites"""
        # Verificar status da instância antes de começar
        if not self.check_instance_status():
            logging.error("Instância não está conectada. Abortando envio.")
            return
        
        try:
            df = pd.read_excel(excel_path)
        except FileNotFoundError:
            logging.error(f"Erro: Planilha de colaboradores não encontrada em {excel_path}")
            return

        total_employees = len(df)
        logging.info(f"Iniciando o envio de holerites para {total_employees} colaboradores usando Evolution API v1.8.2.")
        logging.info(f"Instância: {self.instance_name}")
        logging.info(f"Começando do índice {start_from_index}")

        for index, row in df.iterrows():
            if index < start_from_index:
                continue
                
            logging.info(f"\n--- Processando funcionário {index + 1}/{total_employees} ---")
            
            success = self.process_employee(row, pdf_dir, month_year_str)
            
            # Delay maior entre funcionários para evitar rate limits
            if index < total_employees - 1:  # Não adiciona delay após o último
                if success:
                    self.add_random_delay(60, 20)  # 40-80 segundos entre sucessos
                else:
                    self.add_random_delay(30, 10)  # 20-40 segundos entre falhas

        self.generate_report()

    def generate_report(self):
        """Gera relatório final do envio"""
        logging.info("\n" + "="*50)
        logging.info("RELATÓRIO FINAL DE ENVIO - Evolution API v1.8.2")
        logging.info("="*50)
        logging.info(f"✅ Enviados com sucesso: {self.success_count}")
        logging.info(f"❌ Falhas: {len(self.failed_employees)}")
        logging.info(f"📊 Total processado: {self.success_count + len(self.failed_employees)}")
        
        if self.sent_employees:
            logging.info("\n📋 FUNCIONÁRIOS COM ENVIO REALIZADO:")
            for emp in self.sent_employees:
                logging.info(f"  - {emp['nome']} (ID: {emp['id']}) - {emp['telefone']}")
        
        if self.failed_employees:
            logging.info("\n⚠️  FUNCIONÁRIOS COM FALHA:")
            for emp in self.failed_employees:
                logging.info(f"  - {emp['nome']} (ID: {emp['id']}) - Motivo: {emp['motivo']}")
        
        logging.info("="*50)

def main():
    # Configurações
    excel_file = "./Colaboradores.xlsx"
    holerites_directory = "./holerites_formatados_final/"
    
    # Variáveis de ambiente para Evolution API
    server_url = os.getenv("EVOLUTION_SERVER_URL")        # URL do servidor Evolution API
    api_key = os.getenv("EVOLUTION_API_KEY")              # Chave de API
    instance_name = os.getenv("EVOLUTION_INSTANCE_NAME")  # Nome da instância
    current_month_year = "junho_2025"  # Altere conforme necessário
    start_from_index = int(os.getenv("START_FROM_INDEX", "0"))  # Para retomar de onde parou

    # Validação das variáveis de ambiente
    if not all([server_url, api_key, instance_name]):
        logging.error("Erro: Variáveis de ambiente EVOLUTION_SERVER_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE_NAME devem ser definidas.")
        logging.info("Configure essas variáveis no arquivo .env:")
        logging.info("EVOLUTION_SERVER_URL=https://sua-api.evolution.com")
        logging.info("EVOLUTION_API_KEY=sua_chave_de_api")
        logging.info("EVOLUTION_INSTANCE_NAME=nome_da_sua_instancia")
        return

    try:
        # Criar instância do sender
        sender = HoleritesSenderEvolution(server_url, api_key, instance_name)
        
        # Executar envio
        sender.send_holerites_to_api(excel_file, holerites_directory, current_month_year, start_from_index)
        
    except Exception as e:
        logging.error(f"Erro fatal durante a execução: {e}")

if __name__ == "__main__":
    main()