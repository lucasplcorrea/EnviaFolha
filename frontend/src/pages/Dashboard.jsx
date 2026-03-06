import React, { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon, 
  UsersIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
  DocumentPlusIcon,
  UserPlusIcon,
  ExclamationCircleIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import toast from 'react-hot-toast';

const Dashboard = () => {
  const { config } = useTheme();
  const navigate = useNavigate();
  
  const [activeJob, setActiveJob] = useState(null);
  const [jobPollingInterval, setJobPollingInterval] = useState(null);
  
  const [stats, setStats] = useState([
    {
      name: 'Colaboradores Cadastrados',
      value: '...',
      icon: UsersIcon,
      color: 'bg-blue-500',
      route: '/employees'
    },
    {
      name: 'Holerites Processados',
      value: '...',
      icon: DocumentTextIcon,
      color: 'bg-orange-500',
      route: '/payroll-sender'
    },
    {
      name: 'Holerites Enviados',
      value: '...',
      icon: CheckCircleIcon,
      color: 'bg-green-500',
      route: '/reports'
    },
    {
      name: 'Comunicados Enviados',
      value: '...',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-purple-500',
      route: '/reports'
    },
    {
      name: 'Taxa de Sucesso',
      value: '...',
      icon: ChartBarIcon,
      color: 'bg-yellow-500',
      route: '/reports'
    }
  ]);

  const [evolutionStatus, setEvolutionStatus] = useState(null);
  const [endomarketingSummary, setEndomarketingSummary] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const abortController = new AbortController();
    
    const loadInitialData = async () => {
      try {
        await loadDashboardData(abortController.signal);
        await loadEvolutionStatus(abortController.signal);
        await loadEndomarketingSummary(abortController.signal);
        await loadRecentActivity(abortController.signal);
        await loadAlerts(abortController.signal);
      } catch (error) {
        if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
          console.error('Erro ao carregar dados:', error);
        }
      }
    };
    
    loadInitialData();
    
    // Verificar se há jobs ativos
    checkActiveJobs();
    
    return () => {
      abortController.abort();
      if (jobPollingInterval) {
        clearInterval(jobPollingInterval);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Função para verificar jobs ativos
  const checkActiveJobs = async () => {
    try {
      // Tentar recuperar job ativo do localStorage
      const savedJobId = localStorage.getItem('activeJobId');
      if (savedJobId) {
        const response = await api.get(`/payrolls/bulk-send/${savedJobId}/status`);
        const jobData = response.data;
        
        if (jobData.status === 'running') {
          setActiveJob(jobData);
          startJobPolling(savedJobId);
        } else {
          localStorage.removeItem('activeJobId');
        }
      }
    } catch (error) {
      localStorage.removeItem('activeJobId');
    }
  };
  
  // Polling do job ativo
  const startJobPolling = (jobId) => {
    if (jobPollingInterval) {
      clearInterval(jobPollingInterval);
    }
    
    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/payrolls/bulk-send/${jobId}/status`);
        const jobData = response.data;
        setActiveJob(jobData);
        
        if (jobData.status === 'completed' || jobData.status === 'failed') {
          clearInterval(interval);
          setJobPollingInterval(null);
          localStorage.removeItem('activeJobId');
          
          // Recarregar dados do dashboard
          loadDashboardData();
        }
      } catch (error) {
        clearInterval(interval);
        setJobPollingInterval(null);
        setActiveJob(null);
        localStorage.removeItem('activeJobId');
      }
    }, 2000);
    
    setJobPollingInterval(interval);
  };

  const loadDashboardData = async (signal) => {
    try {
      // Buscar estatísticas do dashboard
      const dashboardResponse = await api.get('/dashboard/stats', { signal });
      const dashboardData = dashboardResponse.data;
      
      // Buscar dados de holerites processados
      const payrollsResponse = await api.get('/payrolls/processed', { signal });
      const payrollsData = payrollsResponse.data;
      
      // Buscar estatísticas de envios REAIS do banco de dados
      const reportsResponse = await api.get('/reports/statistics', { signal });
      const reportsData = reportsResponse.data;
      
      // Extrair dados de comunicados e holerites enviados
      const totalComunicados = reportsData.by_type?.communications?.success || 0;
      const holeritesSent = reportsData.by_type?.payrolls?.success || 0;
      const successRate = reportsData.summary?.success_rate || 100;

      setStats([
        {
          name: 'Colaboradores Cadastrados',
          value: dashboardData.total_employees?.toString() || '0',
          icon: UsersIcon,
          color: 'bg-blue-500',
          route: '/employees'
        },
        {
          name: 'Holerites Processados',
          value: payrollsData.statistics?.total?.toString() || '0',
          icon: DocumentTextIcon,
          color: 'bg-orange-500',
          route: '/payroll-sender',
          subtitle: `${payrollsData.statistics?.ready || 0} prontos para envio`
        },
        {
          name: 'Holerites Enviados',
          value: holeritesSent.toString(),
          icon: CheckCircleIcon,
          color: 'bg-green-500',
          route: '/reports',
          subtitle: reportsData.by_type?.payrolls?.failed > 0 
            ? `${reportsData.by_type.payrolls.failed} com falha` 
            : 'Todos com sucesso'
        },
        {
          name: 'Comunicados Enviados',
          value: totalComunicados.toString(),
          icon: ChatBubbleLeftRightIcon,
          color: 'bg-purple-500',
          route: '/reports',
          subtitle: reportsData.by_type?.communications?.failed > 0 
            ? `${reportsData.by_type.communications.failed} com falha` 
            : reportsData.by_type?.communications?.success > 0 ? 'Todos com sucesso' : ''
        },
        {
          name: 'Taxa de Sucesso Global',
          value: `${successRate.toFixed(1)}%`,
          icon: ChartBarIcon,
          color: 'bg-yellow-500',
          route: '/reports',
          subtitle: `${reportsData.summary?.total_success || 0} de ${reportsData.summary?.total_sent || 0} enviados`
        }
      ]);
    } catch (error) {
      // Ignorar erros de abort (ocorrem quando componente desmonta)
      if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
        console.error('Erro ao carregar dados do dashboard:', error);
        toast.error('Erro ao carregar dados do dashboard');
      }
    }
  };

  const loadEvolutionStatus = async (signal) => {
    try {
      const response = await api.get('/evolution/status', { signal });
      setEvolutionStatus(response.data);
    } catch (error) {
      // Ignorar erros de abort
      if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
        console.error('Erro ao carregar status Evolution API:', error);
      }
    }
  };

  const loadEndomarketingSummary = async (signal) => {
    try {
      const response = await api.get('/endomarketing/summary', { signal });
      setEndomarketingSummary(response.data);
    } catch (error) {
      if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
        console.error('Erro ao carregar resumo de endomarketing:', error);
      }
    }
  };

  const loadRecentActivity = async (signal) => {
    try {
      // Buscar últimas 10 atividades com informações do usuário
      const response = await api.get('/reports/recent', { 
        signal,
        params: { limit: 10 } 
      });
      // Agora a API retorna { data: [...], pagination: {...} }
      setRecentActivity(response.data.data || response.data || []);
    } catch (error) {
      if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
        console.error('Erro ao carregar atividades recentes:', error);
        // Não carregar dados mockados - deixar vazio se endpoint não existir
        setRecentActivity([]);
      }
    }
  };

  const loadAlerts = async (signal) => {
    try {
      const newAlerts = [];
      
      // Verificar Evolution API
      const evolutionResponse = await api.get('/evolution/status', { signal });
      if (evolutionResponse.data.status !== 'connected') {
        newAlerts.push({
          id: 'evolution',
          type: 'error',
          message: 'Evolution API está desconectada. Envios de WhatsApp estão indisponíveis.',
          action: 'Verificar Configurações',
          route: '/settings'
        });
      }
      
      // Verificar holerites processados mas não enviados
      const payrollsResponse = await api.get('/payrolls/processed', { signal });
      const readyToSend = payrollsResponse.data.statistics?.ready || 0;
      if (readyToSend > 0) {
        newAlerts.push({
          id: 'payrolls-pending',
          type: 'warning',
          message: `${readyToSend} holerites processados aguardando envio.`,
          action: 'Enviar Agora',
          route: '/payroll-sender'
        });
      }
      
      setAlerts(newAlerts);
    } catch (error) {
      if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
        console.error('Erro ao carregar alertas:', error);
      }
    }
  };

  const formatTimeAgo = (timestamp) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `${diffMins}min atrás`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h atrás`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d atrás`;
  };

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className={`text-2xl font-semibold ${config.classes.text}`}>Dashboard</h1>
          <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
            Visão geral de métricas e indicadores do sistema
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <CalendarIcon className="h-5 w-5" />
          {new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}
        </div>
      </div>

      {/* Card de Job Ativo */}
      {activeJob && activeJob.status === 'running' && (
        <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-lg p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
                <PaperAirplaneIcon className="h-5 w-5 text-blue-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-blue-900">📨 Envio de Holerites em Andamento</h3>
                <p className="text-sm text-blue-700 mt-1">
                  {activeJob.processed_files} de {activeJob.total_files} arquivos processados
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/payroll-sender')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold shadow-md hover:shadow-lg"
            >
              Acompanhar Detalhes
            </button>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-sm text-blue-700 mb-2">
              <span className="font-medium">{activeJob.progress_percentage}% concluído</span>
              <span>⏱️ {Math.floor(activeJob.elapsed_seconds / 60)}m {activeJob.elapsed_seconds % 60}s</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 shadow-inner"
                style={{ width: `${activeJob.progress_percentage}%` }}
              ></div>
            </div>
            <div className="mt-3 flex justify-between text-xs text-blue-600">
              <span className="flex items-center">
                <CheckCircleIcon className="h-4 w-4 mr-1" />
                {activeJob.successful_sends} enviados
              </span>
              {activeJob.failed_sends > 0 && (
                <span className="flex items-center text-red-600">
                  <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                  {activeJob.failed_sends} falhas
                </span>
              )}
              <span className="font-medium">
                {activeJob.total_files - activeJob.processed_files} restantes
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Alertas */}
      {alerts.length > 0 && (
        <div className="mb-6 space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`flex items-center justify-between p-4 rounded-lg ${
                alert.type === 'error' 
                  ? 'bg-red-50 border border-red-200' 
                  : 'bg-yellow-50 border border-yellow-200'
              }`}
            >
              <div className="flex items-center gap-3">
                {alert.type === 'error' ? (
                  <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
                ) : (
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                )}
                <span className={`text-sm font-medium ${
                  alert.type === 'error' ? 'text-red-800' : 'text-yellow-800'
                }`}>
                  {alert.message}
                </span>
              </div>
              <button
                onClick={() => navigate(alert.route)}
                className={`px-4 py-2 text-sm font-medium rounded-lg ${
                  alert.type === 'error'
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-yellow-600 hover:bg-yellow-700 text-white'
                }`}
              >
                {alert.action}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button
          onClick={() => navigate('/payroll-sender')}
          className="flex items-center gap-3 p-4 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
        >
          <PaperAirplaneIcon className="h-6 w-6 text-blue-600" />
          <div className="text-left">
            <div className="font-medium text-blue-900">Enviar Holerites</div>
            <div className="text-sm text-blue-600">Processar e enviar via WhatsApp</div>
          </div>
        </button>
        
        <button
          onClick={() => navigate('/communications')}
          className="flex items-center gap-3 p-4 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg transition-colors"
        >
          <DocumentPlusIcon className="h-6 w-6 text-purple-600" />
          <div className="text-left">
            <div className="font-medium text-purple-900">Novo Comunicado</div>
            <div className="text-sm text-purple-600">Enviar mensagem para colaboradores</div>
          </div>
        </button>
        
        <button
          onClick={() => navigate('/employees')}
          className="flex items-center gap-3 p-4 bg-green-50 hover:bg-green-100 border border-green-200 rounded-lg transition-colors"
        >
          <UserPlusIcon className="h-6 w-6 text-green-600" />
          <div className="text-left">
            <div className="font-medium text-green-900">Gerenciar Colaboradores</div>
            <div className="text-sm text-green-600">Adicionar ou importar em lote</div>
          </div>
        </button>
      </div>
      
      {/* Estatísticas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          
          return (
            <div 
              key={stat.name} 
              onClick={() => stat.route && navigate(stat.route)}
              className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border} ${
                stat.route ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''
              }`}
            >
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`${stat.color} p-3 rounded-md`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className={`text-sm font-medium ${config.classes.textSecondary} truncate`}>
                        {stat.name}
                      </dt>
                      <dd>
                        <div className={`text-2xl font-bold ${config.classes.text}`}>
                          {stat.value}
                        </div>
                        {stat.subtitle && (
                          <div className={`text-xs ${config.classes.textSecondary} mt-1`}>
                            {stat.subtitle}
                          </div>
                        )}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cards de status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        
        {/* Status de Endomarketing */}
        <div 
          className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border} cursor-pointer hover:shadow-lg transition-shadow`}
          onClick={() => navigate('/endomarketing')}
        >
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-medium ${config.classes.text}`}>📊 Endomarketing</h3>
              <CalendarIcon className="h-5 w-5 text-purple-500" />
            </div>
            <div className="mt-4">
              {endomarketingSummary ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className={config.classes.textSecondary}>🎂 Aniversariantes (semana):</span>
                    <span className={`font-medium ${config.classes.text}`}>
                      {endomarketingSummary.birthdays?.week || 0}
                      {endomarketingSummary.birthdays?.today > 0 && (
                        <span className="ml-1 text-yellow-600">({endomarketingSummary.birthdays.today} hoje!)</span>
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className={config.classes.textSecondary}>🏢 Tempo de casa (semana):</span>
                    <span className={`font-medium ${config.classes.text}`}>
                      {endomarketingSummary.work_anniversaries?.week || 0}
                      {endomarketingSummary.work_anniversaries?.today > 0 && (
                        <span className="ml-1 text-blue-600">({endomarketingSummary.work_anniversaries.today} hoje!)</span>
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className={config.classes.textSecondary}>📋 Experiência (45 dias):</span>
                    <span className={`font-medium ${config.classes.text}`}>
                      {endomarketingSummary.probation?.phase1 || 0}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className={config.classes.textSecondary}>📋 Experiência (90 dias):</span>
                    <span className={`font-medium ${config.classes.text}`}>
                      {endomarketingSummary.probation?.phase2 || 0}
                    </span>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button className="text-sm text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 font-medium flex items-center">
                      Ver detalhes completos →
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
                  <p className={`mt-2 text-sm ${config.classes.textSecondary}`}>Carregando...</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status de Envio de Folhas */}
        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-medium ${config.classes.text}`}>Status de Envio</h3>
              <PaperAirplaneIcon className="h-5 w-5 text-blue-500" />
            </div>
            <div className="mt-4">
              {evolutionStatus ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm ${config.classes.textSecondary}`}>Evolution API:</span>
                    <span className={`inline-flex px-2 text-xs font-semibold rounded-full ${
                      evolutionStatus?.status === 'connected' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {evolutionStatus?.status === 'connected' ? 'Conectado' : 'Desconectado'}
                    </span>
                  </div>
                  {evolutionStatus?.instance_name && (
                    <div className="flex items-center justify-between">
                      <span className={`text-sm ${config.classes.textSecondary}`}>Instância:</span>
                      <span className={`text-sm ${config.classes.text}`}>{evolutionStatus.instance_name}</span>
                    </div>
                  )}
                  {evolutionStatus?.status === 'connected' ? (
                    <div className={`mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg ${config.classes.border}`}>
                      <p className="text-sm text-green-800 dark:text-green-300 flex items-center">
                        <CheckCircleIcon className="h-4 w-4 mr-2" />
                        Sistema pronto para envios
                      </p>
                    </div>
                  ) : (
                    <div className={`mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg ${config.classes.border}`}>
                      <p className="text-sm text-red-800 dark:text-red-300 flex items-center">
                        <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                        Envios indisponíveis
                      </p>
                      {evolutionStatus?.message && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">{evolutionStatus.message}</p>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                  <p className={`mt-2 text-sm ${config.classes.textSecondary}`}>Carregando...</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Atividade recente */}
      <div className={`${config.classes.card} shadow rounded-lg ${config.classes.border}`}>
        <div className={`px-6 py-4 border-b ${config.classes.border}`}>
          <h3 className={`text-lg font-medium ${config.classes.text}`}>Atividade Recente</h3>
        </div>
        <div className="p-6">
          {recentActivity.length === 0 ? (
            <div className={`text-center ${config.classes.textSecondary}`}>
              <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2">Nenhuma atividade recente</p>
              <p className="text-sm">Envios e uploads aparecerão aqui</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((activity) => (
                <div
                  key={activity.id}
                  className={`flex items-center justify-between p-3 rounded-lg ${config.classes.border} border hover:bg-gray-50 transition-colors`}
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className={`p-2 rounded-lg ${
                      activity.type === 'payroll' ? 'bg-blue-100' : 'bg-purple-100'
                    }`}>
                      {activity.type === 'payroll' ? (
                        <DocumentTextIcon className="h-5 w-5 text-blue-600" />
                      ) : (
                        <ChatBubbleLeftRightIcon className="h-5 w-5 text-purple-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${config.classes.text}`}>
                        {activity.type === 'payroll' ? 'Holerite enviado' : 'Comunicado enviado'}
                      </div>
                      <div className={`text-xs ${config.classes.textSecondary}`}>
                        Para: {activity.employee_name || activity.employee}
                      </div>
                      {activity.sent_by_user && (
                        <div className={`text-xs ${config.classes.textSecondary} italic`}>
                          Por: {activity.sent_by_user}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs ${config.classes.textSecondary} whitespace-nowrap`}>
                      {formatTimeAgo(activity.timestamp || activity.sent_at)}
                    </span>
                    {(activity.status === 'success' || activity.status === 'sent') ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0" />
                    ) : (
                      <ExclamationCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;