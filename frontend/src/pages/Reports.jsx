import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useTheme } from '../contexts/ThemeContext';

const Reports = () => {
  const { config } = useTheme();
  const [reports, setReports] = useState({
    summary: {
      totalSent: 0,
      totalSuccess: 0,
      totalFailed: 0,
      successRate: 0
    },
    recentActivity: []
  });

  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    type: 'all' // all, communications, payrolls
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setLoading(true);
      
      // Por enquanto, vamos simular dados de relatório
      // Em uma implementação real, você teria um endpoint específico para relatórios
      
      // Simular dados baseados no que sabemos do sistema
      const mockReports = {
        summary: {
          totalSent: 0,
          totalSuccess: 0,
          totalFailed: 0,
          successRate: 100
        },
        recentActivity: [
          // Será populado com dados reais quando implementarmos logging de envios
        ]
      };
      
      setReports(mockReports);
      
    } catch (error) {
      console.error('Erro ao carregar relatórios:', error);
      toast.error('Erro ao carregar relatórios');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const exportReports = () => {
    toast.success('Funcionalidade de exportação será implementada em breve');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600">Carregando relatórios...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className={`text-2xl font-semibold ${config.classes.text}`}>Relatórios</h1>
        <button
          onClick={exportReports}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
          Exportar
        </button>
      </div>

      {/* Filtros */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 mb-6 ${config.classes.border}`}>
        <h2 className={`text-lg font-medium ${config.classes.text} mb-4`}>Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>
              Data Inicial
            </label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.input}`}
            />
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>
              Data Final
            </label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.input}`}
            />
          </div>
          <div>
            <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>
              Tipo
            </label>
            <select
              value={filters.type}
              onChange={(e) => handleFilterChange('type', e.target.value)}
              className={`w-full rounded-md px-3 py-2 text-sm ${config.classes.select}`}
            >
              <option value="all">Todos</option>
              <option value="communications">Comunicados</option>
              <option value="payrolls">Holerites</option>
            </select>
          </div>
        </div>
      </div>

      {/* Resumo Geral */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="bg-blue-500 p-3 rounded-md">
                  <DocumentTextIcon className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Enviado
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {reports.summary.totalSent}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="bg-green-500 p-3 rounded-md">
                  <CheckCircleIcon className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className={`text-sm font-medium ${config.classes.textSecondary} truncate`}>
                    Sucessos
                  </dt>
                  <dd className={`text-lg font-medium ${config.classes.text}`}>
                    {reports.summary.totalSuccess}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="bg-red-500 p-3 rounded-md">
                  <XCircleIcon className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className={`text-sm font-medium ${config.classes.textSecondary} truncate`}>
                    Falhas
                  </dt>
                  <dd className={`text-lg font-medium ${config.classes.text}`}>
                    {reports.summary.totalFailed}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className={`${config.classes.card} overflow-hidden shadow rounded-lg ${config.classes.border}`}>
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="bg-yellow-500 p-3 rounded-md">
                  <ChartBarIcon className="h-6 w-6 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className={`text-sm font-medium ${config.classes.textSecondary} truncate`}>
                    Taxa de Sucesso
                  </dt>
                  <dd className={`text-lg font-medium ${config.classes.text}`}>
                    {reports.summary.successRate}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Atividade Recente */}
      <div className={`${config.classes.card} shadow rounded-lg ${config.classes.border}`}>
        <div className={`px-6 py-4 border-b ${config.classes.border}`}>
          <h3 className={`text-lg font-medium ${config.classes.text}`}>Atividade Recente</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {reports.recentActivity.length > 0 ? (
            reports.recentActivity.map((activity, index) => (
              <div key={index} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      {activity.type === 'communication' ? (
                        <ChatBubbleLeftRightIcon className="h-5 w-5 text-purple-500" />
                      ) : (
                        <DocumentTextIcon className="h-5 w-5 text-green-500" />
                      )}
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900">
                        {activity.description}
                      </p>
                      <p className="text-sm text-gray-500">
                        {activity.details}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    <span className={`inline-flex px-2 text-xs font-semibold rounded-full ${
                      activity.status === 'success' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {activity.status === 'success' ? 'Sucesso' : 'Falha'}
                    </span>
                    <span className="ml-2 text-sm text-gray-500">
                      {activity.timestamp}
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="px-6 py-12 text-center">
              <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhuma atividade</h3>
              <p className="mt-1 text-sm text-gray-500">
                Quando você começar a enviar comunicados e holerites, eles aparecerão aqui.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Nota sobre implementação futura */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ChartBarIcon className="h-5 w-5 text-blue-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              Funcionalidades Futuras
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Gráficos interativos com dados históricos</li>
                <li>Relatórios por departamento e período</li>
                <li>Exportação em múltiplos formatos (PDF, Excel, CSV)</li>
                <li>Análise de horários de melhor engajamento</li>
                <li>Métricas de entrega e leitura do WhatsApp</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports;