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
            return False
            
        try:
            url = f"{self.server_url}/instance/connectionState/{self.instance_name}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            status = result.get('instance', {}).get('state', 'unknown')
            
            return status in ['open', 'connected']
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da instância: {e}")
            return False
    
    async def send_payroll_message(self, phone: str, employee_name: str, 
                                 file_path: str, month_year: str) -> Dict[str, Any]:
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
            
            # Mensagem combinada (saudação + instruções)
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
        
        Returns:
            Dict com success (bool) e message (str)
        """
        try:
            results = []
            
            # Enviar mensagem de texto se fornecida
            if message_text and message_text.strip():
                text_result = await self._send_text_message(phone, message_text.strip())
                results.append(text_result)
                
                # Delay entre mensagem e arquivo
                if file_path and os.path.exists(file_path):
                    time.sleep(10)
            
            # Enviar arquivo se fornecido
            if file_path and os.path.exists(file_path):
                file_result = await self._send_media_message(phone, file_path, message_text)
                results.append(file_result)
            
            # Verificar se pelo menos um envio foi bem-sucedido
            if not results:
                return {"success": False, "message": "Nenhum conteúdo para enviar"}
            
            successful = any(r["success"] for r in results)
            messages = [r["message"] for r in results]
            
            return {
                "success": successful,
                "message": "; ".join(messages)
            }
            
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
