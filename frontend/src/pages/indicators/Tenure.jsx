import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ClockIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState, formatTenure } from './components';

const Tenure = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/tenure');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar tempo de casa:', error);
      toast.error('Erro ao carregar indicadores de tempo de casa');
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
    return <LoadingSpinner message="Carregando indicadores de tempo de casa..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de tempo de casa disponível" />;
  }

  const { average_tenure_years, average_tenure_months, tenure_ranges } = data;

  // Calcular total
  const totalEmployees = tenure_ranges?.reduce((sum, r) => sum + r.count, 0) || 0;

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
          title="Tempo Médio de Casa"
          value={formatTenure(average_tenure_years || 0, average_tenure_months || 0)}
          icon={ClockIcon}
          color="indigo"
        />
        <MetricCard
          title="Total de Colaboradores"
          value={totalEmployees}
          icon={ClockIcon}
          color="blue"
        />
        <MetricCard
          title="Faixas de Tempo"
          value={tenure_ranges?.length || 0}
          icon={ClockIcon}
          color="purple"
        />
      </div>

      {/* Faixas de Tempo de Casa */}
      {tenure_ranges && tenure_ranges.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            ⏰ Distribuição por Tempo de Casa
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {tenure_ranges.map((range, idx) => {
              const percentage = totalEmployees > 0 ? ((range.count / totalEmployees) * 100).toFixed(1) : 0;
              
              // Cores progressivas representando tempo
              const colors = [
                { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', text: 'text-green-700 dark:text-green-400', bar: 'bg-green-500' },
                { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800', text: 'text-blue-700 dark:text-blue-400', bar: 'bg-blue-500' },
                { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800', text: 'text-purple-700 dark:text-purple-400', bar: 'bg-purple-500' },
                { bg: 'bg-indigo-50 dark:bg-indigo-900/20', border: 'border-indigo-200 dark:border-indigo-800', text: 'text-indigo-700 dark:text-indigo-400', bar: 'bg-indigo-500' },
                { bg: 'bg-orange-50 dark:bg-orange-900/20', border: 'border-orange-200 dark:border-orange-800', text: 'text-orange-700 dark:text-orange-400', bar: 'bg-orange-500' },
              ];
              const color = colors[idx % colors.length];
              
              return (
                <div key={idx} className={`p-4 rounded-lg border ${color.bg} ${color.border}`}>
                  <p className={`text-sm font-medium ${color.text}`}>{range.range}</p>
                  <p className={`text-3xl font-bold ${config.classes.text} mt-2`}>{range.count}</p>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
                    <div 
                      className={`h-2 rounded-full ${color.bar}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{percentage}%</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Análise de Retenção */}
      {tenure_ranges && tenure_ranges.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📈 Análise de Retenção
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Gráfico de barras horizontal */}
            <div>
              <h4 className={`text-sm font-medium ${config.classes.textSecondary} mb-4`}>Distribuição Visual</h4>
              <div className="space-y-3">
                {tenure_ranges.map((range, idx) => {
                  const percentage = totalEmployees > 0 ? (range.count / totalEmployees) * 100 : 0;
                  return (
                    <div key={idx}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className={config.classes.text}>{range.range}</span>
                        <span className={config.classes.textSecondary}>{range.count}</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-indigo-500 h-4 rounded-full flex items-center justify-end pr-2"
                          style={{ width: `${Math.max(percentage, 5)}%` }}
                        >
                          {percentage > 10 && (
                            <span className="text-xs text-white font-medium">{percentage.toFixed(0)}%</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Insights */}
            <div>
              <h4 className={`text-sm font-medium ${config.classes.textSecondary} mb-4`}>Insights</h4>
              <div className="space-y-4">
                {/* Maior concentração */}
                {(() => {
                  const maxRange = tenure_ranges.reduce((max, r) => r.count > max.count ? r : max, tenure_ranges[0]);
                  const percentage = totalEmployees > 0 ? ((maxRange.count / totalEmployees) * 100).toFixed(1) : 0;
                  return (
                    <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                      <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">📊 Maior Concentração</p>
                      <p className={`text-lg font-bold ${config.classes.text} mt-1`}>{maxRange.range}</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {maxRange.count} colaboradores ({percentage}%)
                      </p>
                    </div>
                  );
                })()}

                {/* Colaboradores veteranos (> 5 anos) */}
                {(() => {
                  const veteranos = tenure_ranges
                    .filter(r => {
                      const match = r.range.match(/(\d+)/);
                      return match && parseInt(match[1]) >= 5;
                    })
                    .reduce((sum, r) => sum + r.count, 0);
                  const percentage = totalEmployees > 0 ? ((veteranos / totalEmployees) * 100).toFixed(1) : 0;
                  return (
                    <div className="p-4 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800">
                      <p className="text-sm text-indigo-600 dark:text-indigo-400 font-medium">🏆 Veteranos (5+ anos)</p>
                      <p className={`text-lg font-bold ${config.classes.text} mt-1`}>{veteranos} colaboradores</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {percentage}% do total
                      </p>
                    </div>
                  );
                })()}

                {/* Novos colaboradores (< 1 ano) */}
                {(() => {
                  const novos = tenure_ranges
                    .filter(r => r.range.toLowerCase().includes('< 1') || r.range.toLowerCase().includes('menos de 1'))
                    .reduce((sum, r) => sum + r.count, 0);
                  const percentage = totalEmployees > 0 ? ((novos / totalEmployees) * 100).toFixed(1) : 0;
                  return (
                    <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                      <p className="text-sm text-green-600 dark:text-green-400 font-medium">🌱 Novos (&lt; 1 ano)</p>
                      <p className={`text-lg font-bold ${config.classes.text} mt-1`}>{novos} colaboradores</p>
                      <p className="text-sm text-gray-500 mt-1">
                        {percentage}% do total
                      </p>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tenure;
