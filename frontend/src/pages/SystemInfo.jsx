import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

const SystemInfo = () => {
  const [systemStatus, setSystemStatus] = useState({
    database: { status: 'checking', type: '', version: '' },
    evolution: { instances: [], total: 0, connected: 0, has_multiple: false },
    server: { uptime: '', version: '' }
  });

  const checkSystemStatus = async () => {
    try {
      // Verificar status do banco
      const dbResponse = await fetch('/api/v1/database/health');
      const dbData = await dbResponse.json();
      
      // Verificar Evolution API (multi-instância)
      const evolutionResponse = await fetch('/api/v1/evolution/instances');
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
          instances: evolutionData.instances || [],
          total: evolutionData.total || 0,
          connected: evolutionData.connected || 0,
          has_multiple: evolutionData.has_multiple || false
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
      case 'connected':
        return <span className="text-green-500">🟢</span>;
      case 'offline':
      case 'disconnected':
        return <span className="text-red-500">🔴</span>;
      case 'checking':
      case 'timeout':
        return <span className="text-yellow-500">🟡</span>;
      default:
        return <span className="text-gray-500">⚪</span>;
    }
  };

  const formatTimeSinceLastSend = (seconds) => {
    if (seconds === null || seconds === undefined) {
      return 'Nunca utilizada';
    }
    if (seconds < 60) {
      return `${Math.floor(seconds)}s atrás`;
    }
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
      return `${minutes}min atrás`;
    }
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}min atrás`;
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

        {/* Status da Evolution API - Multi-Instâncias */}
        {systemStatus.evolution.instances.length > 0 ? (
          systemStatus.evolution.instances.map((instance, index) => (
            <div key={instance.name} className="bg-white p-6 rounded-lg shadow-sm border">
              <div className="flex items-center gap-2 mb-4">
                {getStatusIcon(instance.status)}
                <h3 className="text-lg font-semibold">
                  WhatsApp {systemStatus.evolution.has_multiple ? `#${index + 1}` : ''}
                </h3>
              </div>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Status:</span>
                  <span className={`ml-2 ${instance.status === 'connected' ? 'text-green-600' : instance.status === 'timeout' ? 'text-yellow-600' : 'text-red-600'}`}>
                    {instance.status === 'connected' ? 'Conectado' : instance.status === 'timeout' ? 'Timeout' : 'Desconectado'}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Instância:</span>
                  <span className="ml-2">{instance.name}</span>
                </div>
                <div>
                  <span className="font-medium">Pronta:</span>
                  <span className={`ml-2 ${instance.ready ? 'text-green-600' : 'text-yellow-600'}`}>
                    {instance.ready ? 'Sim' : 'Aguardando'}
                  </span>
                </div>
                {instance.seconds_since_last_send !== null && (
                  <div>
                    <span className="font-medium">Último envio:</span>
                    <span className="ml-2 text-gray-600">
                      {formatTimeSinceLastSend(instance.seconds_since_last_send)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-gray-500">⚪</span>
              <h3 className="text-lg font-semibold">WhatsApp API</h3>
            </div>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Status:</span>
                <span className="ml-2 text-gray-600">Carregando...</span>
              </div>
            </div>
          </div>
        )}

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

      {/* Resumo Multi-Instâncias (se tiver mais de uma) */}
      {systemStatus.evolution.has_multiple && (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">📊</span>
            <h3 className="text-lg font-semibold text-blue-900">Resumo Multi-Instâncias</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mt-4">
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <span className="font-medium text-gray-700">Total de Instâncias:</span>
              <span className="ml-2 text-xl font-bold text-blue-600">{systemStatus.evolution.total}</span>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <span className="font-medium text-gray-700">Conectadas:</span>
              <span className="ml-2 text-xl font-bold text-green-600">{systemStatus.evolution.connected}</span>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <span className="font-medium text-gray-700">Desconectadas:</span>
              <span className="ml-2 text-xl font-bold text-red-600">
                {systemStatus.evolution.total - systemStatus.evolution.connected}
              </span>
            </div>
          </div>
          <div className="mt-4 text-sm text-blue-800">
            <p>ℹ️ O sistema distribui os envios em round-robin entre as instâncias conectadas para evitar softban.</p>
          </div>
        </div>
      )}

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