import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline';

/**
 * Componente de Card para exibição de métricas
 */
export const MetricCard = ({ title, value, unit, trend, trendValue, icon: Icon, color = 'blue' }) => {
  const { config } = useTheme();
  
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
    pink: 'bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-400',
    emerald: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400',
    teal: 'bg-teal-100 text-teal-600 dark:bg-teal-900/30 dark:text-teal-400',
    cyan: 'bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400'
  };

  return (
    <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
      <div className="flex items-center justify-between mb-4">
        {Icon && (
          <div className={`p-3 rounded-lg ${colorClasses[color] || colorClasses.blue}`}>
            <Icon className="h-6 w-6" />
          </div>
        )}
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

/**
 * Componente de Loading Spinner
 */
export const LoadingSpinner = ({ message = 'Carregando...' }) => {
  const { config } = useTheme();
  
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      <span className={`ml-4 text-lg ${config.classes.textSecondary}`}>{message}</span>
    </div>
  );
};

/**
 * Componente de estado vazio/erro
 */
export const EmptyState = ({ icon: Icon, message = 'Nenhum dado disponível' }) => {
  const { config } = useTheme();
  
  return (
    <div className={`${config.classes.card} rounded-lg shadow p-8 text-center`}>
      {Icon && <Icon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />}
      <p className={config.classes.text}>{message}</p>
    </div>
  );
};

/**
 * Função para traduzir labels técnicos para português
 */
export const translateLabel = (key) => {
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
  
  const capitalizeProper = (str) => {
    return str.toLowerCase().replace(/^\w|\s\w/g, l => l.toUpperCase());
  };
  
  return translations[key] || capitalizeProper(key.replace(/_/g, ' '));
};

/**
 * Função para formatar tempo (anos/meses)
 */
export const formatTenure = (years, months) => {
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

/**
 * Formatar valor monetário
 */
export const formatCurrency = (value) => {
  return (value || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/**
 * Calcular porcentagem
 */
export const calcPercentage = (value, total) => {
  if (!total || total === 0) return '0.0';
  return ((value / total) * 100).toFixed(1);
};
