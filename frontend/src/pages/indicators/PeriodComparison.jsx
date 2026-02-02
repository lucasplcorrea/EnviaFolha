import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import toast from 'react-hot-toast';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MinusIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';

const PeriodComparison = () => {
  const [periods, setPeriods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCompany, setSelectedCompany] = useState('all');
  const [selectedPeriod, setSelectedPeriod] = useState('all');

  useEffect(() => {
    loadPeriodComparison();
  }, [selectedCompany, selectedPeriod]);

  const loadPeriodComparison = async () => {
    try {
      setLoading(true);
      const response = await api.get('/payroll/period-comparison', {
        params: { 
          company: selectedCompany,
          period: selectedPeriod
        }
      });
      setPeriods(response.data.periods || []);
    } catch (error) {
      console.error('Erro ao carregar comparativo:', error);
      toast.error('Erro ao carregar dados do comparativo');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value || 0);
  };

  const renderTrendIcon = (current, previous, isInverted = false) => {
    if (!previous || previous === 0) return <MinusIcon className="h-4 w-4 text-gray-400" />;
    
    const diff = current - previous;
    const isPositive = isInverted ? diff < 0 : diff > 0;
    
    if (diff === 0) {
      return <MinusIcon className="h-4 w-4 text-gray-400" />;
    }
    
    return isPositive ? (
      <ArrowTrendingUpIcon className="h-4 w-4 text-green-600" />
    ) : (
      <ArrowTrendingDownIcon className="h-4 w-4 text-red-600" />
    );
  };

  const calculateVariation = (current, previous) => {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / previous) * 100;
  };

  const renderVariation = (current, previous, isInverted = false) => {
    if (!previous || previous === 0) return null;
    
    const variation = calculateVariation(current, previous);
    const isPositive = isInverted ? variation < 0 : variation > 0;
    
    if (variation === 0) return null;
    
    return (
      <span className={`text-xs ml-2 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        ({variation > 0 ? '+' : ''}{variation.toFixed(1)}%)
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <CalendarIcon className="h-8 w-8 mr-3 text-indigo-600" />
            Comparativo de Períodos
          </h1>
          <p className="text-gray-600 mt-1">
            Evolução mensal de colaboradores, proventos, descontos e valores líquidos
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          <label className="text-sm font-medium text-gray-700">Período:</label>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">Todos</option>
            <option value="mensal">Mensal</option>
            <option value="13">13º Salário</option>
          </select>
          
          <label className="text-sm font-medium text-gray-700">Empresa:</label>
          <select
            value={selectedCompany}
            onChange={(e) => setSelectedCompany(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">Todas</option>
            <option value="0060">0060 - Empreendimentos</option>
            <option value="0059">0059 - Infraestrutura</option>
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <svg className="animate-spin h-10 w-10 text-indigo-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mês/Ano
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Colaboradores
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Proventos
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Descontos
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Líquido
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {periods.map((period, index) => {
                  const previousPeriod = index < periods.length - 1 ? periods[index + 1] : null;
                  
                  return (
                    <tr key={`${period.year}-${period.month}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {String(period.month).padStart(2, '0')}/{period.year}
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(2000, period.month - 1).toLocaleDateString('pt-BR', { month: 'long' })}
                        </div>
                      </td>
                      
                      <td className="px-6 py-4">
                        <div className="text-xs text-gray-600">{period.period_names}</div>
                      </td>
                      
                      {/* Colaboradores */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center space-x-2">
                          {previousPeriod && renderTrendIcon(period.employee_count, previousPeriod.employee_count)}
                          <span className="text-sm font-semibold text-gray-900">{period.employee_count}</span>
                          {previousPeriod && renderVariation(period.employee_count, previousPeriod.employee_count)}
                        </div>
                      </td>
                      
                      {/* Total Proventos */}
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          {previousPeriod && renderTrendIcon(period.total_earnings, previousPeriod.total_earnings)}
                          <span className="text-sm font-medium text-green-700">{formatCurrency(period.total_earnings)}</span>
                          {previousPeriod && renderVariation(period.total_earnings, previousPeriod.total_earnings)}
                        </div>
                      </td>
                      
                      {/* Total Descontos */}
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          {previousPeriod && renderTrendIcon(period.total_deductions, previousPeriod.total_deductions, true)}
                          <span className="text-sm font-medium text-red-700">{formatCurrency(period.total_deductions)}</span>
                          {previousPeriod && renderVariation(period.total_deductions, previousPeriod.total_deductions, true)}
                        </div>
                      </td>
                      
                      {/* Total Líquido */}
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end space-x-2">
                          {previousPeriod && renderTrendIcon(period.total_net, previousPeriod.total_net)}
                          <span className="text-sm font-bold text-indigo-700">{formatCurrency(period.total_net)}</span>
                          {previousPeriod && renderVariation(period.total_net, previousPeriod.total_net)}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Empty State */}
          {periods.length === 0 && (
            <div className="text-center py-12">
              <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhum período encontrado</h3>
              <p className="mt-1 text-sm text-gray-500">
                Não há dados de períodos para exibir no comparativo
              </p>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      {periods.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Legenda:</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-blue-800">
            <div className="flex items-center space-x-2">
              <ArrowTrendingUpIcon className="h-4 w-4 text-green-600" />
              <span>Aumento em relação ao mês anterior</span>
            </div>
            <div className="flex items-center space-x-2">
              <ArrowTrendingDownIcon className="h-4 w-4 text-red-600" />
              <span>Diminuição em relação ao mês anterior</span>
            </div>
            <div className="flex items-center space-x-2">
              <MinusIcon className="h-4 w-4 text-gray-400" />
              <span>Sem variação ou primeiro mês</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-gray-600">* Para descontos, seta verde = redução (melhoria)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PeriodComparison;
