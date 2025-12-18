import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { usePermissions } from '../hooks/usePermissions';
import ThemeSelector from '../components/ThemeSelector';
import Users from './Users';
import SystemInfo from './SystemInfo';
import UtilityScripts from './UtilityScripts';

const Settings = () => {
  const [activeTab, setActiveTab] = useState('general');
  const { config } = useTheme();
  const { isAdmin } = usePermissions();
  const navigate = useNavigate();

  const tabs = [
    { id: 'general', name: 'Geral', icon: '⚙️' },
    ...(isAdmin() ? [{ id: 'users', name: 'Usuários', icon: '👥' }] : []),
    { id: 'system', name: 'Sistema', icon: '🖥️' },
    ...(isAdmin() ? [{ id: 'scripts', name: 'Scripts Úteis', icon: '🛠️' }] : [])
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

      {/* Logs do Sistema */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-lg font-medium ${config.classes.text}`}>
            📋 Logs do Sistema
          </h2>
        </div>
        
        <p className={`${config.classes.textSecondary} mb-4`}>
          Visualize os registros de atividade do sistema, incluindo importações, autenticações, erros e outras operações.
        </p>
        
        <button
          onClick={() => navigate('/system-logs')}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Ver Logs do Sistema
        </button>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings();
      case 'users':
        return isAdmin() ? <Users /> : renderGeneralSettings();
      case 'system':
        return <SystemInfo />;
      case 'scripts':
        return isAdmin() ? <UtilityScripts /> : renderGeneralSettings();
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