import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  UsersIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState, translateLabel } from './components';

const Demographics = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/demographics');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar demografia:', error);
      toast.error('Erro ao carregar indicadores demográficos');
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
    return <LoadingSpinner message="Carregando indicadores demográficos..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado demográfico disponível" />;
  }

  const { by_sex, age_ranges, average_age } = data;

  // Calcular totais por sexo
  const totalBySex = by_sex?.reduce((sum, s) => sum + s.count, 0) || 0;

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
          title="Idade Média"
          value={average_age || 0}
          unit="anos"
          icon={UsersIcon}
          color="yellow"
        />
        <MetricCard
          title="Total de Colaboradores"
          value={totalBySex}
          icon={UsersIcon}
          color="blue"
        />
        <MetricCard
          title="Faixas Etárias"
          value={age_ranges?.length || 0}
          icon={UsersIcon}
          color="purple"
        />
      </div>

      {/* Distribuição por Sexo */}
      {by_sex && by_sex.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            👥 Distribuição por Sexo
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {by_sex.map((item, idx) => {
              const percentage = totalBySex > 0 ? ((item.count / totalBySex) * 100).toFixed(1) : 0;
              const isMale = item.sex === 'M';
              return (
                <div 
                  key={idx} 
                  className={`p-6 rounded-lg border ${
                    isMale 
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' 
                      : 'bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className={`text-lg font-medium ${isMale ? 'text-blue-700 dark:text-blue-400' : 'text-pink-700 dark:text-pink-400'}`}>
                      {isMale ? '👨 Masculino' : '👩 Feminino'}
                    </span>
                    <span className={`text-3xl font-bold ${isMale ? 'text-blue-700 dark:text-blue-300' : 'text-pink-700 dark:text-pink-300'}`}>
                      {item.count}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div 
                      className={`h-3 rounded-full ${isMale ? 'bg-blue-500' : 'bg-pink-500'}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <p className={`text-sm mt-2 ${config.classes.textSecondary}`}>
                    {percentage}% do total
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Faixas Etárias */}
      {age_ranges && age_ranges.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📊 Distribuição por Faixa Etária
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {age_ranges.map((range, idx) => {
              const totalRange = age_ranges.reduce((sum, r) => sum + r.count, 0);
              const percentage = totalRange > 0 ? ((range.count / totalRange) * 100).toFixed(1) : 0;
              
              // Cores progressivas por faixa
              const colors = [
                'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
                'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
                'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
                'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
                'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
              ];
              
              return (
                <div key={idx} className={`p-4 rounded-lg border ${colors[idx % colors.length]}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>{range.range}</p>
                  <p className={`text-3xl font-bold ${config.classes.text} mt-2`}>{range.count}</p>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full"
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

      {/* Análise Demográfica */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          📈 Análise Demográfica
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Resumo por Sexo */}
          {by_sex && by_sex.length > 0 && (
            <div>
              <h4 className={`text-sm font-medium ${config.classes.textSecondary} mb-3`}>Proporção por Sexo</h4>
              <div className="flex h-8 rounded-full overflow-hidden">
                {by_sex.map((item, idx) => {
                  const percentage = totalBySex > 0 ? (item.count / totalBySex) * 100 : 0;
                  const isMale = item.sex === 'M';
                  return (
                    <div 
                      key={idx}
                      className={`flex items-center justify-center text-xs font-medium text-white ${
                        isMale ? 'bg-blue-500' : 'bg-pink-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    >
                      {percentage > 15 && `${percentage.toFixed(0)}%`}
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-2 text-xs">
                {by_sex.map((item, idx) => (
                  <span key={idx} className={config.classes.textSecondary}>
                    {translateLabel(item.sex)}: {item.count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Faixa mais populosa */}
          {age_ranges && age_ranges.length > 0 && (
            <div>
              <h4 className={`text-sm font-medium ${config.classes.textSecondary} mb-3`}>Maior Faixa Etária</h4>
              {(() => {
                const maxRange = age_ranges.reduce((max, r) => r.count > max.count ? r : max, age_ranges[0]);
                const totalRange = age_ranges.reduce((sum, r) => sum + r.count, 0);
                const percentage = totalRange > 0 ? ((maxRange.count / totalRange) * 100).toFixed(1) : 0;
                return (
                  <div className="p-4 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white">
                    <p className="text-2xl font-bold">{maxRange.range}</p>
                    <p className="text-sm opacity-90 mt-1">
                      {maxRange.count} colaboradores ({percentage}%)
                    </p>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Demographics;
