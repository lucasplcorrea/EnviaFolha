import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import api from '../services/api';
import toast from 'react-hot-toast';

const Endomarketing = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('birthdays');
  const [period, setPeriod] = useState('week');
  const [probationPhase, setProbationPhase] = useState(1);
  
  const [birthdays, setBirthdays] = useState([]);
  const [workAnniversaries, setWorkAnniversaries] = useState([]);
  const [probationEmployees, setProbationEmployees] = useState([]);

  useEffect(() => {
    loadData();
  }, [activeTab, period, probationPhase]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'birthdays') {
        const response = await api.get(`/api/v1/endomarketing/birthdays?period=${period}`);
        setBirthdays(response.data.employees || []);
      } else if (activeTab === 'work-anniversaries') {
        const response = await api.get(`/api/v1/endomarketing/work-anniversaries?period=${period}`);
        setWorkAnniversaries(response.data.employees || []);
      } else if (activeTab === 'probation') {
        const response = await api.get(`/api/v1/endomarketing/probation?phase=${probationPhase}`);
        setProbationEmployees(response.data.employees || []);
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast.error('Erro ao carregar dados de endomarketing');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'birthdays', name: 'Aniversariantes', icon: '🎂' },
    { id: 'work-anniversaries', name: 'Tempo de Casa', icon: '🏢' },
    { id: 'probation', name: 'Período de Experiência', icon: '📋' }
  ];

  const renderBirthdays = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (birthdays.length === 0) {
      return (
        <div className={`text-center py-12 ${config.classes.textSecondary}`}>
          <span className="text-5xl mb-4 block">🎂</span>
          <p>Nenhum aniversariante {period === 'week' ? 'esta semana' : 'este mês'}</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {birthdays.map((employee) => (
          <div
            key={employee.id}
            className={`${config.classes.card} ${config.classes.border} rounded-lg p-4 shadow hover:shadow-lg transition-shadow
              ${employee.is_today ? 'border-l-4 border-l-yellow-500' : ''}`}
          >
            {employee.is_today && (
              <div className="mb-2 text-sm font-bold text-yellow-600 flex items-center gap-1">
                <span>🎉</span> HOJE!
              </div>
            )}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className={`font-semibold ${config.classes.text} text-lg`}>
                  {employee.name}
                </h3>
                <p className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.position || 'Sem cargo'} • {employee.department || 'Sem setor'}
                </p>
              </div>
              <span className="text-3xl ml-2">🎂</span>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Data:</span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.birth_date}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Idade:</span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.age} anos
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.is_today ? 'Hoje!' : 'Faltam:'}
                </span>
                <span className={`text-sm font-medium ${
                  employee.is_today ? 'text-yellow-600' : config.classes.text
                }`}>
                  {employee.is_today ? '🎉' : `${employee.days_until} dias`}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderWorkAnniversaries = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (workAnniversaries.length === 0) {
      return (
        <div className={`text-center py-12 ${config.classes.textSecondary}`}>
          <span className="text-5xl mb-4 block">🏢</span>
          <p>Nenhum aniversário de empresa {period === 'week' ? 'esta semana' : 'este mês'}</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workAnniversaries.map((employee) => (
          <div
            key={employee.id}
            className={`${config.classes.card} ${config.classes.border} rounded-lg p-4 shadow hover:shadow-lg transition-shadow
              ${employee.is_today ? 'border-l-4 border-l-blue-500' : ''}`}
          >
            {employee.is_today && (
              <div className="mb-2 text-sm font-bold text-blue-600 flex items-center gap-1">
                <span>🎊</span> HOJE!
              </div>
            )}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className={`font-semibold ${config.classes.text} text-lg`}>
                  {employee.name}
                </h3>
                <p className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.position || 'Sem cargo'} • {employee.department || 'Sem setor'}
                </p>
              </div>
              <span className="text-3xl ml-2">🏢</span>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Admissão:</span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.admission_date}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Completará:</span>
                <span className={`text-sm font-bold ${config.classes.text} text-lg`}>
                  {employee.years_completing} {employee.years_completing === 1 ? 'ano' : 'anos'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.is_today ? 'Hoje!' : 'Faltam:'}
                </span>
                <span className={`text-sm font-medium ${
                  employee.is_today ? 'text-blue-600' : config.classes.text
                }`}>
                  {employee.is_today ? '🎊' : `${employee.days_until} dias`}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderProbation = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (probationEmployees.length === 0) {
      return (
        <div className={`text-center py-12 ${config.classes.textSecondary}`}>
          <span className="text-5xl mb-4 block">📋</span>
          <p>Nenhum colaborador próximo à fase {probationPhase} do período de experiência</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {probationEmployees.map((employee) => (
          <div
            key={employee.id}
            className={`${config.classes.card} ${config.classes.border} rounded-lg p-4 shadow hover:shadow-lg transition-shadow
              ${employee.is_today ? 'border-l-4 border-l-orange-500' : ''}
              ${employee.is_overdue ? 'border-l-4 border-l-red-500' : ''}`}
          >
            {employee.is_today && (
              <div className="mb-2 text-sm font-bold text-orange-600 flex items-center gap-1">
                <span>⚠️</span> HOJE É O DIA!
              </div>
            )}
            {employee.is_overdue && (
              <div className="mb-2 text-sm font-bold text-red-600 flex items-center gap-1">
                <span>🚨</span> ATRASADO
              </div>
            )}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className={`font-semibold ${config.classes.text} text-lg`}>
                  {employee.name}
                </h3>
                <p className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.position || 'Sem cargo'} • {employee.department || 'Sem setor'}
                </p>
              </div>
              <span className="text-3xl ml-2">📋</span>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Admissão:</span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.admission_date}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>Dias trabalhados:</span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.days_working} dias
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>
                  Data da fase {probationPhase}:
                </span>
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {employee.phase_date}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-sm ${config.classes.textSecondary}`}>
                  {employee.is_overdue ? 'Atraso:' : employee.is_today ? 'Hoje!' : 'Faltam:'}
                </span>
                <span className={`text-sm font-medium ${
                  employee.is_overdue ? 'text-red-600' :
                  employee.is_today ? 'text-orange-600' : config.classes.text
                }`}>
                  {employee.is_today ? '⚠️' : 
                   employee.is_overdue ? `${Math.abs(employee.days_until)} dias` :
                   `${employee.days_until} dias`}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className={`text-2xl font-semibold ${config.classes.text}`}>
            Endomarketing
          </h1>
          <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
            Acompanhe datas importantes e momentos especiais dos colaboradores
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-8 border-b" style={{ borderColor: config.classes.border }}>
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

      {/* Filtros */}
      <div className={`${config.classes.card} ${config.classes.border} rounded-lg p-4 mb-6`}>
        <div className="flex flex-wrap items-center gap-4">
          {activeTab !== 'probation' ? (
            <>
              <label className={`text-sm font-medium ${config.classes.text}`}>
                Período:
              </label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className={`px-3 py-2 border rounded-lg ${config.classes.input} text-sm`}
              >
                <option value="week">Esta Semana</option>
                <option value="month">Este Mês</option>
              </select>
            </>
          ) : (
            <>
              <label className={`text-sm font-medium ${config.classes.text}`}>
                Fase:
              </label>
              <select
                value={probationPhase}
                onChange={(e) => setProbationPhase(parseInt(e.target.value))}
                className={`px-3 py-2 border rounded-lg ${config.classes.input} text-sm`}
              >
                <option value={1}>Fase 1 - 45 dias</option>
                <option value={2}>Fase 2 - 90 dias</option>
              </select>
            </>
          )}
          
          <button
            onClick={loadData}
            disabled={loading}
            className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                     disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            {loading ? 'Carregando...' : '🔄 Atualizar'}
          </button>
        </div>
      </div>

      {/* Conteúdo */}
      {activeTab === 'birthdays' && renderBirthdays()}
      {activeTab === 'work-anniversaries' && renderWorkAnniversaries()}
      {activeTab === 'probation' && renderProbation()}
    </div>
  );
};

export default Endomarketing;
