import React, { useState, useEffect } from 'react';
import { UserGroupIcon, ChartBarIcon, CurrencyDollarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import { Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area } from 'recharts';
import api from '../../services/api';
import toast from 'react-hot-toast';
import ExportPDFButton from '../../components/ExportPDFButton';

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#6366f1'];

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
      indigo: 'bg-indigo-500',
      red: 'bg-red-500'
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
        <ExportPDFButton className="no-print" />
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {renderMetricCard('Headcount Atual', data.current?.headcount || 0, UserGroupIcon, 'blue', data.current?.variation_vs_previous)}
            {renderMetricCard('Líquido Médio por Colaborador', formatCurrency(data.current?.avg_cost_per_employee || 0), ChartBarIcon, 'indigo')}
            {renderMetricCard('Maior Setor', data.top_divisions?.[0]?.division || 'N/A', BuildingOfficeIcon, 'yellow')}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {renderMetricCard('Total de Proventos', formatCurrency(data.current?.total_earnings || 0), ArrowTrendingUpIcon, 'blue')}
            {renderMetricCard('Total de Descontos', formatCurrency(data.current?.total_deductions || 0), ArrowTrendingDownIcon, 'red')}
            {renderMetricCard('Total Líquido', formatCurrency(data.current?.total_cost || 0), CurrencyDollarIcon, 'green')}
          </div>

          {data.evolution && data.evolution.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <ChartBarIcon className="h-6 w-6 mr-2 text-indigo-600" />
                Evolução (Últimos {monthsRange} meses)
              </h3>
              <div className="h-80 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={data.evolution || []} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                    <XAxis dataKey="month_name" axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" axisLine={false} tickLine={false} tickFormatter={(value) => new Intl.NumberFormat('pt-BR', { notation: 'compact', compactDisplay: 'short', style: 'currency', currency: 'BRL' }).format(value)} />
                    <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} />
                    <Tooltip 
                      formatter={(value, name) => {
                        if (name === 'Colaboradores') return [value, name];
                        return [formatCurrency(value), name];
                      }}
                      labelStyle={{ color: '#374151', fontWeight: 'bold' }}
                    />
                    <Legend />
                    <Line yAxisId="right" type="monotone" dataKey="headcount" name="Colaboradores" stroke="#f59e0b" strokeWidth={3} dot={{ r: 4 }} />
                    <Area yAxisId="left" type="monotone" dataKey="total_earnings" name="Total Proventos" fill="#10b981" stroke="#10b981" fillOpacity={0.1} />
                    <Line yAxisId="left" type="monotone" dataKey="total_deductions" name="Total Descontos" stroke="#ef4444" strokeWidth={2} />
                    <Area yAxisId="left" type="monotone" dataKey="total_cost" name="Total Líquido" fill="#4f46e5" stroke="#4f46e5" fillOpacity={0.1} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {data.by_company && data.by_company.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <BuildingOfficeIcon className="h-6 w-6 mr-2 text-indigo-600" />
                  Distribuição por Empresa
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.by_company.map(c => ({
                          name: c.company === '0060' ? 'Empreendimentos' : 'Infraestrutura',
                          value: c.headcount
                        }))}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {data.by_company.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => [`${value} colaboradores`, 'Headcount']} />
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {data.top_divisions && data.top_divisions.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6 lg:col-span-2">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Top Setores</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={data.top_divisions.slice(0, 5).reverse()}
                      margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                      <XAxis type="number" />
                      <YAxis dataKey="division" type="category" width={160} tick={{fontSize: 12}} />
                      <Tooltip formatter={(value) => [value, 'Colaboradores']} />
                      <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]}>
                        {data.top_divisions.slice(0, 5).reverse().map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {data.top_positions && data.top_positions.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Top 10 Cargos</h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={data.top_positions.slice(0, 10).reverse()}
                      margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                      <XAxis type="number" />
                      <YAxis dataKey="position" type="category" width={180} tick={{fontSize: 12}} />
                      <Tooltip formatter={(value) => [value, 'Colaboradores']} />
                      <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
