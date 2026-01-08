"""
Dashboard Routes - Estatísticas e métricas do dashboard
"""
from datetime import datetime
from .base import BaseRouter


class DashboardRouter(BaseRouter):
    """Router para rotas do dashboard"""
    
    def handle_dashboard_stats(self):
        """
        GET /api/v1/dashboard/stats
        Retorna estatísticas gerais para os cards do dashboard
        """
        try:
            from main_legacy import load_employees_data, SessionLocal
            import os
            import asyncio
            
            # Carregar dados dos colaboradores
            current_data = load_employees_data()
            employees_count = len(current_data.get('employees', []))
            
            # Verificar conexão com banco de dados
            database_status = "connected" if SessionLocal else "disconnected"
            
            # Verificar Evolution API (tentar conexão real)
            evolution_status = "disconnected"
            evolution_url = os.getenv('EVOLUTION_SERVER_URL')
            evolution_key = os.getenv('EVOLUTION_API_KEY')
            evolution_instance = os.getenv('EVOLUTION_INSTANCE_NAME')
            
            if evolution_url and evolution_key and evolution_instance:
                try:
                    # Importar o serviço e testar conexão
                    from app.services.evolution_api import EvolutionAPIService
                    evolution_service = EvolutionAPIService()
                    
                    # Criar event loop se necessário
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Testar conexão (timeout curto para não travar o dashboard)
                    try:
                        # Verificar se a instância está conectada
                        is_connected = loop.run_until_complete(
                            asyncio.wait_for(
                                evolution_service.check_instance_status(),
                                timeout=3.0  # 3 segundos de timeout
                            )
                        )
                        if is_connected:
                            evolution_status = "connected"
                        else:
                            evolution_status = "disconnected"
                    except asyncio.TimeoutError:
                        print("⚠️ Timeout ao verificar Evolution API (dashboard)")
                        evolution_status = "timeout"
                    except Exception as check_error:
                        print(f"⚠️ Erro ao verificar Evolution API: {check_error}")
                        evolution_status = "error"
                        
                except Exception as e:
                    print(f"⚠️ Erro ao importar/testar Evolution API: {e}")
                    evolution_status = "error"
            
            # TODO: Buscar métricas reais do banco de dados
            stats = {
                "total_employees": employees_count,
                "active_employees": employees_count,  # Assumindo todos ativos
                "payrolls_sent_this_month": 0,  # TODO: implementar contagem real
                "communications_sent_this_month": 0,  # TODO: implementar contagem real
                "last_payroll_send": None,  # TODO: implementar data real
                "evolution_api_status": evolution_status,
                "database_status": database_status
            }
            
            self.send_json_response(stats)
            
        except Exception as e:
            print(f"❌ Erro ao carregar estatísticas do dashboard: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "error": f"Erro ao carregar estatísticas: {str(e)}"
            }, 500)
