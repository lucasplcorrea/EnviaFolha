"""
Base Router - Classe base para todos os routers com funcionalidades compartilhadas
"""
import json
from typing import Any, Dict


class BaseRouter:
    """Classe base com métodos auxiliares para routers"""
    
    def __init__(self, handler):
        """
        Args:
            handler: Instância do RequestHandler do http.server
        """
        self.handler = handler
    
    def send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """Enviar resposta JSON"""
        try:
            self.handler.send_response(status_code)
            self.handler.send_header('Content-type', 'application/json')
            self.handler.send_header('Access-Control-Allow-Origin', '*')
            self.handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.handler.end_headers()
            
            response = json.dumps(data, ensure_ascii=False, default=str)
            self.handler.wfile.write(response.encode('utf-8'))
        except Exception as e:
            print(f"❌ Erro ao enviar resposta JSON: {e}")
    
    def get_request_data(self) -> Dict[str, Any]:
        """Ler dados JSON do corpo da requisição"""
        try:
            content_length = int(self.handler.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            
            post_data = self.handler.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except Exception as e:
            print(f"❌ Erro ao ler dados da requisição: {e}")
            return {}
    
    def send_error(self, message: str, status_code: int = 400):
        """Enviar resposta de erro"""
        self.send_json_response({"error": message}, status_code)
    
    def send_success(self, message: str, data: Dict[str, Any] = None):
        """Enviar resposta de sucesso"""
        response = {"success": True, "message": message}
        if data:
            response.update(data)
        self.send_json_response(response)
