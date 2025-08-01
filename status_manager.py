import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

class StatusManager:
    """Gerenciador de status para controle de execução e acompanhamento"""
    
    def __init__(self, status_file: str = "execution_status.json"):
        self.status_file = status_file
        self.lock = threading.Lock()
        self._initialize_status()
    
    def _initialize_status(self):
        """Inicializa o arquivo de status se não existir"""
        if not os.path.exists(self.status_file):
            initial_status = {
                "is_running": False,
                "start_time": None,
                "end_time": None,
                "current_step": None,
                "total_employees": 0,
                "processed_employees": 0,
                "successful_sends": 0,
                "failed_sends": 0,
                "current_employee": None,
                "employees_status": {},
                "last_update": None,
                "execution_id": None
            }
            self._save_status(initial_status)
    
    def _load_status(self) -> Dict:
        """Carrega o status atual do arquivo"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_status()
            return self._load_status()
    
    def _save_status(self, status: Dict):
        """Salva o status no arquivo"""
        status["last_update"] = datetime.now().isoformat()
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    
    def start_execution(self, total_employees: int, execution_id: str = None) -> bool:
        """
        Inicia uma nova execução
        Retorna False se já houver uma execução em andamento
        """
        with self.lock:
            status = self._load_status()
            
            if status["is_running"]:
                return False
            
            status.update({
                "is_running": True,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "current_step": "Iniciando execução",
                "total_employees": total_employees,
                "processed_employees": 0,
                "successful_sends": 0,
                "failed_sends": 0,
                "current_employee": None,
                "employees_status": {},
                "execution_id": execution_id or datetime.now().strftime("%Y%m%d_%H%M%S")
            })
            
            self._save_status(status)
            return True
    
    def end_execution(self):
        """Finaliza a execução atual"""
        with self.lock:
            status = self._load_status()
            status.update({
                "is_running": False,
                "end_time": datetime.now().isoformat(),
                "current_step": "Execução finalizada",
                "current_employee": None
            })
            self._save_status(status)
    
    def update_current_step(self, step: str, employee_name: str = None):
        """Atualiza o passo atual da execução"""
        with self.lock:
            status = self._load_status()
            status["current_step"] = step
            if employee_name:
                status["current_employee"] = employee_name
            self._save_status(status)
    
    def update_employee_status(self, employee_id: str, employee_name: str, 
                             phone: str, status_type: str, message: str = ""):
        """
        Atualiza o status de um funcionário específico
        status_type: 'processing', 'success', 'failed'
        """
        with self.lock:
            status = self._load_status()
            
            status["employees_status"][employee_id] = {
                "name": employee_name,
                "phone": phone,
                "status": status_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            if status_type == "success":
                status["successful_sends"] += 1
            elif status_type == "failed":
                status["failed_sends"] += 1
            
            status["processed_employees"] = len([
                emp for emp in status["employees_status"].values() 
                if emp["status"] in ["success", "failed"]
            ])
            
            self._save_status(status)
    
    def get_status(self) -> Dict:
        """Retorna o status atual"""
        return self._load_status()
    
    def is_running(self) -> bool:
        """Verifica se há uma execução em andamento"""
        return self._load_status()["is_running"]
    
    def get_progress_percentage(self) -> float:
        """Retorna a porcentagem de progresso"""
        status = self._load_status()
        if status["total_employees"] == 0:
            return 0.0
        return (status["processed_employees"] / status["total_employees"]) * 100
    
    def get_employees_by_status(self, status_type: str) -> List[Dict]:
        """Retorna lista de funcionários por status"""
        status = self._load_status()
        return [
            emp for emp in status["employees_status"].values()
            if emp["status"] == status_type
        ]
    
    def reset_status(self):
        """Reseta o status para o estado inicial"""
        with self.lock:
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            self._initialize_status()

