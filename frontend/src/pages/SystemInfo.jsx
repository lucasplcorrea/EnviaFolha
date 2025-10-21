import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

const SystemInfo = () => {
  const [systemStatus, setSystemStatus] = useState({
    database: { status: 'checking', type: '', version: '' },
    evolution: { status: 'checking', connected: false, instance: '' },
    server: { uptime: '', version: '' }
  });

  const checkSystemStatus = async () => {
    try {
      // Verificar status do banco
      const dbResponse = await fetch('/api/v1/database/health');
      const dbData = await dbResponse.json();
      
      // Verificar Evolution API
      const evolutionResponse = await fetch('/api/v1/evolution/status');
      const evolutionData = await evolutionResponse.json();
      
      // Verificar status do servidor
      const serverResponse = await fetch('/api/v1/system/status');
      const serverData = await serverResponse.json();

      setSystemStatus({
        database: {
          status: dbData.connected ? 'online' : 'offline',
          type: dbData.type,
          version: dbData.version || 'N/A'
        },
        evolution: {
          status: evolutionData.connected ? 'online' : 'offline',
          connected: evolutionData.connected,
          instance: evolutionData.instance || 'N/A'
        },
        server: {
          uptime: serverData.uptime || 'N/A',
          version: serverData.version || '2.0.0'
        }
      });
    } catch (error) {
      console.error('Erro ao verificar status do sistema:', error);
      toast.error('Erro ao verificar status do sistema');
    }
  };

  useEffect(() => {
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 30000); // Atualizar a cada 30 segundos
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <span className="text-green-500">🟢</span>;
      case 'offline':
        return <span className="text-red-500">🔴</span>;
      case 'checking':
        return <span className="text-yellow-500">🟡</span>;
      default:
        return <span className="text-gray-500">⚪</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Informações do Sistema</h2>
        <button
          onClick={checkSystemStatus}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
        >
          🔄 Atualizar Status
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Status do Banco de Dados */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-2 mb-4">
            {getStatusIcon(systemStatus.database.status)}
            <h3 className="text-lg font-semibold">Banco de Dados</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">Status:</span>
              <span className={`ml-2 ${systemStatus.database.status === 'online' ? 'text-green-600' : 'text-red-600'}`}>
                {systemStatus.database.status === 'online' ? 'Online' : 'Offline'}
              </span>
            </div>
            <div>
              <span className="font-medium">Tipo:</span>
              <span className="ml-2">{systemStatus.database.type}</span>
            </div>
            <div>
              <span className="font-medium">Versão:</span>
              <span className="ml-2">{systemStatus.database.version}</span>
            </div>
          </div>
        </div>

        {/* Status da Evolution API */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-2 mb-4">
            {getStatusIcon(systemStatus.evolution.status)}
            <h3 className="text-lg font-semibold">WhatsApp API</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">Status:</span>
              <span className={`ml-2 ${systemStatus.evolution.connected ? 'text-green-600' : 'text-red-600'}`}>
                {systemStatus.evolution.connected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
            <div>
              <span className="font-medium">Instância:</span>
              <span className="ml-2">{systemStatus.evolution.instance}</span>
            </div>
          </div>
        </div>

        {/* Status do Servidor */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-green-500">🟢</span>
            <h3 className="text-lg font-semibold">Servidor</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">Status:</span>
              <span className="ml-2 text-green-600">Online</span>
            </div>
            <div>
              <span className="font-medium">Versão:</span>
              <span className="ml-2">{systemStatus.server.version}</span>
            </div>
            <div>
              <span className="font-medium">Tempo Ativo:</span>
              <span className="ml-2">{systemStatus.server.uptime}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Informações Adicionais */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="text-lg font-semibold mb-4">Informações do Sistema</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium">Nome do Sistema:</span>
            <span className="ml-2">Sistema de Envio RH v2.0</span>
          </div>
          <div>
            <span className="font-medium">Última Verificação:</span>
            <span className="ml-2">{new Date().toLocaleString('pt-BR')}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemInfo;