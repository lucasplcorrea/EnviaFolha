import React, { useState, useEffect } from 'react';
import { UserGroupIcon, ChartBarIcon, CurrencyDollarIcon, ArrowTrendingUpIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';

export default function Headcount() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState('all');
  const [selectedDivision, setSelectedDivision] = useState('all');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [monthsRange, setMonthsRange] = useState(12);
  const [availableYears, setAvailableYears] = useState([]);
  const [availableMonths, setAvailableMonths] = useState([]);
  const [availableDivisions, setAvailableDivisions] = useState([]);

  useEffect(() => {
    loadFilters();
  }, []);

  useEffect(() => {
    if (selectedYear && selectedMonth) {
      loadHeadcountData();
    }
  }, [selectedCompany, selectedDivision, selectedYear, selectedMonth, monthsRange]);

  const loadFilters = async () => {
    try {
      const yearsResponse = await api.get('/payroll/years');
      const years = yearsResponse.data.years || [];
      setAvailableYears(years);
      
      const monthsResponse = await api.get('/payroll/months');
      const monthsData = monthsResponse.data.months || [];
      setAvailableMonths(monthsData);
      
      const divisionsResponse = await api.get('/payroll/divisions');
      const divisionsData = divisionsResponse.data.departments || [];
      const divisions = divisionsData.map(d => d.name);
      setAvailableDivisions(divisions);
      
      if (years.length > 0 && !selectedYear) {
        setSelectedYear(Math.max(...years).toString());
      }
      if (monthsData.length > 0 && !selectedMonth) {
        const maxMonth = Math.max(...monthsData.map(m => m.number));
        setSelectedMonth(maxMonth.toString());
      }
    } catch (error) {
      console.error('Erro ao carregar filtros:', error);
      toast.error('Erro ao carregar filtros');
    }
  };

  const loadHeadcountData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/indicators/headcount', {
        params: {
          company: selectedCompany,
          division: selectedDivision,
          year: selectedYear,
          month: selectedMonth,
          months_range: monthsRange
        }
      });
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar dados de headcount:', error);
      toast.error('Erro ao carregar dados de headcount');
    } finally {
      setLoading(false);
    }
  };

  const getMonthName = (monthNum) => {
    const months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    return months[monthNum - 1] || '';
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return 'N/A';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  const renderMetricCard = (title, value, icon, color, trend = null) => {
    const Icon = icon;
    const colorClasses = {
      blue: 'bg-blue-500',
      green: 'bg-green-500',
      yellow: 'bg-yellow-500',
      indigo: 'bg-indigo-500'
    };

    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-2">{value}</p>
            {trend !== null && trend !== undefined && (
              <p className={`text-sm mt-1 ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercent(trend)} vs mês anterior
              </p>
            )}
          </div>
          <div className={`${colorClasses[color]} p-3 rounded-full`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <UserGroupIcon className="h-8 w-8 mr-3 text-indigo-600" />
            Headcount - Quadro de Pessoal
          </h1>
          {selectedYear && selectedMonth && (
            <p className="text-gray-600 mt-1">
              Período: {getMonthName(parseInt(selectedMonth))} de {selectedYear}
            </p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
            <select value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="">Selecione...</option>
              {availableYears.map(year => <option key={year} value={year}>{year}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
            <select value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="">Selecione...</option>
              {availableMonths.map(month => <option key={month.number} value={month.number}>{month.name}</option>)}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
            <select value={selectedCompany} onChange={(e) => setSelectedCompany(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="all">Todas</option>
              <option value="0060">0060 - Empreendimentos</option>
              <option value="0059">0059 - Infraestrutura</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
            <select value={selectedDivision} onChange={(e) => setSelectedDivision(e.target.value)} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="all">Todos</option>
              {availableDivisions.map((division, idx) => <option key={idx} value={division}>{division}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Evolução (meses)</label>
            <select value={monthsRange} onChange={(e) => setMonthsRange(parseInt(e.target.value))} className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="6">6 meses</option>
              <option value="12">12 meses</option>
              <option value="18">18 meses</option>
              <option value="24">24 meses</option>
            </select>
          </div>
        </div>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {renderMetricCard('Headcount Atual', data.current?.headcount || 0, UserGroupIcon, 'blue', data.current?.variation_vs_previous)}
            {renderMetricCard('Custo Total (Salário Líquido)', formatCurrency(data.current?.total_cost || 0), CurrencyDollarIcon, 'green')}
            {renderMetricCard('Custo Médio por Colaborador', formatCurrency(data.current?.avg_cost_per_employee || 0), ChartBarIcon, 'indigo')}
            {renderMetricCard('Setor com Mais Colaboradores', data.top_divisions?.[0]?.division || 'N/A', ArrowTrendingUpIcon, 'yellow')}
          </div>

          {data.evolution && data.evolution.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <ChartBarIcon className="h-6 w-6 mr-2 text-indigo-600" />
                Evolução do Headcount (Últimos {monthsRange} meses)
              </h3>
              <div className="space-y-2">
                {[...data.evolution].reverse().map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b">
                    <span className="font-medium text-gray-700">{item.month_name}</span>
                    <div className="flex items-center space-x-4">
                      <span className="text-indigo-600 font-bold">{item.headcount} colaboradores</span>
                      <span className="text-gray-600">{formatCurrency(item.total_cost)}</span>
                      <span className="text-sm text-gray-500">{formatCurrency(item.avg_cost_per_employee)}/pessoa</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {data.by_company && data.by_company.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <BuildingOfficeIcon className="h-6 w-6 mr-2 text-indigo-600" />
                  Distribuição por Empresa
                </h3>
                <div className="space-y-3">
                  {data.by_company.map((comp, idx) => (
                    <div key={idx} className="flex justify-between items-center">
                      <span className="font-medium text-gray-700">{comp.company === '0060' ? 'Empreendimentos' : 'Infraestrutura'}</span>
                      <div className="text-right">
                        <div className="text-indigo-600 font-bold">{comp.headcount} colaboradores</div>
                        <div className="text-sm text-gray-600">{formatCurrency(comp.total_cost)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data.top_divisions && data.top_divisions.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Top 10 Setores</h3>
                <div className="space-y-2">
                  {data.top_divisions.map((div, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b">
                      <span className="text-gray-700">{div.division}</span>
                      <span className="font-bold text-indigo-600">{div.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {data.top_positions && data.top_positions.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Top 10 Cargos</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.top_positions.map((pos, idx) => (
                  <div key={idx} className="flex justify-between items-center py-2 border-b">
                    <span className="text-gray-700">{pos.position}</span>
                    <span className="font-bold text-indigo-600">{pos.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
