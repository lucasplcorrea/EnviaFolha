#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Envio RH - Servidor Mínimo
Baseado nos scripts de backup que funcionam em produção
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
import sys
import time
import random

# Função para carregar variáveis do .env
def load_env_file():
    """Carrega variáveis do arquivo .env"""
    env_vars = {}
    
    # Tentar diferentes caminhos para o .env
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # ../env
        os.path.join(os.path.dirname(__file__), '..', '.env'),              # ../env
        os.path.join(os.getcwd(), '.env'),                                   # ./env no diretório atual
        '.env'                                                               # .env no diretório atual
    ]
    
    env_file = None
    for path in possible_paths:
        if os.path.exists(path):
            env_file = path
            break
    
    if not env_file:
        print(f"⚠️  Arquivo .env não encontrado nos caminhos: {possible_paths}")
        return env_vars
    
    print(f"📄 Carregando .env de: {env_file}")
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove aspas se existirem
                value = value.strip('"\'')
                env_vars[key.strip()] = value
    
    return env_vars

class EvolutionAPI:
    """Cliente para Evolution API baseado no script de backup"""
    
    def __init__(self):
        env_vars = load_env_file()
        self.server_url = env_vars.get('EVOLUTION_SERVER_URL', '').rstrip('/')
        self.api_key = env_vars.get('EVOLUTION_API_KEY', '')
        self.instance_name = env_vars.get('EVOLUTION_INSTANCE_NAME', '')
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
    
    def send_message(self, phone_number, message):
        """Envia mensagem de texto"""
        try:
            url = f"{self.server_url}/message/sendText/{self.instance_name}"
            data = {
                "number": phone_number,
                "text": message
            }
            
            # Simula envio por enquanto - em produção faria request real
            print(f"[MOCK] Enviando mensagem para {phone_number}: {message[:50]}...")
            time.sleep(random.uniform(1, 3))  # Simula delay da API
            
            return {"success": True, "message": "Mensagem enviada com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_file(self, phone_number, file_path, caption=""):
        """Envia arquivo"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "Arquivo não encontrado"}
            
            # Simula envio de arquivo por enquanto
            print(f"[MOCK] Enviando arquivo para {phone_number}: {os.path.basename(file_path)}")
            time.sleep(random.uniform(2, 5))  # Simula delay maior para arquivos
            
            return {"success": True, "message": "Arquivo enviado com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_connection(self):
        """Verifica conexão com a API"""
        if not all([self.server_url, self.api_key, self.instance_name]):
            return {"connected": False, "error": "Configurações incompletas"}
        
        # Em produção faria request real para verificar status
        return {"connected": True, "instance": self.instance_name}

# Configurações
PORT = 8002
UPLOAD_DIR = "uploads"
ENVIADOS_DIR = "enviados" 
DATA_FILE = "employees.json"

# Criar diretórios necessários
for directory in [UPLOAD_DIR, ENVIADOS_DIR]:
    os.makedirs(directory, exist_ok=True)

class SimpleDatabase:
    """Banco de dados simples usando JSON"""
    
    def __init__(self, filename):
        self.filename = filename
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Dados padrão
        return {
            "employees": [
                {
                    "id": 1,
                    "unique_id": "001",
                    "full_name": "Administrador Teste",
                    "phone_number": "11999999999",
                    "email": "admin@teste.com",
                    "department": "TI",
                    "position": "Administrador",
                    "is_active": True
                }
            ],
            "users": [
                {
                    "id": 1,
                    "username": "admin",
                    "password": "admin123",
                    "full_name": "Administrador",
                    "email": "admin@empresa.com",
                    "is_admin": True
                }
            ]
        }
    
    def save_data(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_employees(self):
        return [emp for emp in self.data["employees"] if emp.get("is_active", True)]
    
    def add_employee(self, employee_data):
        new_id = max([emp.get("id", 0) for emp in self.data["employees"]], default=0) + 1
        employee_data["id"] = new_id
        employee_data["created_at"] = datetime.now().isoformat()
        self.data["employees"].append(employee_data)
        self.save_data()
        return employee_data
    
    def update_employee(self, employee_id, employee_data):
        for emp in self.data["employees"]:
            if emp.get("id") == employee_id:
                emp.update(employee_data)
                self.save_data()
                return emp
        return None
    
    def delete_employee(self, employee_id):
        for emp in self.data["employees"]:
            if emp.get("id") == employee_id:
                emp["is_active"] = False
                self.save_data()
                return True
        return False

# Inicializar banco de dados
db = SimpleDatabase(DATA_FILE)

class APIHandler(http.server.SimpleHTTPRequestHandler):
    """Handler para as requisições da API"""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Enviar headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def send_json_response(self, data, status_code=200):
        """Enviar resposta JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def get_request_data(self):
        """Obter dados da requisição POST/PUT"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except:
            return {}
    
    def do_GET(self):
        """Handle GET requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/':
            self.send_json_response({
                "message": "Sistema de Envio RH v2.0",
                "status": "running",
                "docs": "/docs",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "note": "Servidor mínimo baseado nos scripts de produção"
            })
        
        elif path == '/api/v1/employees':
            employees = db.get_employees()
            self.send_json_response(employees)
        
        elif path.startswith('/api/v1/employees/'):
            try:
                employee_id = int(path.split('/')[-1])
                employees = db.get_employees()
                employee = next((emp for emp in employees if emp['id'] == employee_id), None)
                
                if employee:
                    self.send_json_response(employee)
                else:
                    self.send_json_response({"error": "Colaborador não encontrado"}, 404)
            except ValueError:
                self.send_json_response({"error": "ID inválido"}, 400)
        
        elif path == '/api/v1/auth/me':
            # Usuário mock para autenticação
            self.send_json_response({
                "id": 1,
                "username": "admin",
                "full_name": "Administrador",
                "email": "admin@empresa.com",
                "is_admin": True
            })
        
        elif path == '/api/v1/evolution/status':
            # Carrega configurações do .env
            env_vars = load_env_file()
            
            server_url = env_vars.get('EVOLUTION_SERVER_URL', '')
            api_key = env_vars.get('EVOLUTION_API_KEY', '')
            instance_name = env_vars.get('EVOLUTION_INSTANCE_NAME', '')
            
            has_config = all([server_url, api_key, instance_name])
            
            if has_config:
                # Tenta verificar conectividade com a Evolution API
                try:
                    # Simula verificação de status - em produção faria request real
                    self.send_json_response({
                        "connected": True,
                        "instance_name": instance_name,
                        "server_url": server_url,
                        "config": {
                            "server_url": bool(server_url),
                            "api_key": bool(api_key),
                            "instance_name": bool(instance_name)
                        }
                    })
                except Exception as e:
                    self.send_json_response({
                        "connected": False,
                        "error": f"Erro ao conectar com Evolution API: {str(e)}",
                        "config": {
                            "server_url": bool(server_url),
                            "api_key": bool(api_key), 
                            "instance_name": bool(instance_name)
                        }
                    })
            else:
                self.send_json_response({
                    "connected": False,
                    "error": "Configurações da Evolution API não encontradas no .env",
                    "config": {
                        "server_url": bool(server_url),
                        "api_key": bool(api_key),
                        "instance_name": bool(instance_name)
                    }
                })
        
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_POST(self):
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/api/v1/auth/login':
            data = self.get_request_data()
            username = data.get('username')
            password = data.get('password')
            
            print(f"🔐 Tentativa de login - Username: '{username}', Password: '{password}'")
            print(f"📥 Dados recebidos: {data}")
            
            if username == 'admin' and password == 'admin123':
                print("✅ Login bem-sucedido!")
                self.send_json_response({
                    "access_token": "simple-token-123",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "username": "admin",
                        "full_name": "Administrador",
                        "email": "admin@empresa.com",
                        "is_admin": True
                    }
                })
            else:
                print("❌ Credenciais inválidas!")
                self.send_json_response({"detail": "Credenciais inválidas"}, 401)
        
        elif path == '/api/v1/employees':
            data = self.get_request_data()
            try:
                # Verificar se unique_id já existe
                existing = [emp for emp in db.data["employees"] 
                           if emp.get("unique_id") == data.get("unique_id") and emp.get("is_active", True)]
                
                if existing:
                    self.send_json_response({"detail": f"ID único {data.get('unique_id')} já existe"}, 400)
                    return
                
                new_employee = db.add_employee(data)
                self.send_json_response(new_employee, 201)
                
            except Exception as e:
                self.send_json_response({"detail": f"Erro ao criar colaborador: {str(e)}"}, 400)
        
        elif path == '/api/v1/files/upload':
            # Simular upload de arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_arquivo_teste.pdf"
            
            self.send_json_response({
                "filename": filename,
                "original_name": "arquivo_teste.pdf",
                "file_path": f"uploads/{filename}",
                "size": 1024,
                "upload_time": datetime.now().isoformat()
            })
        
        elif path == '/api/v1/communications/send':
            data = self.get_request_data()
            selected_employees = data.get("selectedEmployees", [])
            message = data.get("message", "")
            uploaded_file = data.get("uploadedFile")
            
            if not message.strip() and not uploaded_file:
                self.send_json_response({"detail": "Mensagem ou arquivo é obrigatório"}, 400)
                return
            
            if not selected_employees:
                self.send_json_response({"detail": "Selecione pelo menos um destinatário"}, 400)
                return
            
            # Inicializar Evolution API
            evolution = EvolutionAPI()
            connection_status = evolution.check_connection()
            
            if not connection_status.get("connected"):
                self.send_json_response({
                    "detail": f"Erro na Evolution API: {connection_status.get('error', 'Não conectado')}"
                }, 500)
                return
            
            success_count = 0
            failed_employees = []
            sent_employees = []
            
            print(f"📤 Iniciando envio de comunicado para {len(selected_employees)} colaboradores...")
            
            for emp_id in selected_employees:
                try:
                    # Buscar dados do colaborador
                    employee = None
                    for emp in db.data["employees"]:
                        if emp["id"] == emp_id and emp.get("is_active", True):
                            employee = emp
                            break
                    
                    if not employee:
                        failed_employees.append({"id": emp_id, "error": "Colaborador não encontrado"})
                        continue
                    
                    phone_number = employee.get("phone_number") or employee.get("phone")
                    if not phone_number:
                        failed_employees.append({
                            "id": emp_id, 
                            "name": employee.get("full_name", ""),
                            "error": "Telefone não informado"
                        })
                        continue
                    
                    # Limpar número (remover caracteres especiais)
                    clean_phone = ''.join(filter(str.isdigit, phone_number))
                    if len(clean_phone) < 10:
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": "Número de telefone inválido"
                        })
                        continue
                    
                    # Garantir formato brasileiro
                    if not clean_phone.startswith('55'):
                        clean_phone = '55' + clean_phone
                    
                    # Enviar mensagem
                    if message.strip():
                        result = evolution.send_message(clean_phone, message)
                        if not result.get("success"):
                            failed_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "error": result.get("error", "Erro desconhecido")
                            })
                            continue
                    
                    # Enviar arquivo se houver
                    if uploaded_file:
                        file_path = uploaded_file.get("file_path", "")
                        if file_path and os.path.exists(file_path):
                            result = evolution.send_file(clean_phone, file_path, message)
                            if not result.get("success"):
                                failed_employees.append({
                                    "id": emp_id,
                                    "name": employee.get("full_name", ""),
                                    "error": f"Erro ao enviar arquivo: {result.get('error', 'Erro desconhecido')}"
                                })
                                continue
                    
                    success_count += 1
                    sent_employees.append({
                        "id": emp_id,
                        "name": employee.get("full_name", ""),
                        "phone": clean_phone
                    })
                    
                    # Delay entre envios para evitar rate limiting
                    if emp_id != selected_employees[-1]:  # Não delay no último
                        time.sleep(random.uniform(2, 4))
                        
                except Exception as e:
                    failed_employees.append({
                        "id": emp_id,
                        "error": f"Erro inesperado: {str(e)}"
                    })
            
            result_message = f"Comunicado enviado para {success_count} colaboradores"
            if failed_employees:
                result_message += f". {len(failed_employees)} falharam."
            
            self.send_json_response({
                "success_count": success_count,
                "total_count": len(selected_employees),
                "failed_employees": failed_employees,
                "sent_employees": sent_employees,
                "message": result_message
            })
        
        elif path == '/api/v1/payrolls/send':
            data = self.get_request_data()
            uploaded_files = data.get("uploadedFiles", [])
            selected_employees = data.get("selectedEmployees", [])
            
            if not uploaded_files:
                self.send_json_response({"detail": "Nenhum arquivo de holerite foi enviado"}, 400)
                return
                
            if not selected_employees:
                self.send_json_response({"detail": "Selecione pelo menos um colaborador"}, 400)
                return
            
            # Inicializar Evolution API
            evolution = EvolutionAPI()
            connection_status = evolution.check_connection()
            
            if not connection_status.get("connected"):
                self.send_json_response({
                    "detail": f"Erro na Evolution API: {connection_status.get('error', 'Não conectado')}"
                }, 500)
                return
            
            success_count = 0
            failed_employees = []
            sent_employees = []
            
            print(f"📋 Iniciando envio de holerites para {len(selected_employees)} colaboradores...")
            
            for emp_id in selected_employees:
                try:
                    # Buscar dados do colaborador
                    employee = None
                    for emp in db.data["employees"]:
                        if emp["id"] == emp_id and emp.get("is_active", True):
                            employee = emp
                            break
                    
                    if not employee:
                        failed_employees.append({"id": emp_id, "error": "Colaborador não encontrado"})
                        continue
                    
                    phone_number = employee.get("phone_number") or employee.get("phone")
                    unique_id = employee.get("unique_id", "")
                    
                    if not phone_number:
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": "Telefone não informado"
                        })
                        continue
                    
                    # Procurar arquivo do holerite para este colaborador
                    employee_file = None
                    for file_info in uploaded_files:
                        filename = file_info.get("filename", "")
                        if unique_id and unique_id.lower() in filename.lower():
                            employee_file = file_info
                            break
                    
                    if not employee_file:
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": f"Holerite não encontrado para ID {unique_id}"
                        })
                        continue
                    
                    # Limpar número de telefone
                    clean_phone = ''.join(filter(str.isdigit, phone_number))
                    if len(clean_phone) < 10:
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": "Número de telefone inválido"
                        })
                        continue
                    
                    if not clean_phone.startswith('55'):
                        clean_phone = '55' + clean_phone
                    
                    # Enviar mensagem personalizada
                    message = f"Olá {employee.get('full_name', '')}, segue seu holerite em anexo."
                    
                    # Enviar arquivo
                    file_path = employee_file.get("file_path", "")
                    if file_path and os.path.exists(file_path):
                        result = evolution.send_file(clean_phone, file_path, message)
                        if result.get("success"):
                            success_count += 1
                            sent_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "phone": clean_phone,
                                "file": employee_file.get("filename", "")
                            })
                        else:
                            failed_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "error": f"Erro ao enviar: {result.get('error', 'Erro desconhecido')}"
                            })
                    else:
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": "Arquivo do holerite não encontrado"
                        })
                    
                    # Delay entre envios
                    if emp_id != selected_employees[-1]:
                        time.sleep(random.uniform(3, 6))  # Delay maior para arquivos
                        
                except Exception as e:
                    failed_employees.append({
                        "id": emp_id,
                        "error": f"Erro inesperado: {str(e)}"
                    })
            
            result_message = f"Holerites enviados para {success_count} colaboradores"
            if failed_employees:
                result_message += f". {len(failed_employees)} falharam."
            
            self.send_json_response({
                "success_count": success_count,
                "total_count": len(selected_employees),
                "failed_employees": failed_employees,
                "sent_employees": sent_employees,
                "message": result_message
            })
        
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path.startswith('/api/v1/employees/'):
            try:
                employee_id = int(path.split('/')[-1])
                data = self.get_request_data()
                
                updated_employee = db.update_employee(employee_id, data)
                
                if updated_employee:
                    self.send_json_response(updated_employee)
                else:
                    self.send_json_response({"error": "Colaborador não encontrado"}, 404)
                    
            except ValueError:
                self.send_json_response({"error": "ID inválido"}, 400)
            except Exception as e:
                self.send_json_response({"detail": f"Erro ao atualizar colaborador: {str(e)}"}, 400)
        
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        path = urllib.parse.urlparse(self.path).path
        
        if path.startswith('/api/v1/employees/'):
            try:
                employee_id = int(path.split('/')[-1])
                
                if db.delete_employee(employee_id):
                    self.send_json_response({"message": "Colaborador removido com sucesso"})
                else:
                    self.send_json_response({"error": "Colaborador não encontrado"}, 404)
                    
            except ValueError:
                self.send_json_response({"error": "ID inválido"}, 400)
        
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)

def main():
    """Função principal"""
    try:
        with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
            print(f"🚀 Sistema RH v2.0")
            print(f"🐍 Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            print(f"📡 Servidor rodando em: http://localhost:{PORT}")
            print(f"📚 API base: http://localhost:{PORT}/api/v1/")
            print(f"👤 Login padrão: admin / admin123")
            print("🔥 Pressione Ctrl+C para parar")
            print("-" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main()