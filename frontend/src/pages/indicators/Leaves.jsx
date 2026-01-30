import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ExclamationTriangleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState, translateLabel } from './components';

const Leaves = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/leaves');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar afastamentos:', error);
      toast.error('Erro ao carregar indicadores de afastamentos');
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
    return <LoadingSpinner message="Carregando indicadores de afastamentos..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de afastamentos disponível" />;
  }

  const { currently_on_leave, by_leave_type, by_leave_reason } = data;

  // Calcular totais
  const totalByType = by_leave_type?.reduce((sum, t) => sum + t.count, 0) || 0;
  const totalByReason = by_leave_reason?.reduce((sum, r) => sum + r.count, 0) || 0;

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

      {/* Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Atualmente Afastados"
          value={currently_on_leave || 0}
          icon={ExclamationTriangleIcon}
          color="yellow"
        />
        <MetricCard
          title="Tipos de Afastamento"
          value={by_leave_type?.length || 0}
          icon={ExclamationTriangleIcon}
          color="orange"
        />
        <MetricCard
          title="Motivos Registrados"
          value={by_leave_reason?.length || 0}
          icon={ExclamationTriangleIcon}
          color="pink"
        />
      </div>

      {/* Por Tipo de Afastamento */}
      {by_leave_type && by_leave_type.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📋 Afastamentos por Tipo
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {by_leave_type.map((type, idx) => {
              const percentage = totalByType > 0 ? ((type.count / totalByType) * 100).toFixed(1) : 0;
              
              // Cores por índice
              const colors = [
                { bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800', text: 'text-yellow-700 dark:text-yellow-400', bar: 'bg-yellow-500' },
                { bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800', text: 'text-orange-700 dark:text-orange-400', bar: 'bg-orange-500' },
                { bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800', text: 'text-red-700 dark:text-red-400', bar: 'bg-red-500' },
                { bg: 'bg-pink-50 dark:bg-pink-900/20', border: 'border-pink-200 dark:border-pink-800', text: 'text-pink-700 dark:text-pink-400', bar: 'bg-pink-500' },
                { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800', text: 'text-purple-700 dark:text-purple-400', bar: 'bg-purple-500' },
              ];
              const color = colors[idx % colors.length];
              
              return (
                <div key={idx} className={`p-4 rounded-lg border ${color.bg} ${color.border}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-sm font-medium ${color.text}`}>
                      {translateLabel(type.leave_type) || type.leave_type || 'Não informado'}
                    </p>
                    <span className={`text-2xl font-bold ${config.classes.text}`}>{type.count}</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${color.bar}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{percentage}% do total</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Por Motivo de Afastamento */}
      {by_leave_reason && by_leave_reason.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            🏥 Afastamentos por Motivo
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
                {by_leave_reason.map((reason, idx) => {
                  const percentage = totalByReason > 0 ? ((reason.count / totalByReason) * 100).toFixed(1) : 0;
                  return (
                    <tr key={idx} className={config.classes.cardHover}>
                      <td className={`px-6 py-4 text-sm ${config.classes.text}`}>
                        {translateLabel(reason.leave_reason) || reason.leave_reason || 'Não informado'}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${config.classes.text}`}>
                        {reason.count}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm ${config.classes.textSecondary}`}>
                        <div className="flex items-center">
                          <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2 mr-2">
                            <div 
                              className="bg-yellow-500 h-2 rounded-full" 
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

      {/* Resumo e Alertas */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          ⚠️ Resumo de Afastamentos
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Status atual */}
          <div className="p-4 rounded-lg bg-gradient-to-r from-yellow-500 to-orange-500 text-white">
            <p className="text-sm font-medium opacity-90">Colaboradores Afastados Agora</p>
            <p className="text-4xl font-bold mt-2">{currently_on_leave || 0}</p>
            <p className="text-sm opacity-75 mt-1">
              Requer acompanhamento contínuo
            </p>
          </div>

          {/* Tipo mais comum */}
          {by_leave_type && by_leave_type.length > 0 && (
            <div className="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
              <p className={`text-sm font-medium ${config.classes.textSecondary}`}>Tipo Mais Frequente</p>
              {(() => {
                const maxType = by_leave_type.reduce((max, t) => t.count > max.count ? t : max, by_leave_type[0]);
                const percentage = totalByType > 0 ? ((maxType.count / totalByType) * 100).toFixed(1) : 0;
                return (
                  <>
                    <p className={`text-xl font-bold ${config.classes.text} mt-2`}>
                      {translateLabel(maxType.leave_type) || maxType.leave_type || 'Não informado'}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      {maxType.count} casos ({percentage}%)
                    </p>
                  </>
                );
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Leaves;
