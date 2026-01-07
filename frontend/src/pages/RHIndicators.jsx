import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import api from '../services/api';
import toast from 'react-hot-toast';

const RHIndicators = () => {
  const { config } = useTheme();
  const [activeCategory, setActiveCategory] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [indicatorsData, setIndicatorsData] = useState(null);

  // Carregar dados ao montar ou trocar categoria
  useEffect(() => {
    loadIndicators();
  }, [activeCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadIndicators = useCallback(async () => {
    setLoading(true);
    try {
      let response;
      
      switch (activeCategory) {
        case 'overview':
          response = await api.get('/indicators/overview');
          break;
        case 'headcount':
          response = await api.get('/indicators/headcount');
          break;
        case 'turnover':
          response = await api.get('/indicators/turnover');
          break;
        case 'demographics':
          response = await api.get('/indicators/demographics');
          break;
        case 'tenure':
          response = await api.get('/indicators/tenure');
          break;
        case 'leaves':
          response = await api.get('/indicators/leaves');
          break;
        default:
          response = await api.get('/indicators/overview');
      }
      
      setIndicatorsData(response.data);
    } catch (error) {
      console.error('Erro ao carregar indicadores:', error);
      toast.error('Erro ao carregar indicadores de RH');
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  const refreshIndicators = async () => {
    // Invalidar cache no backend primeiro
    try {
      await api.post('/indicators/cache/invalidate');
      toast.success('Cache invalidado, recalculando...');
    } catch (error) {
      console.error('Erro ao invalidar cache:', error);
    }
    
    // Recarregar dados
    await loadIndicators();
    toast.success('Indicadores atualizados!');
  };

  // Função para traduzir labels técnicos para português
  const translateLabel = (key) => {
    const translations = {
      // Headcount/Efetivo
      'total_active': 'Total de Colaboradores Ativos',
      'by_department': 'Por Departamento',
      'by_sector': 'Por Setor',
      'by_company': 'Por Empresa',
      'by_contract_type': 'Por Tipo de Contrato',
      'by_employment_status': 'Por Status de Emprego',
      'department': 'Departamento',
      'sector': 'Setor',
      'company_code': 'Código da Empresa',
      'contract_type': 'Tipo de Contrato',
      'employment_status': 'Status de Emprego',
      'count': 'Quantidade',
      
      // Turnover/Rotatividade
      'period': 'Período',
      'start': 'Início',
      'end': 'Fim',
      'headcount': 'Efetivo',
      'average': 'Média',
      'movements': 'Movimentações',
      'admissions': 'Admissões',
      'terminations': 'Desligamentos',
      'rates': 'Taxas',
      'turnover': 'Rotatividade',
      'admission': 'Admissão',
      'termination': 'Desligamento',
      'termination_reasons': 'Motivos de Desligamento',
      'turnover_by_department': 'Rotatividade por Departamento',
      'reason': 'Motivo',
      
      // Demografia
      'by_sex': 'Por Sexo',
      'age_ranges': 'Faixas Etárias',
      'average_age': 'Idade Média',
      'sex': 'Sexo',
      'range': 'Faixa',
      'M': 'Masculino',
      'F': 'Feminino',
      
      // Tempo de Casa/Tenure
      'average_tenure_years': 'Tempo Médio de Casa (anos)',
      'tenure_ranges': 'Faixas de Tempo de Casa',
      'avg_years': 'Média (anos)',
      
      // Afastamentos/Leaves
      'currently_on_leave': 'Atualmente Afastados',
      'by_leave_type': 'Por Tipo de Afastamento',
      'by_leave_reason': 'Por Motivo de Afastamento',
      'leave_type': 'Tipo de Afastamento',
      'leave_reason': 'Motivo de Afastamento'
    };
    
    return translations[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Função para formatar tempo (anos/meses)
  const formatTenure = (years, months) => {
    if (!years && !months) return '0 meses';
    
    if (years >= 1) {
      const remainingMonths = months ? months % 12 : 0;
      if (remainingMonths === 0) {
        return years === 1 ? '1 ano' : `${years} anos`;
      }
      return `${years} ${years === 1 ? 'ano' : 'anos'} e ${remainingMonths} ${remainingMonths === 1 ? 'mês' : 'meses'}`;
    }
    
    return `${months} ${months === 1 ? 'mês' : 'meses'}`;
  };


  const categories = [
    { id: 'overview', name: 'Visão Geral', icon: ChartBarIcon, color: 'blue' },
    { id: 'headcount', name: 'Efetivo', icon: UserGroupIcon, color: 'green' },
    { id: 'turnover', name: 'Rotatividade', icon: ArrowPathIcon, color: 'purple' },
    { id: 'demographics', name: 'Demografia', icon: UserGroupIcon, color: 'yellow' },
    { id: 'tenure', name: 'Tempo de Casa', icon: ClockIcon, color: 'indigo' },
    { id: 'leaves', name: 'Afastamentos', icon: ExclamationTriangleIcon, color: 'pink' }
  ];

  const MetricCard = ({ title, value, unit, trend, trendValue, icon: Icon, color = 'blue' }) => {
    const colorClasses = {
      blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
      green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
      purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
      yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
      indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
      pink: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400'
    };

    return (
      <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
          {trend && (
            <div className={`flex items-center text-sm ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {trend === 'up' ? (
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
              )}
              <span>{trendValue}%</span>
            </div>
          )}
        </div>
        <h3 className={`text-sm font-medium ${config.classes.textSecondary} mb-1`}>{title}</h3>
        <p className={`text-3xl font-bold ${config.classes.text}`}>
          {value}
          {unit && <span className="text-lg ml-1">{unit}</span>}
        </p>
      </div>
    );
  };

  const renderOverview = () => {
    if (!indicatorsData?.headcount) return null;
    
    const { headcount, turnover, tenure, leaves } = indicatorsData;
    
    return (
      <div className="space-y-6">
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
              Efetivo por Departamento
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
        {indicatorsData.demographics?.age_ranges && (
          <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
            <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
              Distribuição por Faixa Etária
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {indicatorsData.demographics.age_ranges.map((range, idx) => (
                <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                  <p className={`text-sm ${config.classes.textSecondary}`}>{range.range}</p>
                  <p className={`text-2xl font-bold ${config.classes.text}`}>{range.count}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <span className={`ml-4 text-lg ${config.classes.textSecondary}`}>Carregando indicadores...</span>
        </div>
      );
    }

    if (!indicatorsData) {
      return (
        <div className={`${config.classes.card} rounded-lg shadow p-8 text-center`}>
          <ExclamationTriangleIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <p className={config.classes.text}>Nenhum dado disponível</p>
        </div>
      );
    }

    if (activeCategory === 'overview') {
      return renderOverview();
    }

    // Renderizar dados específicos de cada categoria
    const metrics = indicatorsData.metrics || indicatorsData;
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(metrics).map(([key, value]) => {
            if (typeof value === 'object' && !Array.isArray(value)) return null;
            if (Array.isArray(value)) return null;
            
            // Formatação especial para campos específicos
            let displayValue = value;
            let displayUnit = '';
            
            if (key === 'average_age') {
              displayValue = value;
              displayUnit = value === 1 ? 'ano' : 'anos';
            } else if (key === 'average_tenure_years') {
              displayValue = formatTenure(indicatorsData.metrics?.average_tenure_years, indicatorsData.metrics?.average_tenure_months);
            } else if (typeof value === 'number') {
              displayValue = Number.isInteger(value) ? value : value.toFixed(2);
            }
            
            return (
              <MetricCard
                key={key}
                title={translateLabel(key)}
                value={displayValue}
                unit={displayUnit}
                icon={ChartBarIcon}
                color="blue"
              />
            );
          })}
        </div>

        {/* Renderizar arrays/objetos como tabelas */}
        {Object.entries(metrics).map(([key, value]) => {
          if (!Array.isArray(value) || value.length === 0) return null;
          
          return (
            <div key={key} className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
                {translateLabel(key)}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {value.map((item, idx) => (
                  <div key={idx} className={`p-3 rounded-lg ${config.classes.background} border ${config.classes.border}`}>
                    {Object.entries(item).map(([k, v]) => (
                      <div key={k}>
                        <p className={`text-xs ${config.classes.textSecondary}`}>{translateLabel(k)}</p>
                        <p className={`text-lg font-semibold ${config.classes.text}`}>
                          {typeof v === 'number' 
                            ? (Number.isInteger(v) ? v : v.toFixed(2)) 
                            : (translateLabel(String(v)) || v)}
                        </p>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className={`min-h-screen ${config.classes.background}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`text-3xl font-bold ${config.classes.text}`}>
                📊 Indicadores de RH
              </h1>
              <p className={`mt-2 text-sm ${config.classes.textSecondary}`}>
                Métricas e KPIs para gestão estratégica de pessoas
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {indicatorsData?.cached && (
                <div className={`flex items-center px-4 py-2 rounded-lg ${config.classes.card} ${config.classes.border}`}>
                  <span className="h-2 w-2 bg-green-500 rounded-full mr-2"></span>
                  <span className={`text-sm font-medium ${config.classes.text}`}>
                    Cache Ativo
                  </span>
                </div>
              )}
              <button
                onClick={refreshIndicators}
                disabled={loading}
                className={`flex items-center px-4 py-2 rounded-lg ${config.classes.card} ${config.classes.border} hover:${config.classes.cardHover} transition-colors`}
              >
                <ArrowPathIcon className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
                <span className={`text-sm font-medium ${config.classes.text}`}>
                  {loading ? 'Atualizando...' : 'Atualizar'}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="mb-8 overflow-x-auto">
          <div className="flex space-x-2 min-w-max">
            {categories.map((category) => {
              const Icon = category.icon;
              const isActive = activeCategory === category.id;
              return (
                <button
                  key={category.id}
                  onClick={() => setActiveCategory(category.id)}
                  className={`flex items-center px-4 py-3 rounded-lg font-medium transition-colors ${
                    isActive
                      ? `${config.classes.card} ${config.classes.border} shadow-md ${config.classes.text}`
                      : `${config.classes.cardHover} ${config.classes.textSecondary} hover:${config.classes.text}`
                  }`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {category.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="mb-8">
          {renderContent()}
        </div>

        {/* Info sobre cache e cálculos */}
        {indicatorsData && (
          <div className={`${config.classes.card} rounded-lg shadow-md p-4 ${config.classes.border}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <ChartBarIcon className="h-5 w-5 text-blue-500 mr-3" />
                <div>
                  <p className={`text-sm font-medium ${config.classes.text}`}>
                    {indicatorsData.cached ? '✅ Dados em cache' : '🔄 Dados recém-calculados'}
                  </p>
                  <p className={`text-xs ${config.classes.textSecondary}`}>
                    {indicatorsData.calculation_time_ms && `Tempo de processamento: ${indicatorsData.calculation_time_ms}ms`}
                    {indicatorsData.total_records && ` • ${indicatorsData.total_records} registros`}
                  </p>
                </div>
              </div>
              {indicatorsData.cached_at && (
                <p className={`text-xs ${config.classes.textSecondary}`}>
                  Última atualização: {new Date(indicatorsData.cached_at).toLocaleString('pt-BR')}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RHIndicators;

