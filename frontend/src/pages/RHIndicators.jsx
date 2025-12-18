import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  CurrencyDollarIcon,
  AcademicCapIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowPathIcon,
  WrenchScrewdriverIcon
} from '@heroicons/react/24/outline';

const RHIndicators = () => {
  const { config } = useTheme();
  const [activeCategory, setActiveCategory] = useState('overview');

  // Mockup data - será substituído por dados reais no futuro
  const mockData = {
    overview: {
      totalEmployees: 156,
      turnover: 2.3,
      averageTenure: 3.2,
      headcountGrowth: 8.5
    },
    recruitment: {
      openPositions: 12,
      timeToHire: 28,
      costPerHire: 3500,
      offerAcceptanceRate: 85
    },
    retention: {
      retentionRate: 94.2,
      voluntaryTurnover: 1.8,
      involuntaryTurnover: 0.5,
      criticalRoleRetention: 97.1
    },
    performance: {
      performanceReviewsCompleted: 89,
      averagePerformanceScore: 4.2,
      promotionRate: 12,
      goalCompletionRate: 78
    },
    training: {
      trainingHoursPerEmployee: 24,
      trainingCompletionRate: 92,
      trainingInvestment: 125000,
      certificationRate: 45
    },
    compensation: {
      averageSalary: 5200,
      salaryIncreaseRate: 5.5,
      benefitsCost: 890000,
      payrollAccuracy: 99.8
    }
  };

  const categories = [
    { id: 'overview', name: 'Visão Geral', icon: ChartBarIcon, color: 'blue' },
    { id: 'recruitment', name: 'Recrutamento', icon: UserGroupIcon, color: 'green' },
    { id: 'retention', name: 'Retenção', icon: ArrowPathIcon, color: 'purple' },
    { id: 'performance', name: 'Performance', icon: ArrowTrendingUpIcon, color: 'yellow' },
    { id: 'training', name: 'Treinamento', icon: AcademicCapIcon, color: 'indigo' },
    { id: 'compensation', name: 'Remuneração', icon: CurrencyDollarIcon, color: 'pink' }
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

  const renderOverview = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Total de Colaboradores"
        value={mockData.overview.totalEmployees}
        icon={UserGroupIcon}
        color="blue"
        trend="up"
        trendValue="8.5"
      />
      <MetricCard
        title="Taxa de Turnover"
        value={mockData.overview.turnover}
        unit="%"
        icon={ArrowPathIcon}
        color="green"
        trend="down"
        trendValue="0.3"
      />
      <MetricCard
        title="Tempo Médio de Casa"
        value={mockData.overview.averageTenure}
        unit="anos"
        icon={ClockIcon}
        color="purple"
        trend="up"
        trendValue="5.2"
      />
      <MetricCard
        title="Crescimento do Quadro"
        value={mockData.overview.headcountGrowth}
        unit="%"
        icon={ArrowTrendingUpIcon}
        color="yellow"
        trend="up"
        trendValue="2.1"
      />
    </div>
  );

  const renderRecruitment = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Vagas Abertas"
        value={mockData.recruitment.openPositions}
        icon={UserGroupIcon}
        color="green"
      />
      <MetricCard
        title="Tempo Médio de Contratação"
        value={mockData.recruitment.timeToHire}
        unit="dias"
        icon={ClockIcon}
        color="blue"
        trend="down"
        trendValue="5"
      />
      <MetricCard
        title="Custo por Contratação"
        value={`R$ ${mockData.recruitment.costPerHire}`}
        icon={CurrencyDollarIcon}
        color="pink"
        trend="down"
        trendValue="8"
      />
      <MetricCard
        title="Taxa de Aceitação"
        value={mockData.recruitment.offerAcceptanceRate}
        unit="%"
        icon={ArrowTrendingUpIcon}
        color="green"
        trend="up"
        trendValue="3"
      />
    </div>
  );

  const renderRetention = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Taxa de Retenção"
        value={mockData.retention.retentionRate}
        unit="%"
        icon={UserGroupIcon}
        color="green"
        trend="up"
        trendValue="1.2"
      />
      <MetricCard
        title="Turnover Voluntário"
        value={mockData.retention.voluntaryTurnover}
        unit="%"
        icon={ArrowTrendingDownIcon}
        color="yellow"
        trend="down"
        trendValue="0.3"
      />
      <MetricCard
        title="Turnover Involuntário"
        value={mockData.retention.involuntaryTurnover}
        unit="%"
        icon={ExclamationTriangleIcon}
        color="red"
      />
      <MetricCard
        title="Retenção de Funções Críticas"
        value={mockData.retention.criticalRoleRetention}
        unit="%"
        icon={ArrowTrendingUpIcon}
        color="purple"
        trend="up"
        trendValue="2.1"
      />
    </div>
  );

  const renderPerformance = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Avaliações Concluídas"
        value={mockData.performance.performanceReviewsCompleted}
        unit="%"
        icon={ChartBarIcon}
        color="blue"
      />
      <MetricCard
        title="Score Médio de Performance"
        value={mockData.performance.averagePerformanceScore}
        unit="/5"
        icon={ArrowTrendingUpIcon}
        color="green"
        trend="up"
        trendValue="3"
      />
      <MetricCard
        title="Taxa de Promoção"
        value={mockData.performance.promotionRate}
        unit="%"
        icon={ArrowTrendingUpIcon}
        color="purple"
      />
      <MetricCard
        title="Conclusão de Metas"
        value={mockData.performance.goalCompletionRate}
        unit="%"
        icon={ChartBarIcon}
        color="yellow"
        trend="up"
        trendValue="5"
      />
    </div>
  );

  const renderTraining = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Horas de Treinamento por Colaborador"
        value={mockData.training.trainingHoursPerEmployee}
        unit="h"
        icon={AcademicCapIcon}
        color="indigo"
        trend="up"
        trendValue="12"
      />
      <MetricCard
        title="Taxa de Conclusão"
        value={mockData.training.trainingCompletionRate}
        unit="%"
        icon={ChartBarIcon}
        color="green"
      />
      <MetricCard
        title="Investimento em Treinamento"
        value={`R$ ${(mockData.training.trainingInvestment / 1000).toFixed(0)}k`}
        icon={CurrencyDollarIcon}
        color="pink"
      />
      <MetricCard
        title="Taxa de Certificação"
        value={mockData.training.certificationRate}
        unit="%"
        icon={AcademicCapIcon}
        color="purple"
        trend="up"
        trendValue="8"
      />
    </div>
  );

  const renderCompensation = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Salário Médio"
        value={`R$ ${mockData.compensation.averageSalary}`}
        icon={CurrencyDollarIcon}
        color="pink"
        trend="up"
        trendValue="5.5"
      />
      <MetricCard
        title="Taxa de Aumento Salarial"
        value={mockData.compensation.salaryIncreaseRate}
        unit="%"
        icon={ArrowTrendingUpIcon}
        color="green"
      />
      <MetricCard
        title="Custo Total de Benefícios"
        value={`R$ ${(mockData.compensation.benefitsCost / 1000).toFixed(0)}k`}
        icon={CurrencyDollarIcon}
        color="blue"
      />
      <MetricCard
        title="Precisão da Folha"
        value={mockData.compensation.payrollAccuracy}
        unit="%"
        icon={ChartBarIcon}
        color="green"
      />
    </div>
  );

  const renderContent = () => {
    switch (activeCategory) {
      case 'overview':
        return renderOverview();
      case 'recruitment':
        return renderRecruitment();
      case 'retention':
        return renderRetention();
      case 'performance':
        return renderPerformance();
      case 'training':
        return renderTraining();
      case 'compensation':
        return renderCompensation();
      default:
        return renderOverview();
    }
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
            <div className={`flex items-center px-4 py-2 rounded-lg ${config.classes.card} ${config.classes.border}`}>
              <WrenchScrewdriverIcon className="h-5 w-5 text-yellow-500 mr-2" />
              <span className={`text-sm font-medium ${config.classes.text}`}>
                Mockup - Dados de Exemplo
              </span>
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

        {/* Info Banner */}
        <div className={`${config.classes.card} rounded-lg shadow-md p-6 ${config.classes.border}`}>
          <div className="flex items-start">
            <WrenchScrewdriverIcon className="h-6 w-6 text-yellow-500 mr-3 mt-1 flex-shrink-0" />
            <div>
              <h3 className={`text-lg font-semibold ${config.classes.text} mb-2`}>
                🚧 Página em Desenvolvimento
              </h3>
              <p className={`text-sm ${config.classes.textSecondary} mb-4`}>
                Esta é uma visualização mockup dos indicadores de RH. Os dados apresentados são exemplos
                para demonstração da interface e funcionalidades planejadas.
              </p>
              <div className={`${config.classes.background} rounded-lg p-4 border-l-4 border-blue-500`}>
                <h4 className={`text-sm font-semibold ${config.classes.text} mb-2`}>
                  Funcionalidades Planejadas:
                </h4>
                <ul className={`text-sm ${config.classes.textSecondary} space-y-1 list-disc list-inside`}>
                  <li>Cálculo automático de métricas com base em dados reais</li>
                  <li>Filtros por período, departamento e outros critérios</li>
                  <li>Gráficos interativos e visualizações avançadas</li>
                  <li>Exportação de relatórios em PDF e Excel</li>
                  <li>Alertas e notificações para indicadores críticos</li>
                  <li>Comparações históricas e análise de tendências</li>
                  <li>Benchmarking com métricas do mercado</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RHIndicators;

