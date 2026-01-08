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
            
            # Log estado atual
            logger.info(f"📊 Estado antes: current_index={self.current_index}, total_instances={len(self.instances)}")
            logger.info(f"📊 Instâncias disponíveis: {self.instances}")
            
            instance_name = self.instances[self.current_index]
            
            # Avançar para próxima (circular)
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.instances)
            
            logger.info(f"✅ Instância selecionada: {instance_name}")
            logger.info(f"📊 Índice avançado: {old_index} → {self.current_index}")
            logger.info(f"📊 Próxima será: {self.instances[self.current_index] if self.instances else 'N/A'}")
            
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
    
    async def get_next_available_instance(self) -> Optional[str]:
        """
        Retorna próxima instância ONLINE disponível (round-robin inteligente)
        Verifica conexão de cada instância antes de retornar
        
        Returns:
            Nome da instância online ou None se todas offline
        """
        if not self.instances:
            logger.warning("❌ Nenhuma instância WhatsApp configurada")
            return None
        
        # Verificar status de todas as instâncias
        all_status = await self.check_all_instances_status()
        online_instances = [inst for inst, is_online in all_status.items() if is_online]
        
        if not online_instances:
            logger.error("❌ TODAS as instâncias estão offline!")
            return None
        
        logger.info(f"📡 Instâncias online: {online_instances} (de {len(self.instances)} totais)")
        
        # Se só há uma instância online, retornar ela
        if len(online_instances) == 1:
            logger.info(f"✅ Única instância online: {online_instances[0]}")
            return online_instances[0]
        
        # Round-robin entre as instâncias ONLINE
        with self.lock:
            # Encontrar índice atual no array de instâncias online
            # Se não houver último usado ou ele estiver offline, começar do 0
            last_used = getattr(self, '_last_used_online', None)
            
            if last_used and last_used in online_instances:
                # Avançar para próxima instância online
                current_idx = online_instances.index(last_used)
                next_idx = (current_idx + 1) % len(online_instances)
            else:
                # Primeira vez ou última usada está offline
                next_idx = 0
            
            selected = online_instances[next_idx]
            self._last_used_online = selected
            
            logger.info(f"✅ Round-robin: {last_used} → {selected} (índice {next_idx}/{len(online_instances)-1})")
            return selected


# Instância global (singleton)
_instance_manager = None

def get_instance_manager() -> InstanceManager:
    """Retorna instância singleton do gerenciador"""
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = InstanceManager()
    return _instance_manager
