"""
System Routes - Sistema, Health Checks e Logs
"""
import os
import urllib.parse
from datetime import datetime
from .base import BaseRouter


class SystemRouter(BaseRouter):
    """Router para rotas de sistema, status e logs"""
    
    def handle_system_status(self):
        """
        GET /api/v1/system/status
        Status geral do sistema (uptime, versão, database)
        """
        try:
            import time
            from main_legacy import SessionLocal
            
            # Calcular uptime usando tempo de módulo (alternativa sem psutil)
            try:
                import psutil
                current_process = psutil.Process()
                uptime_seconds = time.time() - current_process.create_time()
            except ImportError:
                # Fallback: usar variável global se disponível
                uptime_seconds = 0
                try:
                    from main_legacy import start_time
                    uptime_seconds = time.time() - start_time
                except (ImportError, NameError):
                    # Se não conseguir, retornar 0
                    pass
            
            uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
            
            self.send_json_response({
                "status": "online",
                "uptime": uptime_str,
                "version": "2.0.0",
                "database": "PostgreSQL" if SessionLocal else "JSON",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"❌ Erro ao obter status do sistema: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_database_health(self):
        """
        GET /api/v1/database/health
        Health check do banco de dados PostgreSQL
        """
        try:
            from main_legacy import SessionLocal
            
            if SessionLocal:
                from sqlalchemy import text
                db = SessionLocal()
                try:
                    # Testar conexão com uma query simples
                    result = db.execute(text("SELECT version();"))
                    version = result.fetchone()[0]
                    
                    self.send_json_response({
                        "connected": True,
                        "type": "PostgreSQL",
                        "version": version,
                        "status": "online"
                    })
                except Exception as e:
                    self.send_json_response({
                        "connected": False,
                        "type": "PostgreSQL",
                        "error": str(e),
                        "status": "offline"
                    })
                finally:
                    db.close()
            else:
                self.send_json_response({
                    "connected": True,
                    "type": "JSON Fallback",
                    "status": "online",
                    "message": "Usando armazenamento JSON local"
                })
                
        except Exception as e:
            print(f"❌ Erro ao verificar saúde do banco: {e}")
            self.send_json_response({
                "connected": False,
                "error": str(e),
                "status": "error"
            })
    
    def handle_evolution_status(self):
        """
        GET /api/v1/evolution/status
        Status da integração com Evolution API (WhatsApp)
        """
        try:
            import asyncio
            
            # Buscar configurações do .env
            instance_name = os.getenv('EVOLUTION_INSTANCE_NAME', 'Desconhecido')
            server_url = os.getenv('EVOLUTION_SERVER_URL', '')
            
            # Verificar se está configurado
            if not server_url or not os.getenv('EVOLUTION_API_KEY'):
                self.send_json_response({
                    "status": "not_configured",
                    "instance_name": instance_name,
                    "server_url": server_url or "Não configurado",
                    "last_check": datetime.now().isoformat(),
                    "message": "Evolution API não configurada. Verifique as variáveis de ambiente."
                })
                return
            
            # Tentar verificação real
            try:
                from app.services.evolution_api import EvolutionAPIService
                evolution_service = EvolutionAPIService()
                
                # Criar event loop se necessário
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Verificar conexão com timeout
                is_connected = loop.run_until_complete(
                    asyncio.wait_for(
                        evolution_service.check_instance_status(),
                        timeout=5.0
                    )
                )
                
                status = "connected" if is_connected else "disconnected"
                message = "Instância conectada" if is_connected else "Instância desconectada ou offline"
                
                self.send_json_response({
                    "status": status,
                    "instance_name": instance_name,
                    "server_url": server_url,
                    "last_check": datetime.now().isoformat(),
                    "message": message
                })
                
            except asyncio.TimeoutError:
                self.send_json_response({
                    "status": "timeout",
                    "instance_name": instance_name,
                    "server_url": server_url,
                    "last_check": datetime.now().isoformat(),
                    "message": "Timeout ao verificar Evolution API (>5s)"
                })
            except Exception as check_error:
                print(f"❌ Erro ao verificar Evolution API: {check_error}")
                import traceback
                traceback.print_exc()
                self.send_json_response({
                    "status": "error",
                    "instance_name": instance_name,
                    "server_url": server_url,
                    "last_check": datetime.now().isoformat(),
                    "message": f"Erro ao verificar: {str(check_error)}"
                })
            
        except Exception as e:
            print(f"❌ Erro ao verificar Evolution API: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "status": "error",
                "error": str(e)
            }, 500)
    
    def handle_system_logs(self):
        """
        GET /api/v1/system/logs
        Lista logs do sistema com filtros opcionais
        Query params: level, category, user_id, limit, offset
        """
        from main_legacy import SessionLocal
        
        db = SessionLocal()
        try:
            from app.services.logging_service import LoggingService
            
            # Verificar autenticação
            authenticated_user = self.handler.get_authenticated_user(db)
            if not authenticated_user:
                self.send_json_response({"error": "Usuário não autenticado"}, 401)
                return
            
            # Parse query parameters
            parsed = urllib.parse.urlparse(self.handler.path)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Filtros opcionais
            level = query_params.get('level', [None])[0]
            category = query_params.get('category', [None])[0]
            user_id = query_params.get('user_id', [None])[0]
            limit = int(query_params.get('limit', [100])[0])
            offset = int(query_params.get('offset', [0])[0])
            
            # Buscar logs usando a mesma sessão
            logger = LoggingService(db)
            logs_data = logger.get_logs(
                level=level,
                category=category,
                user_id=int(user_id) if user_id else None,
                limit=limit,
                offset=offset
            )
            
            self.send_json_response(logs_data)
            
        except Exception as e:
            print(f"❌ Erro ao buscar logs: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "error": f"Erro ao buscar logs: {str(e)}"
            }, 500)
        finally:
            db.close()
