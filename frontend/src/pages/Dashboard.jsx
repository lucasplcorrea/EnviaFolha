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
import api from '../services/api';
import toast from 'react-hot-toast';

const Dashboard = () => {
  const [stats, setStats] = useState([
    {
      name: 'Colaboradores Cadastrados',
      value: '...',
      icon: UsersIcon,
      color: 'bg-blue-500'
    },
    {
      name: 'Holerites Enviados',
      value: '...',
      icon: DocumentTextIcon,
      color: 'bg-green-500'
    },
    {
      name: 'Comunicados Enviados',
      value: '...',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-purple-500'
    },
    {
      name: 'Taxa de Sucesso',
      value: '...',
      icon: ChartBarIcon,
      color: 'bg-yellow-500'
    }
  ]);

  const [evolutionStatus, setEvolutionStatus] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);

  useEffect(() => {
    loadDashboardData();
    loadEvolutionStatus();
    loadProcessingStatus();
  }, []);

  const loadDashboardData = async () => {
    try {
      // Buscar colaboradores
      const employeesResponse = await api.get('/employees');
      const activeEmployees = employeesResponse.data.filter(emp => emp.is_active !== false);
      
      // Por enquanto, vamos usar dados simulados para envios
      // Em uma implementação real, você teria endpoints específicos para essas estatísticas
      const totalHolerites = 0; // TODO: Implementar endpoint /stats/payrolls
      const totalComunicados = 0; // TODO: Implementar endpoint /stats/communications
      const successRate = '100%'; // TODO: Calcular baseado em logs de envio
      
      setStats([
        {
          name: 'Colaboradores Cadastrados',
          value: activeEmployees.length.toString(),
          icon: UsersIcon,
          color: 'bg-blue-500'
        },
        {
          name: 'Holerites Enviados',
          value: totalHolerites.toString(),
          icon: DocumentTextIcon,
          color: 'bg-green-500'
        },
        {
          name: 'Comunicados Enviados',
          value: totalComunicados.toString(),
          icon: ChatBubbleLeftRightIcon,
          color: 'bg-purple-500'
        },
        {
          name: 'Taxa de Sucesso',
          value: successRate,
          icon: ChartBarIcon,
          color: 'bg-yellow-500'
        }
      ]);
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error);
      toast.error('Erro ao carregar estatísticas');
    }
  };

  const loadEvolutionStatus = async () => {
    try {
      const response = await api.get('/evolution/status');
      setEvolutionStatus(response.data);
    } catch (error) {
      console.error('Erro ao carregar status da Evolution API:', error);
    }
  };

  const loadProcessingStatus = async () => {
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
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h1>
      
      {/* Estatísticas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`${stat.color} p-3 rounded-md`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {stat.name}
                      </dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {stat.value}
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
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Status Evolution API</h3>
              {evolutionStatus?.connected ? (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
              )}
            </div>
            <div className="mt-4">
              <div className="flex items-center">
                <span className={`inline-flex px-2 text-xs font-semibold rounded-full ${
                  evolutionStatus?.connected 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {evolutionStatus?.connected ? 'Conectado' : 'Desconectado'}
                </span>
                {evolutionStatus?.instance_name && (
                  <span className="ml-2 text-sm text-gray-500">
                    ({evolutionStatus.instance_name})
                  </span>
                )}
              </div>
              {evolutionStatus?.error && (
                <p className="mt-2 text-sm text-red-600">{evolutionStatus.error}</p>
              )}
            </div>
          </div>
        </div>

        {/* Status de processamento */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Status de Processamento</h3>
              {processingStatus?.hasActiveProcesses ? (
                <ClockIcon className="h-5 w-5 text-yellow-500 animate-spin" />
              ) : (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              )}
            </div>
            <div className="mt-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Arquivos na fila:</span>
                  <span className="font-medium">{processingStatus?.queuedFiles || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Uploads ativos:</span>
                  <span className="font-medium">{processingStatus?.activeUploads || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Status:</span>
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
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Atividade Recente</h3>
        </div>
        <div className="p-6">
          <div className="text-center text-gray-500">
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