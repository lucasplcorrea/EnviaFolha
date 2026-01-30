import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState } from './components';

const Turnover = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/turnover');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar rotatividade:', error);
      toast.error('Erro ao carregar indicadores de rotatividade');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = async () => {
    try {
      await api.post('/indicators/cache/invalidate');
      toast.success('Cache invalidado, recalculando...');
    } catch (error) {
      console.error('Erro ao invalidar cache:', error);
    }
    await loadData();
    toast.success('Indicadores atualizados!');
  };

  if (loading) {
    return <LoadingSpinner message="Carregando indicadores de rotatividade..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de rotatividade disponível" />;
  }

  const { rates, movements, termination_reasons, turnover_by_department } = data;

  return (
    <div className="space-y-6">
      {/* Botão de atualização */}
      <div className="flex justify-end">
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <ArrowPathIcon className="h-5 w-5" />
          Atualizar
        </button>
      </div>

      {/* Taxas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Taxa de Rotatividade"
          value={rates?.turnover || 0}
          unit="%"
          icon={ArrowPathIcon}
          color="purple"
        />
        <MetricCard
          title="Taxa de Admissão"
          value={rates?.admission || 0}
          unit="%"
          icon={ArrowTrendingUpIcon}
          color="green"
        />
        <MetricCard
          title="Taxa de Desligamento"
          value={rates?.termination || 0}
          unit="%"
          icon={ArrowTrendingDownIcon}
          color="red"
        />
      </div>

      {/* Movimentações */}
      {movements && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📈 Movimentações no Período
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Efetivo Médio</p>
              <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                {movements.average_headcount || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">✅ Admissões</p>
              <p className="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">
                {movements.admissions || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-600 dark:text-red-400 font-medium">❌ Desligamentos</p>
              <p className="text-3xl font-bold text-red-700 dark:text-red-300 mt-2">
                {movements.terminations || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
              <p className="text-sm text-purple-600 dark:text-purple-400 font-medium">📊 Saldo Líquido</p>
              <p className={`text-3xl font-bold mt-2 ${
                (movements.admissions - movements.terminations) >= 0 
                  ? 'text-green-700 dark:text-green-300' 
                  : 'text-red-700 dark:text-red-300'
              }`}>
                {(movements.admissions || 0) - (movements.terminations || 0)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Motivos de Desligamento */}
      {termination_reasons && termination_reasons.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📋 Motivos de Desligamento
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className={config.classes.background}>
                <tr>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Motivo
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Quantidade
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Percentual
                  </th>
                </tr>
              </thead>
              <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                {termination_reasons.map((reason, idx) => {
                  const total = termination_reasons.reduce((sum, r) => sum + r.count, 0);
                  const percentage = total > 0 ? ((reason.count / total) * 100).toFixed(1) : 0;
                  return (
                    <tr key={idx} className={config.classes.cardHover}>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.text}`}>
                        {reason.reason || 'Não informado'}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                        {reason.count}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                        <div className="flex items-center">
                          <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2 mr-2">
                            <div 
                              className="bg-red-500 h-2 rounded-full" 
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                          <span>{percentage}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rotatividade por Departamento */}
      {turnover_by_department && turnover_by_department.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            🏢 Rotatividade por Departamento
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className={config.classes.background}>
                <tr>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Departamento
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Admissões
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Desligamentos
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Taxa
                  </th>
                </tr>
              </thead>
              <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                {turnover_by_department.map((dept, idx) => (
                  <tr key={idx} className={config.classes.cardHover}>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.text}`}>
                      {dept.department || 'Não informado'}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-green-600 dark:text-green-400`}>
                      +{dept.admissions || 0}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-red-600 dark:text-red-400`}>
                      -{dept.terminations || 0}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                      {(dept.turnover_rate || 0).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Turnover;
