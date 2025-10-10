import axios from 'axios';
import toast from 'react-hot-toast';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8002/api/v1',
  timeout: 30000,
});

// Interceptor para adicionar token nas requisições
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratamento de erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];
      window.location.href = '/login';
    } else if (error.response?.status >= 500) {
      toast.error('Erro interno do servidor. Tente novamente.');
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Tempo limite excedido. Verifique sua conexão.');
    }
    
    return Promise.reject(error);
  }
);

export default api;

// Funções específicas para verificação de saúde
export const healthAPI = {
  // Verificação geral de saúde
  checkHealth: () => api.get('/health', { baseURL: 'http://localhost:8002' }),
  
  // Verificação específica do banco de dados
  checkDatabaseHealth: () => api.get('/database/health'),
  
  // Verificação com timeout menor para detectar problemas rapidamente
  quickHealthCheck: () => api.get('/database/health', { timeout: 5000 })
};
