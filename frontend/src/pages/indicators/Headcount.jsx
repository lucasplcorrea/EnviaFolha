import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  UserGroupIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState, translateLabel } from './components';

const Headcount = () => {
  const { config } = useTheme();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/headcount');
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar efetivo:', error);
      toast.error('Erro ao carregar indicadores de efetivo');
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
    return <LoadingSpinner message="Carregando indicadores de efetivo..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de efetivo disponível" />;
  }

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

      {/* Total de Colaboradores */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Total de Colaboradores Ativos"
          value={data.total_active || 0}
          icon={UserGroupIcon}
          color="blue"
        />
        <MetricCard
          title="Departamentos"
          value={data.by_department?.length || 0}
          icon={BuildingOfficeIcon}
          color="green"
        />
        <MetricCard
          title="Setores"
          value={data.by_sector?.length || 0}
          icon={BuildingOfficeIcon}
          color="purple"
        />
      </div>

      {/* Por Departamento */}
      {data.by_department && data.by_department.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            🏢 Efetivo por Departamento
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {data.by_department.map((dept, idx) => (
              <div key={idx} className={`p-4 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-sm ${config.classes.textSecondary} truncate`}>{dept.department || 'Não informado'}</p>
                <p className={`text-2xl font-bold ${config.classes.text} mt-1`}>{dept.count}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {data.total_active > 0 ? ((dept.count / data.total_active) * 100).toFixed(1) : 0}% do total
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Por Setor */}
      {data.by_sector && data.by_sector.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📍 Efetivo por Setor
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {data.by_sector.slice(0, 18).map((sector, idx) => (
              <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-xs ${config.classes.textSecondary} truncate`}>{sector.sector || 'Não informado'}</p>
                <p className={`text-xl font-bold ${config.classes.text}`}>{sector.count}</p>
              </div>
            ))}
            {data.by_sector.length > 18 && (
              <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-700 border ${config.classes.border} flex items-center justify-center`}>
                <p className={`text-sm ${config.classes.textSecondary}`}>+{data.by_sector.length - 18} setores</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Por Tipo de Contrato */}
      {data.by_contract_type && data.by_contract_type.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📋 Por Tipo de Contrato
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.by_contract_type.map((contract, idx) => (
              <div key={idx} className={`p-4 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-sm ${config.classes.textSecondary}`}>{translateLabel(contract.contract_type) || 'Não informado'}</p>
                <p className={`text-2xl font-bold ${config.classes.text} mt-1`}>{contract.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Por Status de Emprego */}
      {data.by_employment_status && data.by_employment_status.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📊 Por Status de Emprego
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.by_employment_status.map((status, idx) => (
              <div key={idx} className={`p-4 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                <p className={`text-sm ${config.classes.textSecondary}`}>{translateLabel(status.employment_status) || 'Não informado'}</p>
                <p className={`text-2xl font-bold ${config.classes.text} mt-1`}>{status.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Headcount;
