"""
Filtro de Logging para Reduzir Ruído de Healthchecks
Silencia logs repetitivos de polling do frontend
"""
import logging


class HealthCheckFilter(logging.Filter):
    """
    Filtro que remove logs de rotas de healthcheck/polling
    """
    
    # Rotas que devem ser silenciadas (não aparecer nos logs)
    SILENT_ROUTES = [
        '/api/v1/database/health',      # Healthcheck do banco (a cada 5s)
        '/api/v1/queue/active',          # Polling de filas ativas (a cada 3s)
        '/api/v1/payrolls/bulk-send/',   # Polling de status de jobs (a cada 2s)
        '/api/v1/evolution/instances',   # Polling de status WhatsApp (a cada 5s)
        '/favicon.ico',                   # Navegador pedindo favicon
    ]
    
    def filter(self, record):
        """
        Retorna False para silenciar log, True para permitir
        
        Args:
            record: LogRecord do logging
            
        Returns:
            False se deve silenciar, True se deve logar
        """
        # Pegar mensagem do log
        message = record.getMessage()
        
        # Verificar se é uma requisição HTTP
        if '"GET ' in message or '"POST ' in message:
            # Verificar se contém alguma rota silenciosa
            for route in self.SILENT_ROUTES:
                if route in message:
                    return False  # Silenciar este log
        
        return True  # Permitir todos os outros logs


def setup_quiet_logging():
    """
    Configura logging silencioso para healthchecks
    Mantém logs importantes, remove ruído de polling
    """
    # Obter logger raiz
    root_logger = logging.getLogger()
    
    # Adicionar filtro ao logger raiz
    health_filter = HealthCheckFilter()
    root_logger.addFilter(health_filter)
    
    # Também adicionar aos handlers específicos se existirem
    for handler in root_logger.handlers:
        handler.addFilter(health_filter)
    
    print("🔇 Filtro de healthcheck ativado - logs de polling silenciados")


def setup_verbose_logging():
    """
    Remove filtros - mostra todos os logs (útil para debug)
    """
    root_logger = logging.getLogger()
    
    # Remover todos os filtros HealthCheckFilter
    for handler in root_logger.handlers:
        for filter_obj in handler.filters[:]:
            if isinstance(filter_obj, HealthCheckFilter):
                handler.removeFilter(filter_obj)
    
    # Remover do logger raiz também
    for filter_obj in root_logger.filters[:]:
        if isinstance(filter_obj, HealthCheckFilter):
            root_logger.removeFilter(filter_obj)
    
    print("📢 Modo verbose ativado - mostrando todos os logs")
