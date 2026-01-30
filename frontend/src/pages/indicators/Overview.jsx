import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState, formatTenure } from './components';

const Overview = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/overview');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar visão geral:', error);
      toast.error('Erro ao carregar indicadores');
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
    return <LoadingSpinner message="Carregando visão geral..." />;
  }

  if (!data?.headcount) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado disponível" />;
  }

  const { headcount, turnover, tenure, leaves, demographics } = data;

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

      {/* Métricas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total de Colaboradores"
          value={headcount.total_active}
          icon={UserGroupIcon}
          color="blue"
        />
        <MetricCard
          title="Taxa de Rotatividade"
          value={turnover.rates?.turnover || 0}
          unit="%"
          icon={ArrowPathIcon}
          color="green"
        />
        <MetricCard
          title="Tempo Médio de Casa"
          value={formatTenure(tenure.average_tenure_years || 0, tenure.average_tenure_months || 0)}
          icon={ClockIcon}
          color="purple"
        />
        <MetricCard
          title="Colaboradores Afastados"
          value={leaves.currently_on_leave || 0}
          icon={ExclamationTriangleIcon}
          color="yellow"
        />
      </div>

      {/* Distribuição por Departamento */}
      {headcount.by_department && headcount.by_department.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            👥 Efetivo por Departamento
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {headcount.by_department.map((dept, idx) => (
              <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-sm ${config.classes.textSecondary}`}>{dept.department || 'Não informado'}</p>
                <p className={`text-2xl font-bold ${config.classes.text}`}>{dept.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Faixas Etárias */}
      {demographics?.age_ranges && demographics.age_ranges.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📊 Distribuição por Faixa Etária
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {demographics.age_ranges.map((range, idx) => (
              <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-sm ${config.classes.textSecondary}`}>{range.range}</p>
                <p className={`text-2xl font-bold ${config.classes.text}`}>{range.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Movimentações recentes */}
      {turnover.movements && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📈 Movimentações Recentes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">Admissões</p>
              <p className="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">
                {turnover.movements.admissions || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-600 dark:text-red-400 font-medium">Desligamentos</p>
              <p className="text-3xl font-bold text-red-700 dark:text-red-300 mt-2">
                {turnover.movements.terminations || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Saldo</p>
              <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                {(turnover.movements.admissions || 0) - (turnover.movements.terminations || 0)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Overview;
