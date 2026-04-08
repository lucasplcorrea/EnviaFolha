#!/usr/bin/env python3
"""Servidor HTTP modular do Sistema de Envio RH v2.0."""

from __future__ import annotations

import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.core.auth import verify_token
from app.models.base import SessionLocal as BaseSessionLocal, engine as db_engine
from app.models.user import User
from app.routes import (
    AuthRouter,
    CompaniesRouter,
    DashboardRouter,
    EmployeesRouter,
    IndicatorsRouter,
    SystemRouter,
    TaxStatementsRouter,
    WorkLocationsRouter,
)
from app.routes.benefits import BenefitsRouter
from app.routes.endomarketing import EndomarketingRouter
from app.routes.files import FilesRouter
from app.routes.payroll import PayrollRouter
from app.routes.queue import QueueRouter
from app.routes.reports import ReportsRouter
from app.routes.timecard_http import TimecardRouter
from app.routes.users import UsersRouter
from app.services.runtime_compat import check_database_health, load_employees_data


PORT = int(os.getenv('PORT', 8002))
SessionLocal = BaseSessionLocal


try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


class ModularEnviaFolhaHandler(BaseHTTPRequestHandler):
    """Servidor HTTP sem dependência do legado."""

    @staticmethod
    def _normalize_path(raw_path: str) -> str:
        parts = [part for part in (raw_path or '').split('/') if part]
        return '/' if not parts else '/' + '/'.join(parts)

    def send_json_response(self, data, status_code: int = 200):
        import json

        response = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(response)

    def send_error(self, message: str, status_code: int = 400):
        self.send_json_response({'error': message}, status_code)

    def get_request_data(self):
        import json

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            return {}
        payload = self.rfile.read(content_length)
        if not payload:
            return {}
        try:
            return json.loads(payload.decode('utf-8'))
        except Exception:
            return {}

    def get_authenticated_user(self, db=None):
        authorization = self.headers.get('Authorization', '')
        if not authorization.startswith('Bearer '):
            return None

        token = authorization.replace('Bearer ', '', 1).strip()
        payload = verify_token(token)
        if not payload:
            return None

        username = payload.get('sub')
        if not username:
            return None

        session = db
        created_session = False
        if session is None:
            if not SessionLocal:
                return None
            session = SessionLocal()
            created_session = True

        try:
            user = session.query(User).filter(User.username == username).first()
            return user if user and user.is_active else None
        finally:
            if created_session and session is not None:
                session.close()

    def _route_get(self, path: str):
        if path == '/api/v1/auth/me':
            AuthRouter(self).handle_auth_me()
            return
        if path in ('/api/v1/system/status', '/api/v1/database/health', '/api/v1/health'):
            if path == '/api/v1/system/status':
                SystemRouter(self).handle_system_status()
            else:
                SystemRouter(self).handle_database_health()
            return

        if path == '/api/v1/evolution/status':
            SystemRouter(self).handle_evolution_status()
            return

        if path == '/api/v1/evolution/instances':
            SystemRouter(self).handle_evolution_instances_status()
            return

        if path == '/api/v1/dashboard/stats':
            DashboardRouter(self).handle_dashboard_stats()
            return

        if path == '/api/v1/tax-statements/export/sent':
            TaxStatementsRouter(self).handle_export_sent()
            return

        if path == '/api/v1/tax-statements':
            TaxStatementsRouter(self).handle_list()
            return

        if path.startswith('/api/v1/tax-statements/process/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 7:
                TaxStatementsRouter(self).handle_process_status(parts[5])
                return

        if path.startswith('/api/v1/tax-statements/send/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 7:
                TaxStatementsRouter(self).handle_send_status(parts[5])
                return

        if path == '/api/v1/payroll' or path.startswith('/api/v1/payroll/') or path.startswith('/api/v1/payrolls/'):
            PayrollRouter(self).handle_get(path)
            return

        if path.startswith('/api/v1/reports/'):
            if path == '/api/v1/reports/recent':
                ReportsRouter(self).handle_recent_activity()
                return
            if path == '/api/v1/reports/statistics':
                ReportsRouter(self).handle_statistics()
                return
            if path == '/api/v1/reports/exports/infra-analytics':
                ReportsRouter(self).handle_export_infra_analytics()
                return

        if path.startswith('/api/v1/endomarketing/'):
            EndomarketingRouter(self).handle_get(path)
            return

        if path.startswith('/api/v1/timecard/'):
            TimecardRouter(self).handle_get(path)
            return

        if path.startswith('/api/v1/queue/'):
            QueueRouter(self).handle_get(path)
            return

        if path in ('/api/v1/users', '/api/v1/roles', '/api/v1/users/permissions'):
            UsersRouter(self).handle_get(path)
            return

        if path.startswith('/api/v1/benefits/periods/') or path in ('/api/v1/benefits/periods', '/api/v1/benefits/processing-logs') or '/employees/' in path and '/benefits' in path:
            BenefitsRouter(self).handle_get(path)
            return

        if path.startswith('/api/v1/indicators/'):
            IndicatorsRouter(self).handle_get(path)
            return

        if path == '/api/v1/companies':
            CompaniesRouter(self).handle_list()
            return

        if path.startswith('/api/v1/companies/'):
            try:
                company_id = int(path.split('/')[-1])
                CompaniesRouter(self).handle_get(company_id)
            except ValueError:
                self.send_error('Empresa inválida', 400)
            return

        if path == '/api/v1/work-locations':
            WorkLocationsRouter(self).handle_list()
            return

        if path.startswith('/api/v1/work-locations/'):
            try:
                location_id = int(path.split('/')[-1])
                WorkLocationsRouter(self).handle_get(location_id)
            except ValueError:
                self.send_error('Local inválido', 400)
            return

        if path == '/api/v1/employees' or path.startswith('/api/v1/employees/'):
            EmployeesRouter(self).handle_get(path)
            return

        self.send_error('Endpoint não encontrado', 404)

    def do_GET(self):
        path = self._normalize_path(urllib.parse.urlparse(self.path).path)
        self._route_get(path)

    def do_POST(self):
        path = self._normalize_path(urllib.parse.urlparse(self.path).path)

        if path == '/api/v1/auth/login':
            AuthRouter(self).handle_login()
            return

        if path == '/api/v1/tax-statements/process':
            TaxStatementsRouter(self).handle_process()
            return

        if path == '/api/v1/tax-statements/send':
            TaxStatementsRouter(self).handle_send()
            return

        if path == '/api/v1/tax-statements/delete':
            TaxStatementsRouter(self).handle_delete()
            return

        if path == '/api/v1/benefits/upload-xlsx' or path == '/api/v1/benefits/periods':
            BenefitsRouter(self).handle_post(path)
            return

        if path == '/api/v1/files/upload' or path == '/api/v1/uploads/csv':
            FilesRouter(self).handle_post(path)
            return

        if path == '/api/v1/indicators/cache/invalidate':
            IndicatorsRouter(self).handle_post(path)
            return

        if path == '/api/v1/payroll' or path.startswith('/api/v1/payroll/') or path.startswith('/api/v1/payrolls/'):
            PayrollRouter(self).handle_post(path)
            return

        if path.startswith('/api/v1/timecard/'):
            TimecardRouter(self).handle_post(path)
            return

        if path.startswith('/api/v1/queue/'):
            QueueRouter(self).handle_post(path)
            return

        if path in ('/api/v1/users', '/api/v1/users/permissions'):
            UsersRouter(self).handle_post(path)
            return

        if path == '/api/v1/companies':
            CompaniesRouter(self).handle_create()
            return

        if path == '/api/v1/work-locations':
            WorkLocationsRouter(self).handle_create()
            return

        if path == '/api/v1/employees' or path == '/api/v1/employees/cache/invalidate' or path.startswith('/api/v1/employees/'):
            EmployeesRouter(self).handle_post(path)
            return

        self.send_error('Endpoint não encontrado', 404)

    def do_PUT(self):
        path = self._normalize_path(urllib.parse.urlparse(self.path).path)

        if path.startswith('/api/v1/companies/'):
            try:
                company_id = int(path.split('/')[-1])
                CompaniesRouter(self).handle_update(company_id)
            except ValueError:
                self.send_error('Empresa inválida', 400)
            return

        if path.startswith('/api/v1/work-locations/'):
            try:
                location_id = int(path.split('/')[-1])
                WorkLocationsRouter(self).handle_update(location_id)
            except ValueError:
                self.send_error('Local inválido', 400)
            return

        if path == '/api/v1/employees' or path.startswith('/api/v1/employees/'):
            EmployeesRouter(self).handle_put(path)
            return

        if path.startswith('/api/v1/users/'):
            UsersRouter(self).handle_put(path)
            return

        self.send_error('Endpoint não encontrado', 404)

    def do_DELETE(self):
        path = self._normalize_path(urllib.parse.urlparse(self.path).path)

        if path.startswith('/api/v1/companies/'):
            try:
                company_id = int(path.split('/')[-1])
                CompaniesRouter(self).handle_delete(company_id)
            except ValueError:
                self.send_error('Empresa inválida', 400)
            return

        if path.startswith('/api/v1/work-locations/'):
            try:
                location_id = int(path.split('/')[-1])
                WorkLocationsRouter(self).handle_delete(location_id)
            except ValueError:
                self.send_error('Local inválido', 400)
            return

        if path.startswith('/api/v1/benefits/'):
            BenefitsRouter(self).handle_delete(path)
            return

        if path == '/api/v1/employees/bulk' or path == '/api/v1/employees' or path.startswith('/api/v1/employees/'):
            EmployeesRouter(self).handle_delete(path)
            return

        if path.startswith('/api/v1/timecard/periods/'):
            TimecardRouter(self).handle_delete(path)
            return

        if path.startswith('/api/v1/payroll/periods/'):
            PayrollRouter(self).handle_delete(path)
            return

        if path.startswith('/api/v1/users/'):
            UsersRouter(self).handle_delete(path)
            return

        self.send_error('Endpoint não encontrado', 404)

    def do_PATCH(self):
        path = self._normalize_path(urllib.parse.urlparse(self.path).path)

        if path == '/api/v1/employees/bulk':
            EmployeesRouter(self).handle_patch(path)
            return

        self.send_error('Endpoint não encontrado', 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def log_message(self, format, *args):
        return


def print_startup_banner():
    try:
        employees_data = load_employees_data()
        employees_count = len(employees_data.get('employees', []))
        db_health = check_database_health()
        db_type = db_health.get('type', 'Desconhecido')

        print('=' * 60)
        print('🚀 Sistema de Envio RH v2.0 - Modular')
        print('=' * 60)
        print(f'📡 Servidor: http://localhost:{PORT}')
        print(f'🗄️  Banco de dados: {db_type}')
        print(f'👥 Colaboradores: {employees_count}')
        print('📁 Estrutura: Modular (app/routes, app/services)')
        print('=' * 60)
        print()
    except Exception as exc:
        print(f'⚠️  Erro ao carregar informações iniciais: {exc}')
        print('   Servidor iniciará mesmo assim...')
        print()


def cleanup_connections():
    try:
        if db_engine:
            db_engine.dispose()
            print('🔌 Conexão com PostgreSQL encerrada')
    except Exception as exc:
        print(f'⚠️  Erro ao encerrar conexão: {exc}')


def main():
    try:
        print_startup_banner()
        server_address = ('', PORT)
        httpd = HTTPServer(server_address, ModularEnviaFolhaHandler)

        print(f'✅ Servidor rodando em http://localhost:{PORT}')
        print('   📦 Estrutura modular ativa')
        print('   ⏸️  Pressione Ctrl+C para parar')
        print()

        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n\n🛑 Servidor finalizado pelo usuário')
    except OSError as exc:
        if 'address already in use' in str(exc).lower():
            print(f'\n❌ ERRO: Porta {PORT} já está em uso!')
            print(f'   Solução: Pare o processo na porta {PORT} ou use outra porta')
        else:
            print(f'\n❌ Erro ao iniciar servidor: {exc}')
    finally:
        cleanup_connections()


if __name__ == '__main__':
    main()
