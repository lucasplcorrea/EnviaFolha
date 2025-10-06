import pandas as pd
import os
import logging
import requests
import time
import random
import base64
from datetime import datetime
import mimetypes
from dotenv import load_dotenv
from status_manager import StatusManager
import shutil

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
        self.status_manager = StatusManager()
        self.sent_files_dir = "enviados"
        
        # Criar diretório de arquivos enviados se não existir
        os.makedirs(self.sent_files_dir, exist_ok=True)
        
    def move_sent_file(self, file_path, filename):
        """Move arquivo enviado com sucesso para a pasta 'enviados'"""
        try:
            destination_path = os.path.join(self.sent_files_dir, filename)
            shutil.move(file_path, destination_path)
            logging.info(f"Arquivo {filename} movido para pasta 'enviados'")
            return True
        except Exception as e:
            logging.error(f"Erro ao mover arquivo {filename}: {e}")
            return False
        
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
            "text": text,
            "delay": delay
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
            "mediatype": media_type,
            "mimetype": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
            "caption": caption or "",
            "media": base64_content,
            "fileName": filename or os.path.basename(file_path),
            "delay": delay
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
            # A partir da v2.2.2, o status pode vir em 'state' ou 'status'
            status = result.get('instance', {}).get('state', result.get('instance', {}).get('status', 'unknown'))
            logging.info(f"Status da instância {self.instance_name}: {status}")
            
            if status != 'open' and status != 'connected': # Adicionado 'connected' para v2.2.2+
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

        # Atualiza status para "processando"
        self.status_manager.update_current_step(f"Processando {employee_name}", employee_name)
        self.status_manager.update_employee_status(unique_id, employee_name, phone_number, "processing", "Iniciando processamento")

        if phone_number == "nan" or not phone_number.strip():
            logging.warning(f"Número de telefone inválido para {employee_name} (ID: {unique_id}). Pulando...")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Telefone inválido"})
            self.status_manager.update_employee_status(unique_id, employee_name, phone_number, "failed", "Telefone inválido")
            return False

        # Formatar número de telefone
        formatted_phone = self.format_phone_number(phone_number)
        
        pdf_filename = f"{unique_id}_holerite_{month_year_str}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        if not os.path.exists(pdf_path):
            logging.warning(f"Holerite não encontrado para {employee_name} (ID: {unique_id}) em {pdf_path}. Pulando...")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Holerite não encontrado"})
            self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "failed", "Holerite não encontrado")
            return False

        logging.info(f"Iniciando envio para {employee_name} (ID: {unique_id}) no número {formatted_phone}...")

        # Mensagem de saudação combinada com informações do holerite
        greeting_message = f"Olá {employee_name}, segue seu holerite referente ao mês de {month_year_str.replace('_', ' ')}, a senha para abrir são os 4 primeiros dígitos do seu CPF. Esta é uma mensagem automática, em caso de dúvidas contate o RH."
        
        self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "processing", "Enviando mensagem de saudação")
        
        if not self.send_text_message(formatted_phone, greeting_message):
            logging.error(f"Falha ao enviar mensagem de saudação para {employee_name}")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Falha na mensagem de saudação"})
            self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "failed", "Falha na mensagem de saudação")
            return False

        # Delay entre mensagem e arquivo (reduzido)
        self.add_random_delay(20, 8)

        # Envio do holerite com caption informativo
        self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "processing", "Enviando holerite")
        
        holerite_caption = "📄 Seu holerite está anexo. Guarde este documento em local seguro."
        
        if not self.send_media_message(formatted_phone, pdf_path, pdf_filename, holerite_caption):
            logging.error(f"Falha ao enviar holerite para {employee_name}")
            self.failed_employees.append({"nome": employee_name, "id": unique_id, "motivo": "Falha no envio do holerite"})
            self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "failed", "Falha no envio do holerite")
            return False

        self.success_count += 1
        self.sent_employees.append({"nome": employee_name, "id": unique_id, "telefone": formatted_phone})
        self.status_manager.update_employee_status(unique_id, employee_name, formatted_phone, "success", "Holerite enviado com sucesso")
        
        # Mover arquivo para pasta 'enviados'
        if self.move_sent_file(pdf_path, pdf_filename):
            logging.info(f"✅ Processo completo para {employee_name}! Arquivo movido para 'enviados'.")
        else:
            logging.warning(f"✅ Processo completo para {employee_name}! Mas houve erro ao mover o arquivo.")
        
        return True

    def send_holerites_to_api(self, excel_path, pdf_dir, month_year_str, start_from_index=0):
        """Função principal para envio dos holerites"""
        
        # Verificar se já há uma execução em andamento
        if self.status_manager.is_running():
            logging.error("Já existe uma execução em andamento. Aguarde a conclusão ou resete o status.")
            return
        
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
        execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Iniciar execução
        if not self.status_manager.start_execution(total_employees, execution_id):
            logging.error("Não foi possível iniciar a execução. Verifique se não há outra execução em andamento.")
            return
        
        logging.info(f"Iniciando o envio de holerites para {total_employees} colaboradores usando Evolution API v2.2.2.")
        logging.info(f"Instância: {self.instance_name}")
        logging.info(f"Começando do índice {start_from_index}")
        logging.info(f"ID da execução: {execution_id}")

        try:
            for index, row in df.iterrows():
                if index < start_from_index:
                    continue
                    
                logging.info(f"\n--- Processando funcionário {index + 1}/{total_employees} ---")
                
                success = self.process_employee(row, pdf_dir, month_year_str)
                
                # Delay menor entre funcionários devido à otimização das mensagens
                if index < total_employees - 1:  # Não adiciona delay após o último
                    if success:
                        self.add_random_delay(45, 15)  # 30-60 segundos entre sucessos (reduzido)
                    else:
                        self.add_random_delay(20, 8)   # 12-28 segundos entre falhas (reduzido)

        except Exception as e:
            logging.error(f"Erro durante a execução: {e}")
        finally:
            # Finalizar execução
            self.status_manager.end_execution()
            self.generate_report()

    def generate_report(self):
        """Gera relatório final do envio"""
        logging.info("\n" + "="*50)
        logging.info("RELATÓRIO FINAL DE ENVIO - Evolution API v2.2.2")
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
        
        # Gerar arquivo de relatório para envio via WhatsApp
        self.generate_whatsapp_report()
    
    def generate_whatsapp_report(self):
        """Gera relatório em arquivo e envia via WhatsApp"""
        try:
            # Obter número do administrador das variáveis de ambiente
            admin_phone = os.getenv("ADMIN_WHATSAPP_NUMBER")
            if not admin_phone:
                logging.warning("Número do administrador não configurado (ADMIN_WHATSAPP_NUMBER). Pulando envio de relatório.")
                return
            
            # Gerar nome do arquivo de relatório
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"relatorio_envio_holerites_{timestamp}.txt"
            
            # Criar conteúdo do relatório
            report_content = []
            report_content.append("📊 RELATÓRIO DE ENVIO DE HOLERITES")
            report_content.append("=" * 40)
            report_content.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            report_content.append(f"Instância: {self.instance_name}")
            report_content.append("")
            report_content.append("📈 RESUMO:")
            report_content.append(f"✅ Enviados com sucesso: {self.success_count}")
            report_content.append(f"❌ Falhas: {len(self.failed_employees)}")
            report_content.append(f"📊 Total processado: {self.success_count + len(self.failed_employees)}")
            report_content.append("")
            
            if self.sent_employees:
                report_content.append("✅ FUNCIONÁRIOS COM ENVIO REALIZADO:")
                for emp in self.sent_employees:
                    report_content.append(f"  • {emp['nome']} (ID: {emp['id']}) - {emp['telefone']}")
                report_content.append("")
            
            if self.failed_employees:
                report_content.append("❌ FUNCIONÁRIOS COM FALHA:")
                for emp in self.failed_employees:
                    report_content.append(f"  • {emp['nome']} (ID: {emp['id']}) - {emp['motivo']}")
                report_content.append("")
            
            report_content.append("=" * 40)
            report_content.append("Relatório gerado automaticamente pelo sistema")
            
            # Salvar arquivo de relatório
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_content))
            
            # Formatar número do administrador
            formatted_admin_phone = self.format_phone_number(admin_phone)
            
            # Enviar mensagem de texto com resumo
            summary_message = f"""📊 *Relatório de Envio de Holerites*
            
✅ Sucessos: {self.success_count}
❌ Falhas: {len(self.failed_employees)}
📊 Total: {self.success_count + len(self.failed_employees)}

Relatório detalhado em anexo."""
            
            if self.send_text_message(formatted_admin_phone, summary_message):
                logging.info("Mensagem de resumo enviada para o administrador")
                
                # Aguardar um pouco antes de enviar o arquivo
                time.sleep(5)
                
                # Enviar arquivo de relatório
                if self.send_media_message(formatted_admin_phone, report_filename, report_filename, "Relatório detalhado de envio"):
                    logging.info(f"Relatório {report_filename} enviado para o administrador via WhatsApp")
                else:
                    logging.error("Falha ao enviar arquivo de relatório para o administrador")
            else:
                logging.error("Falha ao enviar mensagem de resumo para o administrador")
                
        except Exception as e:
            logging.error(f"Erro ao gerar/enviar relatório via WhatsApp: {e}")

def main():
    # Configurações
    excel_file = "./Colaboradores.xlsx"
    holerites_directory = "./holerites_formatados_final/"
    
    # Variáveis de ambiente para Evolution API
    server_url = os.getenv("EVOLUTION_SERVER_URL")        # URL do servidor Evolution API
    api_key = os.getenv("EVOLUTION_API_KEY")              # Chave de API
    instance_name = os.getenv("EVOLUTION_INSTANCE_NAME")  # Nome da instância
    current_month_year = "setembro_2025"  # Altere conforme necessário
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