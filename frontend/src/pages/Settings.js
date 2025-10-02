import React from 'react';

const Settings = () => {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Configurações</h1>
      
      <div className="space-y-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            🔗 Evolution API
          </h2>
          <p className="text-gray-600 mb-4">
            Configure suas credenciais da Evolution API para envio via WhatsApp.
          </p>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600">
              <strong>Status:</strong> Não configurado
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Configure no arquivo .env do backend
            </p>
          </div>
        </div>
        
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            🔐 Segurança
          </h2>
          <p className="text-gray-600">
            Configurações de segurança e autenticação do sistema.
          </p>
        </div>
        
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            📁 Backup
          </h2>
          <p className="text-gray-600">
            Sistema de backup automático e recuperação de dados.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Settings;
