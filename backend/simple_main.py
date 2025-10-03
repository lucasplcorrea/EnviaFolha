from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import json
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração com .env
class Settings:
    APP_NAME = "Sistema de Envio RH"
    VERSION = "2.0.0"
    DATABASE_FILE = "employees.json"  # Arquivo unificado
    
    # Evolution API
    EVOLUTION_SERVER_URL = os.getenv("EVOLUTION_SERVER_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")
    
    # Configurações de upload
    UPLOAD_FOLDER = "uploads"
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

settings = Settings()

# Modelos Pydantic simples
class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    is_admin: bool

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class Employee(BaseModel):
    id: Optional[int] = None
    unique_id: str
    full_name: str
    phone_number: str
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None

# "Banco de dados" em arquivo JSON
class SimpleDB:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "users": [
                {
                    "id": 1,
                    "username": "admin",
                    "password": "admin123",  # Em produção, usar hash
                    "full_name": "Administrador",
                    "email": "admin@empresa.com",
                    "is_admin": True
                }
            ],
            "employees": []
        }
    
    def save_data(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_user_by_username(self, username: str):
        for user in self.data["users"]:
            if user["username"] == username:
                return user
        return None
    
    def get_employees(self):
        return [emp for emp in self.data["employees"] if emp.get("is_active", True)]
    
    def add_employee(self, employee_data: dict):
        new_id = max([emp.get("id", 0) for emp in self.data["employees"]], default=0) + 1
        employee_data["id"] = new_id
        employee_data["created_at"] = datetime.now().isoformat()
        self.data["employees"].append(employee_data)
        self.save_data()
        return employee_data

# Inicializar "banco de dados"
db = SimpleDB(settings.DATABASE_FILE)

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sistema completo para envio de holerites e comunicados via WhatsApp (Versão Simplificada)"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Criar diretórios necessários
os.makedirs("uploads", exist_ok=True)

# Servir arquivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    """Endpoint de teste"""
    try:
        import pandas as pd
        pandas_info = f"✅ pandas {pd.__version__}"
    except ImportError:
        pandas_info = "❌ pandas não disponível"
    
    try:
        import numpy as np
        numpy_info = f"✅ numpy {np.__version__}"
    except ImportError:
        numpy_info = "❌ numpy não disponível"
    
    return {
        "message": f"{settings.APP_NAME} v{settings.VERSION}",
        "status": "running",
        "docs": "/docs",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "dependencies": {
            "fastapi": "✅ Funcionando",
            "pandas": pandas_info,
            "numpy": numpy_info
        },
        "note": "Versão simplificada sem SQLAlchemy"
    }

@app.post("/api/v1/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Endpoint de login"""
    user = db.get_user_by_username(user_credentials.username)
    
    if not user or user["password"] != user_credentials.password:
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
        )
    
    user_response = UserResponse(
        id=user["id"],
        username=user["username"],
        full_name=user["full_name"],
        email=user["email"],
        is_admin=user["is_admin"]
    )
    
    return Token(
        access_token="simple-token-" + str(user["id"]),
        token_type="bearer",
        user=user_response
    )

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info():
    """Obter informações do usuário atual (simulado)"""
    return UserResponse(
        id=1,
        username="admin",
        full_name="Administrador",
        email="admin@empresa.com",
        is_admin=True
    )

@app.get("/api/v1/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "database": "JSON file",
        "employees_count": len(db.get_employees())
    }

@app.get("/api/v1/employees", response_model=List[Employee])
async def list_employees():
    """Listar colaboradores"""
    return db.get_employees()

@app.post("/api/v1/employees", response_model=Employee)
async def create_employee(employee: Employee):
    """Criar novo colaborador"""
    try:
        # Verificar se unique_id já existe
        existing = [emp for emp in db.data["employees"] if emp.get("unique_id") == employee.unique_id and emp.get("is_active", True)]
        if existing:
            raise HTTPException(status_code=400, detail=f"ID único {employee.unique_id} já existe")
        
        employee_data = employee.dict()
        new_employee = db.add_employee(employee_data)
        
        return Employee(**new_employee)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao criar colaborador: {str(e)}")

@app.get("/api/v1/employees/{employee_id}")
async def get_employee(employee_id: int):
    """Obter colaborador por ID"""
    for emp in db.data["employees"]:
        if emp.get("id") == employee_id and emp.get("is_active", True):
            return emp
    
    raise HTTPException(status_code=404, detail="Colaborador não encontrado")

@app.delete("/api/v1/employees/{employee_id}")
async def delete_employee(employee_id: int):
    """Excluir colaborador (soft delete)"""
    for emp in db.data["employees"]:
        if emp.get("id") == employee_id:
            emp["is_active"] = False
            db.save_data()
            return {"message": "Colaborador removido com sucesso"}
    
    raise HTTPException(status_code=404, detail="Colaborador não encontrado")

@app.get("/api/v1/test/pandas")
async def test_pandas():
    """Testar se pandas está funcionando"""
    try:
        import pandas as pd
        import numpy as np
        
        # Criar um DataFrame de teste
        data = {
            'nome': ['João', 'Maria', 'Pedro'],
            'telefone': ['11999999999', '11888888888', '11777777777'],
            'departamento': ['TI', 'RH', 'Vendas']
        }
        df = pd.DataFrame(data)
        
        return {
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "test_dataframe": df.to_dict('records'),
            "status": "✅ Pandas funcionando perfeitamente!"
        }
    
    except ImportError as e:
        return {
            "error": str(e),
            "status": "❌ Pandas não disponível"
        }

# Adicionar novos endpoints para Evolution API
@app.get("/api/v1/evolution/status")
async def check_evolution_status():
    """Verificar status da Evolution API"""
    if not all([settings.EVOLUTION_SERVER_URL, settings.EVOLUTION_API_KEY, settings.EVOLUTION_INSTANCE_NAME]):
        return {
            "connected": False,
            "error": "Configurações da Evolution API não encontradas no .env",
            "config": {
                "server_url": bool(settings.EVOLUTION_SERVER_URL),
                "api_key": bool(settings.EVOLUTION_API_KEY),
                "instance_name": bool(settings.EVOLUTION_INSTANCE_NAME)
            }
        }
    
    try:
        url = f"{settings.EVOLUTION_SERVER_URL.rstrip('/')}/instance/connectionState/{settings.EVOLUTION_INSTANCE_NAME}"
        headers = {"apikey": settings.EVOLUTION_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        instance_state = result.get('instance', {}).get('state', 'unknown')
        
        return {
            "connected": instance_state in ['open', 'connected'],
            "state": instance_state,
            "instance_name": settings.EVOLUTION_INSTANCE_NAME,
            "server_url": settings.EVOLUTION_SERVER_URL
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "connected": False,
            "error": f"Erro de conexão: {str(e)}",
            "server_url": settings.EVOLUTION_SERVER_URL
        }

@app.post("/api/v1/employees/import")
async def import_employees_from_excel(file: UploadFile = File(...)):
    """Importar colaboradores de planilha Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Arquivo deve ser Excel (.xlsx ou .xls)")
    
    try:
        # Salvar arquivo temporariamente
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Ler planilha
        df = pd.read_excel(temp_path)
        
        # Validar colunas obrigatórias
        required_columns = ['unique_id', 'full_name', 'phone_number']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            os.remove(temp_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}"
            )
        
        # Processar dados
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                employee_data = {
                    "unique_id": str(row['unique_id']).strip(),
                    "full_name": str(row['full_name']).strip(),
                    "phone_number": str(row['phone_number']).strip(),
                    "email": str(row.get('email', '')).strip() if pd.notna(row.get('email')) else '',
                    "department": str(row.get('department', '')).strip() if pd.notna(row.get('department')) else '',
                    "position": str(row.get('position', '')).strip() if pd.notna(row.get('position')) else '',
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
                
                # Verificar se já existe
                existing = [emp for emp in db.data["employees"] 
                           if emp.get("unique_id") == employee_data["unique_id"] and emp.get("is_active", True)]
                
                if existing:
                    errors.append(f"Linha {index + 2}: ID {employee_data['unique_id']} já existe")
                    continue
                
                # Adicionar ao banco
                new_id = max([emp.get("id", 0) for emp in db.data["employees"]], default=0) + 1
                employee_data["id"] = new_id
                db.data["employees"].append(employee_data)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Linha {index + 2}: {str(e)}")
        
        # Salvar alterações
        db.save_data()
        
        # Remover arquivo temporário
        os.remove(temp_path)
        
        return {
            "imported": imported_count,
            "errors": errors,
            "total_rows": len(df)
        }
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivo: {str(e)}")

@app.post("/api/v1/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload de arquivos (holerites, comunicados)"""
    try:
        # Criar pasta uploads se não existir
        os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
        
        # Gerar nome único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_FOLDER, filename)
        
        # Salvar arquivo
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "filename": filename,
            "original_name": file.filename,
            "file_path": file_path,
            "size": len(content),
            "upload_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro no upload: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Sistema RH v{settings.VERSION}")
    print(f"🐍 Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("📡 Servidor: http://localhost:8000")
    print("📚 Documentação: http://localhost:8000/docs")
    print("🧪 Teste pandas: http://localhost:8000/api/v1/test/pandas")
    print("🔥 Iniciando servidor...")
    
    try:
        uvicorn.run(
            "simple_main:app",  # Usar string para evitar warning
            host="0.0.0.0",
            port=8000,
            reload=False,  # Desabilitar reload para evitar problemas
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        print("💡 Tente executar: uvicorn simple_main:app --host 0.0.0.0 --port 8000")
