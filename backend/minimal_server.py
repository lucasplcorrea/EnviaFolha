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
            
            print(f"📞 Enviando mensagem para {phone_number}")
            print(f"   - URL: {url}")
            print(f"   - Headers: {self.headers}")
            print(f"   - Data: {data}")
            
            # Fazer request real para Evolution API
            import urllib.request
            import urllib.error
            
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                print(f"✅ Resposta da API: {response_data}")
                return {"success": True, "message": "Mensagem enviada com sucesso", "response": response_data}
                
        except urllib.error.HTTPError as e:
            error_message = e.read().decode('utf-8') if e.fp else str(e)
            print(f"❌ Erro HTTP {e.code}: {error_message}")
            return {"success": False, "error": f"HTTP {e.code}: {error_message}"}
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_file(self, phone_number, file_path, caption=""):
        """Envia arquivo"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "Arquivo não encontrado"}
            
            # Usar endpoint correto para mídia
            url = f"{self.server_url}/message/sendMedia/{self.instance_name}"
            
            # Converter arquivo para base64
            import base64
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            
            # Detectar tipo MIME
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Formato correto para Evolution API v2 - base64 puro
            data = {
                "number": phone_number,
                "media": file_content,  # Base64 puro, sem prefixo data:
                "mediatype": "image" if mime_type.startswith('image/') else "document",
                "fileName": os.path.basename(file_path),
                "mimeType": mime_type
            }
            
            # Adicionar caption se fornecido
            if caption.strip():
                data["caption"] = caption
            
            print(f"📎 Enviando arquivo para {phone_number}: {os.path.basename(file_path)}")
            print(f"   - URL: {url}")
            print(f"   - MIME Type: {mime_type}")
            print(f"   - Media Type: {data['mediatype']}")
            print(f"   - Tamanho do base64: {len(data['media'])} chars")
            print(f"   - Estrutura dos dados: {list(data.keys())}")
            
            # Fazer request real
            import urllib.request
            import urllib.error
            
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=json_data, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                print(f"✅ Arquivo enviado: {response_data}")
                return {"success": True, "message": "Arquivo enviado com sucesso", "response": response_data}
                
        except urllib.error.HTTPError as e:
            error_message = e.read().decode('utf-8') if e.fp else str(e)
            print(f"❌ Erro HTTP {e.code} ao enviar arquivo: {error_message}")
            return {"success": False, "error": f"HTTP {e.code}: {error_message}"}
        except Exception as e:
            print(f"❌ Erro ao enviar arquivo: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_connection(self):
        """Verifica conexão com a API"""
        if not all([self.server_url, self.api_key, self.instance_name]):
            missing = []
            if not self.server_url: missing.append("EVOLUTION_SERVER_URL")
            if not self.api_key: missing.append("EVOLUTION_API_KEY") 
            if not self.instance_name: missing.append("EVOLUTION_INSTANCE_NAME")
            return {"connected": False, "error": f"Configurações faltando: {', '.join(missing)}"}
        
        try:
            # Testar conectividade básica
            url = f"{self.server_url}/instance/connectionState/{self.instance_name}"
            req = urllib.request.Request(url, headers={"apikey": self.api_key})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status_data = json.loads(response.read().decode('utf-8'))
                print(f"🔗 Status da instância: {status_data}")
                return {"connected": True, "instance": self.instance_name, "status": status_data}
                
        except Exception as e:
            print(f"⚠️  Não foi possível verificar status da instância: {str(e)}")
            # Mesmo assim retorna connected=True se as configurações existem
            return {"connected": True, "instance": self.instance_name, "warning": str(e)}

# Configurações
PORT = 8002
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
ENVIADOS_DIR = os.path.join(os.getcwd(), "enviados")
DATA_FILE = "employees.json"

# Criar diretórios necessários
for directory in [UPLOAD_DIR, ENVIADOS_DIR]:
    os.makedirs(directory, exist_ok=True)
    print(f"📁 Diretório criado/verificado: {directory}")

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
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        print(f"🔧 OPTIONS recebido: {self.path}")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, apikey')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
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
                # Verificar status real da Evolution API
                try:
                    evolution = EvolutionAPI()
                    connection_status = evolution.check_connection()
                    
                    if connection_status.get("connected"):
                        instance_status = connection_status.get("status", {}).get("instance", {})
                        instance_state = instance_status.get("state", "unknown")
                        
                        self.send_json_response({
                            "connected": True,
                            "instance_name": instance_name,
                            "server_url": server_url,
                            "state": instance_state,
                            "config": {
                                "server_url": bool(server_url),
                                "api_key": bool(api_key),
                                "instance_name": bool(instance_name)
                            }
                        })
                    else:
                        self.send_json_response({
                            "connected": False,
                            "error": connection_status.get("error", "Erro desconhecido"),
                            "state": "disconnected",
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
                        "state": "error",
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
        print(f"🔥 POST recebido: {path}")
        
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
            print("📤 Requisição de upload de arquivo recebida")
            
            try:
                # Verificar se a requisição tem multipart/form-data
                content_type = self.headers.get('Content-Type', '')
                print(f"   - Content-Type: {content_type}")
                
                if not content_type.startswith('multipart/form-data'):
                    print("❌ Content-Type deve ser multipart/form-data")
                    self.send_json_response({"detail": "Content-Type deve ser multipart/form-data"}, 400)
                    return
                
                # Obter o boundary do multipart
                boundary = content_type.split('boundary=')[1] if 'boundary=' in content_type else None
                if not boundary:
                    print("❌ Boundary não encontrado")
                    self.send_json_response({"detail": "Boundary não encontrado"}, 400)
                    return
                
                # Ler o conteúdo da requisição
                content_length = int(self.headers.get('Content-Length', 0))
                print(f"   - Content-Length: {content_length}")
                
                if content_length == 0:
                    print("❌ Nenhum arquivo enviado")
                    self.send_json_response({"detail": "Nenhum arquivo enviado"}, 400)
                    return
                
                # Ler dados do arquivo
                post_data = self.rfile.read(content_length)
                print(f"   - Dados recebidos: {len(post_data)} bytes")
                
                # Processar multipart data (implementação simples)
                boundary_bytes = boundary.encode()
                parts = post_data.split(b'--' + boundary_bytes)
                
                file_data = None
                filename = None
                
                for part in parts:
                    if b'Content-Disposition: form-data' in part and b'filename=' in part:
                        # Extrair nome do arquivo
                        lines = part.split(b'\r\n')
                        for line in lines:
                            if b'filename=' in line:
                                filename_match = line.decode().split('filename="')[1].split('"')[0]
                                filename = filename_match
                                break
                        
                        # Extrair dados do arquivo (após headers)
                        if b'\r\n\r\n' in part:
                            file_data = part.split(b'\r\n\r\n', 1)[1]
                            # Remover \r\n do final se existir
                            if file_data.endswith(b'\r\n'):
                                file_data = file_data[:-2]
                            break
                
                if not file_data or not filename:
                    print("❌ Arquivo não encontrado nos dados")
                    self.send_json_response({"detail": "Arquivo não encontrado nos dados"}, 400)
                    return
                
                # Gerar nome único para o arquivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = os.path.splitext(filename)[1]
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(UPLOAD_DIR, unique_filename)
                
                # Salvar arquivo
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                
                print(f"✅ Arquivo salvo: {file_path} ({len(file_data)} bytes)")
                
                self.send_json_response({
                    "filename": unique_filename,
                    "original_name": filename,
                    "file_path": file_path,
                    "size": len(file_data),
                    "upload_time": datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ Erro no upload: {str(e)}")
                self.send_json_response({"detail": f"Erro no upload: {str(e)}"}, 500)
        
        elif path == '/api/v1/communications/send':
            data = self.get_request_data()
            print(f"📤 Requisição de envio de comunicado recebida:")
            print(f"   - Dados: {data}")
            
            selected_employees = data.get("selectedEmployees", [])
            message = data.get("message", "")
            uploaded_file = data.get("uploadedFile")
            
            print(f"   - Colaboradores selecionados: {selected_employees}")
            print(f"   - Mensagem: '{message}'")
            print(f"   - Arquivo: {uploaded_file}")
            
            if not message.strip() and not uploaded_file:
                print("❌ Erro: Mensagem ou arquivo é obrigatório")
                self.send_json_response({"detail": "Mensagem ou arquivo é obrigatório"}, 400)
                return
            
            if not selected_employees:
                print("❌ Erro: Nenhum colaborador selecionado")
                self.send_json_response({"detail": "Selecione pelo menos um destinatário"}, 400)
                return
            
            # Inicializar Evolution API
            print("🔌 Inicializando Evolution API...")
            evolution = EvolutionAPI()
            print(f"   - Server URL: {evolution.server_url}")
            print(f"   - API Key: {'***' if evolution.api_key else 'Não configurado'}")
            print(f"   - Instance: {evolution.instance_name}")
            
            connection_status = evolution.check_connection()
            print(f"   - Status de conexão: {connection_status}")
            
            if not connection_status.get("connected"):
                print(f"❌ Erro na Evolution API: {connection_status.get('error', 'Não conectado')}")
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
                    
                    # Lógica de envio baseada no que foi preenchido
                    has_message = message.strip()
                    has_file = uploaded_file and uploaded_file.get("file_path") and os.path.exists(uploaded_file.get("file_path", ""))
                    
                    print(f"   - Tem mensagem: {has_message}")
                    print(f"   - Tem arquivo: {has_file}")
                    
                    if has_file and has_message:
                        # Caso 3: Texto + arquivo → Enviar arquivo com caption (texto)
                        print("   - Enviando arquivo com caption (texto + mídia)")
                        file_path = uploaded_file.get("file_path", "")
                        result = evolution.send_file(clean_phone, file_path, message)
                        if not result.get("success"):
                            failed_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "error": f"Erro ao enviar arquivo com caption: {result.get('error', 'Erro desconhecido')}"
                            })
                            continue
                            
                    elif has_file and not has_message:
                        # Caso 2: Só arquivo → Enviar apenas arquivo (sem caption)
                        print("   - Enviando apenas arquivo (sem caption)")
                        file_path = uploaded_file.get("file_path", "")
                        result = evolution.send_file(clean_phone, file_path, "")
                        if not result.get("success"):
                            failed_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "error": f"Erro ao enviar arquivo: {result.get('error', 'Erro desconhecido')}"
                            })
                            continue
                            
                    elif has_message and not has_file:
                        # Caso 1: Só texto → Enviar apenas mensagem de texto
                        print("   - Enviando apenas mensagem de texto")
                        result = evolution.send_message(clean_phone, message)
                        if not result.get("success"):
                            failed_employees.append({
                                "id": emp_id,
                                "name": employee.get("full_name", ""),
                                "error": result.get("error", "Erro desconhecido")
                            })
                            continue
                    else:
                        # Não deveria chegar aqui devido à validação anterior
                        failed_employees.append({
                            "id": emp_id,
                            "name": employee.get("full_name", ""),
                            "error": "Nenhum conteúdo para enviar"
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