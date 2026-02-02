import React, { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CalendarIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';

const Overview = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState('all');
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [availablePeriods, setAvailablePeriods] = useState([]);

  useEffect(() => {
    loadAvailablePeriods();
  }, []);

  useEffect(() => {
    if (selectedPeriod || availablePeriods.length > 0) {
      loadOverviewData();
    }
  }, [selectedCompany, selectedPeriod, availablePeriods]);

  const loadAvailablePeriods = async () => {
    try {
      const response = await api.get('/payroll/periods');
      const periods = response.data.periods || [];
      setAvailablePeriods(periods);
      
      // Selecionar o período mais recente por padrão
      if (periods.length > 0 && !selectedPeriod) {
        const mostRecent = periods.reduce((latest, p) => {
          const latestDate = new Date(latest.year, latest.month - 1);
          const currentDate = new Date(p.year, p.month - 1);
          return currentDate > latestDate ? p : latest;
        });
        setSelectedPeriod(mostRecent.id);
      }
    } catch (error) {
      console.error('Erro ao carregar períodos:', error);
      toast.error('Erro ao carregar períodos disponíveis');
    }
  };

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      const params = { 
        company: selectedCompany,
        period_id: selectedPeriod
      };
      
      const response = await api.get('/indicators/overview', { params });
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar visão geral:', error);
      toast.error('Erro ao carregar indicadores');
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

  const formatPercent = (value) => {
    return `${(value || 0).toFixed(1)}%`;
  };

  const getCurrentPeriod = () => {
    return availablePeriods.find(p => p.id === parseInt(selectedPeriod));
  };

  const renderMetricCard = (title, value, icon: any, color, trend = null) => {
    const Icon = icon;
    const colorClasses = {
      blue: 'bg-blue-50 text-blue-600 border-blue-200',
      green: 'bg-green-50 text-green-600 border-green-200',
      purple: 'bg-purple-50 text-purple-600 border-purple-200',
      yellow: 'bg-yellow-50 text-yellow-600 border-yellow-200',
      red: 'bg-red-50 text-red-600 border-red-200',
      indigo: 'bg-indigo-50 text-indigo-600 border-indigo-200'
    };

    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
          {trend !== null && (
            <div className={`flex items-center text-sm ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend >= 0 ? (
                <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
              )}
              {Math.abs(trend).toFixed(1)}%
            </div>
          )}
        </div>
        <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <svg className="animate-spin h-10 w-10 text-indigo-600" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    );
  }

  const currentPeriod = getCurrentPeriod();

  return (
    <div className="space-y-6">
      {/* Header com filtros */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <ChartBarIcon className="h-8 w-8 mr-3 text-indigo-600" />
            Visão Geral - Indicadores RH
          </h1>
          {currentPeriod && (
            <p className="text-gray-600 mt-1">
              Período: {currentPeriod.period_name} ({String(currentPeriod.month).padStart(2, '0')}/{currentPeriod.year})
            </p>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-sm font-medium text-gray-700">Período:</label>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {availablePeriods.map(period => (
              <option key={period.id} value={period.id}>
                {period.period_name} - {String(period.month).padStart(2, '0')}/{period.year}
              </option>
            ))}
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

      {/* Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {renderMetricCard(
          'Total de Colaboradores',
          data?.total_employees || 0,
          UserGroupIcon,
          'blue',
          data?.employee_variation
        )}
        {renderMetricCard(
          'Custo de Folha Total',
          formatCurrency(data?.total_payroll_cost || 0),
          CurrencyDollarIcon,
          'green',
          data?.cost_variation
        )}
        {renderMetricCard(
          'Admissões no Período',
          data?.admissions || 0,
          ArrowTrendingUpIcon,
          'indigo'
        )}
        {renderMetricCard(
          'Desligamentos no Período',
          data?.terminations || 0,
          ArrowTrendingDownIcon,
          'red'
        )}
      </div>

      {/* Distribuição por Empresa */}
      {data?.by_company && data.by_company.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <BuildingOfficeIcon className="h-6 w-6 mr-2 text-indigo-600" />
            Distribuição por Empresa
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.by_company.map((company, idx) => (
              <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-600">
                      {company.company === '0060' ? 'Empreendimentos' : 'Infraestrutura'}
                    </p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{company.count} colaboradores</p>
                    <p className="text-sm text-gray-500 mt-1">
                      Folha: {formatCurrency(company.total_cost)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-indigo-600">
                      {((company.count / data.total_employees) * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top 5 Setores */}
      {data?.top_divisions && data.top_divisions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            📊 Top 5 Setores por Quantidade de Colaboradores
          </h3>
          <div className="space-y-3">
            {data.top_divisions.map((division, idx) => (
              <div key={idx} className="flex items-center">
                <div className="w-8 h-8 flex items-center justify-center bg-indigo-100 text-indigo-600 rounded-full font-bold text-sm mr-3">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-700">{division.division || 'Não informado'}</span>
                    <span className="text-sm font-semibold text-gray-900">{division.count} colaboradores</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full"
                      style={{ width: `${(division.count / data.total_employees) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Movimentações */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          📈 Resumo de Movimentações
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-green-50 border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600 font-medium">Admissões</p>
                <p className="text-3xl font-bold text-green-700 mt-2">{data?.admissions || 0}</p>
              </div>
              <ArrowTrendingUpIcon className="h-12 w-12 text-green-400" />
            </div>
          </div>
          
          <div className="p-4 rounded-lg bg-red-50 border border-red-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600 font-medium">Desligamentos</p>
                <p className="text-3xl font-bold text-red-700 mt-2">{data?.terminations || 0}</p>
              </div>
              <ArrowTrendingDownIcon className="h-12 w-12 text-red-400" />
            </div>
          </div>
          
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-medium">Saldo Líquido</p>
                <p className={`text-3xl font-bold mt-2 ${
                  (data?.admissions || 0) - (data?.terminations || 0) >= 0 ? 'text-blue-700' : 'text-red-700'
                }`}>
                  {((data?.admissions || 0) - (data?.terminations || 0)) >= 0 ? '+' : ''}
                  {(data?.admissions || 0) - (data?.terminations || 0)}
                </p>
              </div>
              <CalendarIcon className="h-12 w-12 text-blue-400" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
