import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';

const Settings = () => {
  const [evolutionStatus, setEvolutionStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkEvolutionStatus();
  }, []);

  const checkEvolutionStatus = async () => {
    try {
      const response = await api.get('/evolution/status');
      setEvolutionStatus(response.data);
    } catch (error) {
      toast.error('Erro ao verificar status da Evolution API');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Configurações</h1>
      
      <div className="space-y-6">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">
              🔗 Evolution API
            </h2>
            <button
              onClick={checkEvolutionStatus}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              {loading ? 'Verificando...' : 'Verificar Status'}
            </button>
          </div>
          
          <p className="text-gray-600 mb-4">
            Configure suas credenciais da Evolution API para envio via WhatsApp.
          </p>
          
          {loading ? (
            <div className="flex items-center">
              <div className="spinner w-5 h-5 mr-2"></div>
              <span className="text-sm text-gray-600">Verificando conexão...</span>
            </div>
          ) : evolutionStatus ? (
            <div className="space-y-3">
              <div className="flex items-center">
                {evolutionStatus.connected ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                ) : (
                  <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                )}
                <span className={`text-sm font-medium ${
                  evolutionStatus.connected ? 'text-green-700' : 'text-red-700'
                }`}>
                  {evolutionStatus.connected ? 'Conectado' : 'Desconectado'}
                </span>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Servidor:</span>
                  <span className="text-gray-900 font-mono">
                    {evolutionStatus.server_url || 'Não configurado'}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Instância:</span>
                  <span className="text-gray-900 font-mono">
                    {evolutionStatus.instance_name || 'Não configurado'}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Estado:</span>
                  <span className="text-gray-900">
                    {evolutionStatus.state || 'Desconhecido'}
                  </span>
                </div>
                
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">API Key:</span>
                  <span className="text-gray-900">
                    {evolutionStatus.config?.api_key ? '✓ Configurada' : '✗ Não configurada'}
                  </span>
                </div>
              </div>
              
              {evolutionStatus.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-700">
                    <strong>Erro:</strong> {evolutionStatus.error}
                  </p>
                </div>
              )}
              
              {!evolutionStatus.connected && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    <strong>Configure no arquivo backend/.env:</strong>
                  </p>
                  <pre className="text-xs text-yellow-700 mt-2 font-mono">
{`EVOLUTION_SERVER_URL=https://sua-api.evolution.com
EVOLUTION_API_KEY=sua_chave_de_api
EVOLUTION_INSTANCE_NAME=nome_da_instancia`}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">
                Erro ao verificar status da Evolution API
              </p>
            </div>
          )}
        </div>
        
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            🔐 Segurança
          </h2>
          <p className="text-gray-600">
            Configurações de segurança e autenticação do sistema.
          </p>
          <div className="mt-4 bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">
              <strong>Usuário atual:</strong> admin<br />
              <strong>Permissões:</strong> Administrador<br />
              <strong>Última sessão:</strong> Ativa
            </p>
          </div>
        </div>
        
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            📁 Sistema
          </h2>
          <p className="text-gray-600">
            Informações do sistema e banco de dados.
          </p>
          <div className="mt-4 bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">
              <strong>Versão:</strong> 2.0.0<br />
              <strong>Banco de dados:</strong> JSON (simple_db.json)<br />
              <strong>Backend:</strong> FastAPI + Python<br />
              <strong>Frontend:</strong> React + Tailwind CSS
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
