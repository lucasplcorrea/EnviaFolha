import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat
from typing import Tuple, Optional
import requests
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class PhoneValidator:
    """Validador e formatador de números de telefone internacionais"""
    
    @staticmethod
    def validate_and_format(phone: str, default_country: str = "BR") -> Tuple[bool, str, Optional[str]]:
        """
        Valida e formata número de telefone
        
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, formatted_number, error_message)
        """
        try:
            # Limpar o número
            clean_phone = ''.join(filter(str.isdigit, str(phone)))
            
            if len(clean_phone) < 8:
                return False, "", "Número muito curto"
            
            # Tentar fazer parse do número
            parsed_number = phonenumbers.parse(f"+{clean_phone}", None)
            
            # Se não conseguir, tentar com código do país padrão
            if not phonenumbers.is_valid_number(parsed_number):
                try:
                    parsed_number = phonenumbers.parse(phone, default_country)
                except NumberParseException:
                    return False, "", "Formato de número inválido"
            
            # Validar o número
            if not phonenumbers.is_valid_number(parsed_number):
                return False, "", "Número de telefone inválido"
            
            # Formatar para E164 (formato internacional)
            formatted = phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)
            # Remover o + do início para a Evolution API
            formatted = formatted[1:] if formatted.startswith('+') else formatted
            
            return True, formatted, None
            
        except NumberParseException as e:
            return False, "", f"Erro ao processar número: {e}"
        except Exception as e:
            logger.error(f"Erro inesperado na validação de telefone: {e}")
            return False, "", "Erro interno na validação"
    
    @staticmethod
    async def check_whatsapp_availability(phone: str) -> Tuple[bool, str]:
        """
        Verifica se o número tem WhatsApp através da Evolution API
        
        Returns:
            Tuple[bool, str]: (has_whatsapp, message)
        """
        try:
            if not all([settings.EVOLUTION_SERVER_URL, settings.EVOLUTION_API_KEY, settings.EVOLUTION_INSTANCE_NAME]):
                return False, "Configurações da Evolution API não encontradas"
            
            url = f"{settings.EVOLUTION_SERVER_URL.rstrip('/')}/chat/whatsappNumbers/{settings.EVOLUTION_INSTANCE_NAME}"
            headers = {
                "Content-Type": "application/json",
                "apikey": settings.EVOLUTION_API_KEY
            }
            
            payload = {
                "numbers": [phone]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # A resposta pode variar dependendo da versão da Evolution API
                if isinstance(result, list) and len(result) > 0:
                    first_result = result[0]
                    has_whatsapp = first_result.get('exists', False)
                    return has_whatsapp, "Verificação realizada com sucesso"
                else:
                    return False, "Resposta inesperada da API"
            else:
                return False, f"Erro na API: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Timeout na verificação"
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na verificação de WhatsApp: {e}")
            return False, "Erro na comunicação com a API"
        except Exception as e:
            logger.error(f"Erro inesperado na verificação de WhatsApp: {e}")
            return False, "Erro interno na verificação"
    
    @staticmethod
    def get_country_from_phone(phone: str) -> Optional[str]:
        """
        Detecta o país baseado no número de telefone
        
        Returns:
            Optional[str]: Código do país (ex: "BR", "US") ou None
        """
        try:
            clean_phone = ''.join(filter(str.isdigit, str(phone)))
            parsed_number = phonenumbers.parse(f"+{clean_phone}", None)
            
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.region_code_for_number(parsed_number)
            return None
            
        except Exception:
            return None
