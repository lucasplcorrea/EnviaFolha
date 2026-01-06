"""
Gerenciador de Múltiplas Instâncias WhatsApp
Controla round-robin e delays por instância
"""
import time
import threading
import logging
from typing import Dict, Optional
from ..core.config import settings
from .evolution_api import EvolutionAPIService

logger = logging.getLogger(__name__)

class InstanceManager:
    """Gerencia múltiplas instâncias WhatsApp com round-robin"""
    
    def __init__(self):
        self.instances = settings.get_evolution_instances()
        self.current_index = 0
        self.last_send_time: Dict[str, float] = {}  # {instance_name: timestamp}
        self.lock = threading.Lock()
        
        logger.info(f"InstanceManager inicializado com {len(self.instances)} instância(s): {self.instances}")
    
    def get_next_instance(self) -> Optional[str]:
        """
        Retorna próxima instância disponível (round-robin)
        
        Returns:
            Nome da instância ou None se nenhuma configurada
        """
        with self.lock:
            if not self.instances:
                logger.warning("Nenhuma instância WhatsApp configurada")
                return None
            
            instance_name = self.instances[self.current_index]
            
            # Avançar para próxima (circular)
            self.current_index = (self.current_index + 1) % len(self.instances)
            
            logger.debug(f"Próxima instância selecionada: {instance_name} (índice: {self.current_index})")
            return instance_name
    
    def get_instance_delay(self, instance_name: str) -> float:
        """
        Retorna tempo (em segundos) desde último envio nesta instância
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Segundos desde último envio (infinito se nunca enviou)
        """
        last_time = self.last_send_time.get(instance_name, 0)
        if last_time == 0:
            return float('inf')  # Nunca enviou
        return time.time() - last_time
    
    def should_wait(self, instance_name: str, min_delay: float = 300) -> bool:
        """
        Verifica se deve aguardar antes de usar esta instância
        
        Args:
            instance_name: Nome da instância
            min_delay: Delay mínimo em segundos (padrão: 5 minutos)
            
        Returns:
            True se deve aguardar, False se pode usar
        """
        delay = self.get_instance_delay(instance_name)
        should_wait = delay < min_delay
        
        if should_wait:
            remaining = min_delay - delay
            logger.debug(f"Instância {instance_name} precisa aguardar {remaining:.1f}s")
        
        return should_wait
    
    def register_send(self, instance_name: str):
        """
        Registra que um envio foi realizado nesta instância
        
        Args:
            instance_name: Nome da instância
        """
        with self.lock:
            self.last_send_time[instance_name] = time.time()
            logger.debug(f"Envio registrado para instância {instance_name}")
    
    def get_instance_stats(self) -> Dict[str, Dict]:
        """
        Retorna estatísticas de cada instância
        
        Returns:
            Dict com stats por instância
        """
        stats = {}
        for inst_name in self.instances:
            delay = self.get_instance_delay(inst_name)
            stats[inst_name] = {
                "last_send": self.last_send_time.get(inst_name, 0),
                "seconds_since_last_send": delay if delay != float('inf') else None,
                "ready": not self.should_wait(inst_name)
            }
        return stats
    
    async def check_all_instances_status(self) -> Dict[str, bool]:
        """
        Verifica status de conexão de todas as instâncias
        
        Returns:
            Dict {instance_name: is_connected}
        """
        status = {}
        for inst_name in self.instances:
            try:
                service = EvolutionAPIService(inst_name)
                is_online = await service.check_instance_status()
                status[inst_name] = is_online
                logger.info(f"Instância {inst_name}: {'online' if is_online else 'offline'}")
            except Exception as e:
                logger.error(f"Erro ao verificar instância {inst_name}: {e}")
                status[inst_name] = False
        return status
    
    def get_total_instances(self) -> int:
        """Retorna número total de instâncias configuradas"""
        return len(self.instances)
    
    def has_multiple_instances(self) -> bool:
        """Verifica se há mais de uma instância configurada"""
        return len(self.instances) > 1


# Instância global (singleton)
_instance_manager = None

def get_instance_manager() -> InstanceManager:
    """Retorna instância singleton do gerenciador"""
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = InstanceManager()
    return _instance_manager
