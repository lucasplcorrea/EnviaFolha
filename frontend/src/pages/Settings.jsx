import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../contexts/ThemeContext';
import ThemeSelector from '../components/ThemeSelector';
import UserManagement from './UserManagement';
import SystemInfo from './SystemInfo';
import toast from 'react-hot-toast';
import api from '../services/api';

const Settings = () => {
  const [evolutionStatus, setEvolutionStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('general');
  const { config } = useTheme();

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

  const tabs = [
    { id: 'general', name: 'Geral', icon: '⚙️' },
    { id: 'users', name: 'Usuários', icon: '👥' },
    { id: 'system', name: 'Sistema', icon: '🖥️' }
  ];

  const renderGeneralSettings = () => (
    <div className="space-y-6">
      {/* Configurações de Tema */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-lg font-medium ${config.classes.text}`}>
            🎨 Tema da Interface
          </h2>
        </div>
        
        <p className={`${config.classes.textSecondary} mb-4`}>
          Escolha o tema que melhor se adapta ao seu ambiente de trabalho.
        </p>
        
        <div className="flex flex-col space-y-4">
          <div className="flex items-center justify-between">
            <span className={`text-sm ${config.classes.text}`}>Selecionar Tema:</span>
            <ThemeSelector />
          </div>
          <div className={`text-xs ${config.classes.textSecondary}`}>
            O tema selecionado será aplicado imediatamente a toda a interface.
          </div>
        </div>
      </div>

      {/* Status da Evolution API */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-lg font-medium ${config.classes.text}`}>
            📱 WhatsApp Integration (Evolution API)
          </h2>
          {!loading && (
            <button
              onClick={checkEvolutionStatus}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              🔄 Verificar novamente
            </button>
          )}
        </div>
        
        {loading ? (
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className={config.classes.textSecondary}>Verificando status...</span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              {evolutionStatus?.connected ? (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              ) : (
                <XCircleIcon className="h-5 w-5 text-red-500" />
              )}
              <span className={`font-medium ${evolutionStatus?.connected ? 'text-green-700' : 'text-red-700'}`}>
                {evolutionStatus?.connected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
            
            {evolutionStatus?.instance && (
              <div className={`text-sm ${config.classes.textSecondary}`}>
                <strong>Instância:</strong> {evolutionStatus.instance}
              </div>
            )}
            
            {evolutionStatus?.message && (
              <div className={`text-sm ${config.classes.textSecondary}`}>
                {evolutionStatus.message}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Informações da Sessão */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <h2 className={`text-lg font-medium ${config.classes.text} mb-4`}>
          👤 Sessão Atual
        </h2>
        <div className={`${config.classes.background === 'bg-white' ? 'bg-gray-50' : config.classes.surface} rounded-lg p-4`}>
          <p className={`text-sm ${config.classes.textSecondary}`}>
            <strong>Usuário atual:</strong> admin<br />
            <strong>Permissões:</strong> Administrador<br />
            <strong>Última sessão:</strong> Ativa
          </p>
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings();
      case 'users':
        return <UserManagement />;
      case 'system':
        return <SystemInfo />;
      default:
        return renderGeneralSettings();
    }
  };

  return (
    <div>
      <h1 className={`text-2xl font-semibold ${config.classes.text} mb-6`}>Configurações</h1>
      
      {/* Tabs Navigation */}
      <div className="mb-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {renderTabContent()}
    </div>
  );
};

export default Settings;