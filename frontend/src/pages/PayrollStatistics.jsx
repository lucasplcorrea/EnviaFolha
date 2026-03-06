import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  CalendarIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function PayrollStatistics() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(null);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const response = await api.get('/payroll/statistics');
      if (response.data.success) {
        setStats(response.data);
        // Selecionar o período mais recente por padrão
        if (response.data.periods && response.data.periods.length > 0) {
          setSelectedPeriod(response.data.periods[0].id);
        }
      }
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
      toast.error('Erro ao carregar estatísticas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatistics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-gray-600">Nenhuma estatística disponível</p>
      </div>
    );
  }

  const selectedPeriodData = stats.financial_stats?.find(
    (p) => p.period_id === selectedPeriod
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Estatísticas de Folha de Pagamento</h1>
            <p className="mt-1 text-sm text-gray-500">
              Análise consolidada dos dados CSV processados
            </p>
          </div>
          <button
            onClick={loadStatistics}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <ArrowPathIcon className="h-5 w-5" />
            <span>Atualizar</span>
          </button>
        </div>
      </div>

      {/* Totais Gerais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CalendarIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total de Períodos</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totals?.total_periods || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <UserGroupIcon className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total de Registros</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totals?.total_records || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CurrencyDollarIcon className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total INSS</p>
              <p className="text-xl font-bold text-gray-900">
                R$ {(stats.totals?.total_inss || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ArrowTrendingUpIcon className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total FGTS</p>
              <p className="text-xl font-bold text-gray-900">
                R$ {(stats.totals?.total_fgts || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Seletor de Período */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Análise por Período</h2>
        <div className="flex flex-wrap gap-2">
          {stats.periods?.map((period) => (
            <button
              key={period.id}
              onClick={() => setSelectedPeriod(period.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedPeriod === period.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {period.period_name}
              <span className="ml-2 text-xs opacity-75">({period.total_records} registros)</span>
            </button>
          ))}
        </div>
      </div>

      {/* Detalhes do Período Selecionado */}
      {selectedPeriodData && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-6">
            Detalhes - {selectedPeriodData.period_name}
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Funcionários</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {selectedPeriodData.total_employees}
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Total INSS</p>
              <p className="text-2xl font-bold text-red-600 mt-2">
                R$ {selectedPeriodData.total_inss.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Total IRRF</p>
              <p className="text-2xl font-bold text-orange-600 mt-2">
                R$ {selectedPeriodData.total_irrf.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Total FGTS</p>
              <p className="text-2xl font-bold text-purple-600 mt-2">
                R$ {selectedPeriodData.total_fgts.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Horas Extras 50%</p>
              <p className="text-2xl font-bold text-green-600 mt-2">
                R$ {selectedPeriodData.total_he_50.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500">Horas Extras 100%</p>
              <p className="text-2xl font-bold text-blue-600 mt-2">
                R$ {selectedPeriodData.total_he_100.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </p>
            </div>
          </div>

          {/* Resumo Total do Período */}
          <div className="mt-6 pt-6 border-t">
            <div className="flex justify-between items-center">
              <span className="text-lg font-medium text-gray-700">Total de Descontos:</span>
              <span className="text-2xl font-bold text-red-700">
                R$ {(
                  selectedPeriodData.total_inss + 
                  selectedPeriodData.total_irrf + 
                  selectedPeriodData.total_fgts
                ).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tabela de Todos os Períodos */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Todos os Períodos</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Período
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Funcionários
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  INSS
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  IRRF
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  FGTS
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stats.financial_stats?.map((period) => (
                <tr key={period.period_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {period.period_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {period.total_employees}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    R$ {period.total_inss.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    R$ {period.total_irrf.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    R$ {period.total_fgts.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    R$ {(period.total_inss + period.total_irrf + period.total_fgts).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
