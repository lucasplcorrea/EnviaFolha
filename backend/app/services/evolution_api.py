import requests
import base64
import mimetypes
import os
import time
import random
import logging
from typing import Optional, Dict, Any
from ..core.config import settings
from .phone_validator import PhoneValidator

logger = logging.getLogger(__name__)

class EvolutionAPIService:
    """Serviço para comunicação com a Evolution API"""
    
    def __init__(self):
        self.server_url = settings.EVOLUTION_SERVER_URL.rstrip('/') if settings.EVOLUTION_SERVER_URL else None
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        } if self.api_key else None
        
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.warning("Configurações da Evolution API incompletas")
    
    def _add_random_delay(self, base_delay: int = 30, variation: int = 10):
        """Adiciona delay aleatório entre envios"""
        delay = base_delay + random.uniform(-variation, variation)
        logger.info(f"Aguardando {delay:.1f} segundos...")
        time.sleep(delay)
    
    def _file_to_base64(self, file_path: str) -> Optional[str]:
        """Converte arquivo para base64"""
        try:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Erro ao converter arquivo para base64: {e}")
            return None
    
    async def check_instance_status(self) -> bool:
        """Verifica se a instância está conectada"""
        if not self.headers:
            logger.warning("Headers da Evolution API não configurados")
            return False
            
        try:
            url = f"{self.server_url}/instance/connectionState/{self.instance_name}"
            logger.info(f"Verificando status da instância: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Resposta da API: {result}")
            
            status = result.get('instance', {}).get('state', 'unknown')
            logger.info(f"Status da instância: {status}")
            
            is_connected = status in ['open', 'connected']
            logger.info(f"Instância conectada: {is_connected}")
            
            return is_connected
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da instância: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_presence(self, phone: str, presence_type: str = "composing", delay: int = 5000) -> Dict[str, Any]:
        """
        Envia presença (digitando/gravando) para simular comportamento humano
        
        Args:
            phone: Número do telefone no formato internacional
            presence_type: Tipo de presença - "composing" (digitando), "recording" (gravando áudio), 
                          "paused" (pausado), "available" (disponível)
            delay: Tempo em milissegundos que a presença ficará ativa (padrão: 5000ms = 5s)
        
        Returns:
            Dict com success (bool) e message (str)
        """
        if not self.headers:
            logger.warning("Headers da Evolution API não configurados")
            return {"success": False, "message": "API não configurada"}
        
        try:
            url = f"{self.server_url}/chat/sendPresence/{self.instance_name}"
            
            payload = {
                "number": phone,
                "options": {
                    "delay": delay,
                    "presence": presence_type
                }
            }
            
            logger.info(f"Enviando presença '{presence_type}' para {phone} ({delay}ms)")
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            
            return {
                "success": True,
                "message": f"Presença '{presence_type}' enviada com sucesso"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao enviar presença: {e}")
            return {
                "success": False,
                "message": f"Erro ao enviar presença: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar presença: {e}")
            return {
                "success": False,
                "message": f"Erro inesperado: {str(e)}"
            }
    
    async def send_payroll_message(self, phone: str, employee_name: str, 
                                 file_path: str, month_year: str, 
                                 message_template: str = None) -> Dict[str, Any]:
        """
        Envia holerite em uma única mensagem (otimizado)
        
        Returns:
            Dict com success (bool) e message (str)
        """
        try:
            if not os.path.exists(file_path):
                return {"success": False, "message": "Arquivo não encontrado"}
            
            # Converter arquivo para base64
            base64_content = self._file_to_base64(file_path)
            if not base64_content:
                return {"success": False, "message": "Erro ao processar arquivo"}
            
            # Mensagem: usar template customizada ou padrão
            if message_template:
                # Substituir placeholders na mensagem customizada
                first_name = employee_name.split()[0] if employee_name else "Colaborador"
                
                # Formatar mês/ano para exibição humanizada
                # Pode vir em dois formatos:
                # 1. "outubro_2025" (formato original do processamento)
                # 2. "2025-10" (formato do banco de dados)
                if '_' in month_year:
                    # Formato: outubro_2025 -> "outubro de 2025"
                    month_formatted = month_year.replace('_', ' de ')
                elif '-' in month_year and len(month_year) == 7:
                    # Formato: 2025-10 -> "outubro de 2025"
                    year, month_num = month_year.split('-')
                    month_names = {
                        '01': 'janeiro', '02': 'fevereiro', '03': 'março', '04': 'abril',
                        '05': 'maio', '06': 'junho', '07': 'julho', '08': 'agosto',
                        '09': 'setembro', '10': 'outubro', '11': 'novembro', '12': 'dezembro'
                    }
                    month_name = month_names.get(month_num, f'mês {month_num}')
                    month_formatted = f"{month_name} de {year}"
                else:
                    # Formato desconhecido, usar como está
                    month_formatted = month_year
                
                caption = (message_template
                          .replace('{nome}', employee_name)
                          .replace('{primeiro_nome}', first_name)
                          .replace('{mes_anterior}', month_formatted))
            else:
                # Mensagem padrão simples (caso nenhum template seja fornecido)
                caption = (f"Olá {employee_name}, segue seu holerite referente a {month_year.replace('_', ' ')}. "
                          f"A senha para abrir o arquivo são os 4 primeiros dígitos do seu CPF. "
                          f"Esta é uma mensagem automática, em caso de dúvidas contate o RH.")
            
            url = f"{self.server_url}/message/sendMedia/{self.instance_name}"
            
            payload = {
                "number": phone,
                "mediatype": "document",
                "mimetype": mimetypes.guess_type(file_path)[0] or "application/pdf",
                "caption": caption,
                "media": base64_content,
                "fileName": os.path.basename(file_path),
                "delay": 0
            }
            
            # Tentar envio com retry
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=self.headers, json=payload, timeout=60)
                    response.raise_for_status()
                    
                    result = response.json()
                    message_id = result.get('key', {}).get('id', 'N/A')
                    
                    return {
                        "success": True, 
                        "message": f"Holerite enviado com sucesso. ID: {message_id}"
                    }
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Rate limit
                        logger.warning(f"Rate limit atingido. Aguardando...")
                        time.sleep(60)
                        continue
                    elif e.response.status_code in [401, 404]:
                        return {"success": False, "message": f"Erro de API: {e.response.status_code}"}
                    else:
                        if attempt < 2:
                            time.sleep(30)
                            continue
                        return {"success": False, "message": f"Erro HTTP: {e.response.status_code}"}
                        
                except requests.exceptions.Timeout:
                    if attempt < 2:
                        time.sleep(20)
                        continue
                    return {"success": False, "message": "Timeout na requisição"}
                    
                except Exception as e:
                    if attempt < 2:
                        time.sleep(30)
                        continue
                    return {"success": False, "message": f"Erro inesperado: {str(e)}"}
            
            return {"success": False, "message": "Falha após 3 tentativas"}
            
        except Exception as e:
            logger.error(f"Erro ao enviar holerite: {e}")
            return {"success": False, "message": f"Erro interno: {str(e)}"}
    
    async def send_communication_message(self, phone: str, message_text: str = None, 
                                       file_path: str = None) -> Dict[str, Any]:
        """
        Envia comunicado (texto e/ou arquivo)
        Se houver arquivo + texto, envia TUDO EM UMA ÚNICA MENSAGEM (arquivo com legenda)
        
        Returns:
            Dict com success (bool) e message (str)
        """
        try:
            # Caso 1: Arquivo + Texto → enviar arquivo com legenda
            if file_path and os.path.exists(file_path) and message_text and message_text.strip():
                logger.info(f"📎 Enviando arquivo com legenda (texto + anexo em 1 mensagem)")
                return await self._send_media_message(phone, file_path, caption=message_text.strip())
            
            # Caso 2: Apenas arquivo → enviar arquivo sem legenda
            elif file_path and os.path.exists(file_path):
                logger.info(f"📎 Enviando apenas arquivo")
                return await self._send_media_message(phone, file_path, caption=None)
            
            # Caso 3: Apenas texto → enviar mensagem simples
            elif message_text and message_text.strip():
                logger.info(f"💬 Enviando apenas mensagem de texto")
                return await self._send_text_message(phone, message_text.strip())
            
            # Caso 4: Nada fornecido
            else:
                return {"success": False, "message": "Nenhum conteúdo para enviar"}
            
        except Exception as e:
            logger.error(f"Erro ao enviar comunicado: {e}")
            return {"success": False, "message": f"Erro interno: {str(e)}"}
    
    async def _send_text_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Envia mensagem de texto simples"""
        try:
            url = f"{self.server_url}/message/sendText/{self.instance_name}"
            payload = {"number": phone, "text": text, "delay": 0}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('key', {}).get('id', 'N/A')
            
            return {"success": True, "message": f"Mensagem enviada. ID: {message_id}"}
            
        except Exception as e:
            return {"success": False, "message": f"Erro ao enviar mensagem: {str(e)}"}
    
    async def _send_media_message(self, phone: str, file_path: str, caption: str = None) -> Dict[str, Any]:
        """Envia arquivo de mídia"""
        try:
            base64_content = self._file_to_base64(file_path)
            if not base64_content:
                return {"success": False, "message": "Erro ao processar arquivo"}
            
            # Determinar tipo de mídia
            file_extension = os.path.splitext(file_path)[1].lower()
            media_type = "image" if file_extension in ['.jpg', '.jpeg', '.png', '.gif'] else "document"
            
            url = f"{self.server_url}/message/sendMedia/{self.instance_name}"
            payload = {
                "number": phone,
                "mediatype": media_type,
                "mimetype": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                "caption": caption or "",
                "media": base64_content,
                "fileName": os.path.basename(file_path),
                "delay": 0
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('key', {}).get('id', 'N/A')
            
            return {"success": True, "message": f"Arquivo enviado. ID: {message_id}"}
            
        except Exception as e:
            return {"success": False, "message": f"Erro ao enviar arquivo: {str(e)}"}
