import React, { useState, useEffect } from 'react';
import { 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon, 
  UsersIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { useTheme } from '../contexts/ThemeContext';
import api from '../services/api';
import toast from 'react-hot-toast';

const Dashboard = () => {
  const { config } = useTheme();
  const [stats, setStats] = useState([
    {
      name: 'Colaboradores Cadastrados',
      value: '...',
      icon: UsersIcon,
      color: 'bg-brand-500'
    },
    {
      name: 'Holerites Processados',
      value: '...',
      icon: DocumentTextIcon,
      color: 'bg-accent-yellow'
    },
    {
      name: 'Holerites Enviados',
      value: '...',
      icon: CheckCircleIcon,
      color: 'bg-accent-green'
    },
    {
      name: 'Comunicados Enviados',
      value: '...',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-accent-cyan'
    },
    {
      name: 'Taxa de Sucesso',
      value: '...',
      icon: ChartBarIcon,
      color: 'bg-brand-600'
    }
  ]);

  const [evolutionStatus, setEvolutionStatus] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);

  useEffect(() => {
    // Criar AbortController para cancelar requisições pendentes
    const abortController = new AbortController();
    
    // Carregar dados iniciais com signal para permitir cancelamento
    const loadInitialData = async () => {
      try {
        await loadDashboardData(abortController.signal);
        await loadEvolutionStatus(abortController.signal);
        await loadProcessingStatus(abortController.signal);
      } catch (error) {
        // Ignorar erros de abort (ocorrem quando componente desmonta)
        if (error.name !== 'AbortError' && error.name !== 'CanceledError') {
          console.error('Erro ao carregar dados:', error);
        }
      }
    };
    
    loadInitialData();
    
    // Cleanup: cancelar requisições pendentes ao desmontar
    return () => {
      abortController.abort();
    };
  }, []);

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
          color: 'bg-blue-500'
        },
        {
          name: 'Holerites Processados',
          value: payrollsData.statistics?.total?.toString() || '0',
          icon: DocumentTextIcon,
          color: 'bg-orange-500',
          subtitle: `${payrollsData.statistics?.ready || 0} prontos para envio`
        },
        {
          name: 'Holerites Enviados',
          value: holeritesSent.toString(),
          icon: CheckCircleIcon,
          color: 'bg-green-500',
          subtitle: reportsData.by_type?.payrolls?.failed > 0 
            ? `${reportsData.by_type.payrolls.failed} com falha` 
            : 'Todos com sucesso'
        },
        {
          name: 'Comunicados Enviados',
          value: totalComunicados.toString(),
          icon: ChatBubbleLeftRightIcon,
          color: 'bg-purple-500',
          subtitle: reportsData.by_type?.communications?.failed > 0 
            ? `${reportsData.by_type.communications.failed} com falha` 
            : reportsData.by_type?.communications?.success > 0 ? 'Todos com sucesso' : ''
        },
        {
          name: 'Taxa de Sucesso',
          value: `${successRate.toFixed(1)}%`,
          icon: ChartBarIcon,
          color: 'bg-yellow-500',
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

  const loadProcessingStatus = async (signal) => {
    // Por enquanto simulado - em implementação real seria um endpoint específico
    setProcessingStatus({
      hasActiveProcesses: false,
      queuedFiles: 0,
      activeUploads: 0,
      lastProcessed: null
    });
  };

  return (
    <div>
      <h1 className={`text-2xl font-semibold ${config.classes.text} mb-6`}>Dashboard</h1>
      
      {/* Estatísticas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
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
                      <dd className={`text-lg font-medium ${config.classes.text}`}>
                        {stat.value}
                        {stat.subtitle && (
                          <div className={`text-sm ${config.classes.textSecondary} mt-1`}>
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
        
        {/* Status da Evolution API */}
        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-medium ${config.classes.text}`}>Status Evolution API</h3>
              {evolutionStatus?.status === 'connected' ? (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
              )}
            </div>
            <div className="mt-4">
              <div className="flex items-center">
                <span className={`inline-flex px-2 text-xs font-semibold rounded-full ${
                  evolutionStatus?.status === 'connected' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {evolutionStatus?.status === 'connected' ? 'Conectado' : 'Desconectado'}
                </span>
                {evolutionStatus?.instance_name && (
                  <span className={`ml-2 text-sm ${config.classes.textSecondary}`}>
                    ({evolutionStatus.instance_name})
                  </span>
                )}
              </div>
              {evolutionStatus?.message && evolutionStatus?.status !== 'connected' && (
                <p className="mt-2 text-sm text-red-600">{evolutionStatus.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Status de processamento */}
        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-medium ${config.classes.text}`}>Status de Processamento</h3>
              {processingStatus?.hasActiveProcesses ? (
                <ClockIcon className="h-5 w-5 text-yellow-500 animate-spin" />
              ) : (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              )}
            </div>
            <div className="mt-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className={config.classes.textSecondary}>Arquivos na fila:</span>
                  <span className={`font-medium ${config.classes.text}`}>{processingStatus?.queuedFiles || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className={config.classes.textSecondary}>Uploads ativos:</span>
                  <span className={`font-medium ${config.classes.text}`}>{processingStatus?.activeUploads || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className={config.classes.textSecondary}>Status:</span>
                  <span className={`font-medium ${
                    processingStatus?.hasActiveProcesses ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {processingStatus?.hasActiveProcesses ? 'Processando...' : 'Ocioso'}
                  </span>
                </div>
              </div>
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
          <div className={`text-center ${config.classes.textSecondary}`}>
            <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2">Nenhuma atividade recente</p>
            <p className="text-sm">Envios e uploads aparecerão aqui</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;