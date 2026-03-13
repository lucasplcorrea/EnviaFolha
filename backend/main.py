"""
Main Module - Sistema de Envio RH v2.0 Refatorado (NOVA VERSÃO)
================================================================================

ARQUITETURA:
- main.py (este arquivo): Inicialização minimalista (~100 linhas)
- main_legacy.py: Código original completo (backup/referência)
- app/routes/: Rotas organizadas por domínio
- app/handlers/: Lógica de negócio
- app/services/: Integrações externas (Evolution API, etc)
- app/models/: Modelos do banco de dados
- app/core/: Configurações e autenticação

MUDANÇAS:
✅ Código modular e organizado
✅ Facilita manutenção e testes
✅ Mantém todas funcionalidades
✅ Preparado para crescimento

================================================================================
"""
import os
import sys
import urllib.parse
from http.server import HTTPServer

# Importar RequestHandler do código legado (TEMPORÁRIO - fase 1 da refatoração)
# Próximas fases: migrar handlers gradualmente para app/handlers/
from main_legacy import (
    EnviaFolhaHandler,
    load_employees_data,
    check_database_health,
    SessionLocal,
    db_engine
)

from app.routes import TaxStatementsRouter

# Configurações
PORT = int(os.getenv('PORT', 8002))


class ModularEnviaFolhaHandler(EnviaFolhaHandler):
    """Adapter que intercepta rotas modulares sem expandir o main_legacy."""

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/v1/tax-statements/export/sent':
            TaxStatementsRouter(self).handle_export_sent()
            return

        if path == '/api/v1/tax-statements':
            TaxStatementsRouter(self).handle_list()
            return

        if path.startswith('/api/v1/tax-statements/process/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 7:
                job_id = parts[5]
                TaxStatementsRouter(self).handle_process_status(job_id)
                return

        if path.startswith('/api/v1/tax-statements/send/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 7:
                queue_id = parts[5]
                TaxStatementsRouter(self).handle_send_status(queue_id)
                return

        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/v1/tax-statements/process':
            TaxStatementsRouter(self).handle_process()
            return

        if path == '/api/v1/tax-statements/send':
            TaxStatementsRouter(self).handle_send()
            return

        if path == '/api/v1/tax-statements/delete':
            TaxStatementsRouter(self).handle_delete()
            return

        super().do_POST()


def print_startup_banner():
    """Exibir banner de inicialização"""
    try:
        employees_data = load_employees_data()
        employees_count = len(employees_data.get('employees', []))
        db_health = check_database_health()
        db_type = db_health.get("type", "Desconhecido")
        
        print("=" * 60)
        print("🚀 Sistema de Envio RH v2.0 - REFATORADO")
        print("=" * 60)
        print(f"📡 Servidor: http://localhost:{PORT}")
        print(f"🗄️  Banco de dados: {db_type}")
        print(f"👥 Colaboradores: {employees_count}")
        print(f"📁 Estrutura: Modular (app/routes, app/handlers)")
        print("=" * 60)
        print()
        
    except Exception as e:
        print(f"⚠️  Erro ao carregar informações iniciais: {e}")
        print("   Servidor iniciará mesmo assim...")
        print()


def cleanup_connections():
    """Encerrar conexões do banco de dados"""
    try:
        if SessionLocal and db_engine:
            db_engine.dispose()
            print("🔌 Conexão com PostgreSQL encerrada")
    except Exception as e:
        print(f"⚠️  Erro ao encerrar conexão: {e}")


def main():
    """
    Função principal do servidor
    
    Fase 1 (ATUAL): Usa EnviaFolhaHandler do main_legacy.py
    Fase 2 (PRÓXIMA): Migrar rotas para app/routes/
    Fase 3 (FUTURA): Migrar handlers para app/handlers/
    """
    try:
        # Exibir informações de inicialização
        print_startup_banner()
        
        # Criar servidor HTTP
        server_address = ('', PORT)
        httpd = HTTPServer(server_address, ModularEnviaFolhaHandler)
        
        print(f"✅ Servidor rodando em http://localhost:{PORT}")
        print("   🔧 Código em main_legacy.py (backup seguro)")
        print("   📦 Estrutura modular preparada em app/")
        print("   ⏸️  Pressione Ctrl+C para parar")
        print()
        
        # Iniciar loop do servidor
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor finalizado pelo usuário")
        
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"\n❌ ERRO: Porta {PORT} já está em uso!")
            print(f"   Solução: Pare o processo na porta {PORT} ou use outra porta")
        else:
            print(f"\n❌ Erro de rede: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        cleanup_connections()


if __name__ == '__main__':
    # Adicionar diretório ao path para imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Iniciar servidor
    main()
