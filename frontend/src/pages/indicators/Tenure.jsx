import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ClockIcon,
  ExclamationTriangleIcon,
  UsersIcon,
  UserIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import ExportPDFButton from '../../components/ExportPDFButton';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState } from './components';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const Tenure = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({
    years: [],
    months: [],
    divisions: []
  });
  const [selectedFilters, setSelectedFilters] = useState({
    year: '',
    month: '',
    company: 'all',
    division: 'all',
    months_range: 12
  });
  
  const [filtersReady, setFiltersReady] = useState(false);
  const [selectedTenureRange, setSelectedTenureRange] = useState(null);
  const initialLoadDone = useRef(false);

  // Carregar filtros apenas uma vez na montagem
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    
    const loadFilters = async () => {
      try {
        const token = localStorage.getItem('token');
        
        const [yearsRes, monthsRes, divisionsRes] = await Promise.all([
          fetch('http://localhost:8002/api/v1/payroll/years', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('http://localhost:8002/api/v1/payroll/months', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('http://localhost:8002/api/v1/payroll/divisions', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);
        
        const [yearsData, monthsData, divisionsData] = await Promise.all([
          yearsRes.json(),
          monthsRes.json(),
          divisionsRes.json()
        ]);
        
        // Extrair apenas os nomes das divisões
        const divisionNames = (divisionsData.departments || []).map(d => 
          typeof d === 'object' ? d.name : d
        ).filter(Boolean);
        
        const years = yearsData.years || [];
        const months = monthsData.months || [];
        
        setFilters({
          years,
          months,
          divisions: divisionNames
        });
        
        // Selecionar período mais recente
        if (years.length > 0 && months.length > 0) {
          const latestYear = Math.max(...years);
          const latestMonth = months[months.length - 1].number;
          
          setSelectedFilters(prev => ({ 
            ...prev, 
            year: latestYear,
            month: latestMonth
          }));
          setFiltersReady(true);
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('Erro ao carregar filtros:', error);
        toast.error('Erro ao carregar filtros');
        setLoading(false);
      }
    };
    
    loadFilters();
  }, []);

  const loadData = useCallback(async () => {
    if (!selectedFilters.year || !selectedFilters.month) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams({
        company: selectedFilters.company,
        division: selectedFilters.division,
        year: selectedFilters.year,
        month: selectedFilters.month,
        months_range: selectedFilters.months_range
      });
      
      const response = await api.get(`/indicators/tenure?${params}`);
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar tempo de casa:', error);
      toast.error('Erro ao carregar indicadores de tempo de casa');
    } finally {
      setLoading(false);
    }
  }, [selectedFilters]);

  useEffect(() => {
    if (filtersReady && selectedFilters.year && selectedFilters.month) {
      loadData();
    }
  }, [filtersReady, selectedFilters, loadData]);

  const handleFilterChange = (filterName, value) => {
    setSelectedFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };

  // Preparar dados do gráfico de evolução
  const chartData = useMemo(() => {
    if (!data?.evolution) return [];
    return data.evolution;
  }, [data]);

  const sortedDepartmentData = useMemo(() => {
    if (!data?.current?.by_department) return [];
    return [...data.current.by_department].sort((a, b) => b.avg_months - a.avg_months);
  }, [data]);

  const sortedRoleData = useMemo(() => {
    if (!data?.current?.by_role) return [];
    return data.current.by_role; // já vem ordenado e quebrado top 10 do backend
  }, [data]);

  const formatTenure = (years, months) => {
    if (years === 0 && months === 0) return '0 meses';
    if (years === 0) return `${months} ${months === 1 ? 'mês' : 'meses'}`;
    if (months === 0) return `${years} ${years === 1 ? 'ano' : 'anos'}`;
    return `${years}a ${months % 12}m`;
  };

  if (loading) {
    return <LoadingSpinner message="Carregando indicadores de tempo de casa..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado de tempo de casa disponível" />;
  }

  const { current, evolution } = data;
  const { tenure_ranges, average_tenure_years, average_tenure_months, total_employees, by_gender } = current;

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
          <ExportPDFButton className="no-print" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
            <select
              value={selectedFilters.year}
              onChange={(e) => handleFilterChange('year', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione</option>
              {filters.years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
            <select
              value={selectedFilters.month}
              onChange={(e) => handleFilterChange('month', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione</option>
              {filters.months.map(month => (
                <option key={month.number} value={month.number}>{month.name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
            <select
              value={selectedFilters.company}
              onChange={(e) => handleFilterChange('company', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todas</option>
              <option value="0060">Empreendimentos</option>
              <option value="0059">Infraestrutura</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
            <select
              value={selectedFilters.division}
              onChange={(e) => handleFilterChange('division', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todos</option>
              {filters.divisions.map(division => (
                <option key={division} value={division}>{division}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Período Evolução</label>
            <select
              value={selectedFilters.months_range}
              onChange={(e) => handleFilterChange('months_range', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={6}>6 meses</option>
              <option value={12}>12 meses</option>
              <option value={18}>18 meses</option>
              <option value={24}>24 meses</option>
            </select>
          </div>
        </div>
      </div>

      {/* Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <MetricCard
          title="Tempo Médio Geral"
          value={formatTenure(average_tenure_years || 0, average_tenure_months || 0)}
          icon={ClockIcon}
          color="indigo"
        />
        <MetricCard
          title="Média Mulheres"
          value={formatTenure(by_gender?.F ? Math.floor(by_gender.F / 12) : 0, by_gender?.F ? by_gender.F % 12 : 0)}
          icon={UserIcon}
          color="pink"
        />
        <MetricCard
          title="Média Homens"
          value={formatTenure(by_gender?.M ? Math.floor(by_gender.M / 12) : 0, by_gender?.M ? by_gender.M % 12 : 0)}
          icon={UserIcon}
          color="blue"
        />
        <MetricCard
          title="Total de Colaboradores"
          value={total_employees || 0}
          icon={UsersIcon}
          color="teal"
        />
      </div>

      {/* Gráfico de Evolução do Tempo Médio */}
      {evolution && evolution.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📊 Evolução do Tempo Médio de Casa
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis dataKey="month_name" axisLine={false} tickLine={false} />
              <YAxis label={{ value: 'Meses', angle: -90, position: 'insideLeft' }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{fill: 'transparent'}} />
              <Legend />
              <Area
                type="monotone"
                dataKey="average_tenure_months"
                stroke="#6366f1"
                fill="#6366f1"
                fillOpacity={0.15}
                strokeWidth={3}
                name="Tempo Médio (meses)"
                dot={{ fill: '#6366f1', r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Faixas de Tempo de Casa */}
      {tenure_ranges && tenure_ranges.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            ⏰ Distribuição por Tempo de Casa (Período Atual)
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {tenure_ranges.map((range, idx) => {
              const totalRange = tenure_ranges.reduce((sum, r) => sum + r.count, 0);
              const percentage = totalRange > 0 ? ((range.count / totalRange) * 100).toFixed(1) : 0;
              
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
                <div 
                  key={idx} 
                  className={`p-4 rounded-lg border ${color.bg} ${color.border} cursor-pointer hover:shadow-md transition-shadow`}
                  onClick={() => setSelectedTenureRange(range)}
                >
                  <p className={`text-sm font-medium ${color.text}`}>{range.range}</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{range.count}</p>
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

      {/* Setores e Cargos Lado a Lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tempo Médio por Departamento */}
        {sortedDepartmentData && sortedDepartmentData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900">
                🏢 Tempo Médio por Departamento
              </h3>
              <p className="text-sm text-gray-500">Departamentos com maior índice de retenção</p>
            </div>
            
            <ResponsiveContainer width="100%" height={450}>
              <BarChart
                data={sortedDepartmentData}
                margin={{ top: 20, right: 30, left: 0, bottom: 80 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                <XAxis 
                  dataKey="department" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={0}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip 
                  cursor={{ fill: '#f9fafb' }} 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                  formatter={(value) => [`${value} meses`, 'Tempo Médio']}
                />
                <Bar dataKey="avg_months" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {sortedDepartmentData.map((entry, index) => {
                    const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4'];
                    return <Cell key={`cell-dept-${index}`} fill={colors[index % colors.length]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Tempo Médio por Cargo */}
        {sortedRoleData && sortedRoleData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900">
                👔 Top 10 Cargos Retentores
              </h3>
              <p className="text-sm text-gray-500">Cargos com o maior tempo médio na empresa (Meses)</p>
            </div>
            
            <ResponsiveContainer width="100%" height={450}>
              <BarChart
                data={sortedRoleData}
                margin={{ top: 20, right: 30, left: 0, bottom: 80 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                <XAxis 
                  dataKey="role" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  interval={0}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip 
                  cursor={{ fill: '#f9fafb' }} 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                  formatter={(value) => [`${value} meses`, 'Tempo Médio']}
                />
                <Bar dataKey="avg_months" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {sortedRoleData.map((entry, index) => {
                    const colors = ['#10b981', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6', '#06b6d4'];
                    return <Cell key={`cell-role-${index}`} fill={colors[index % colors.length]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Modal de Detalhamento por Faixa de Tempo de Casa */}
      {selectedTenureRange && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[80vh] flex flex-col">
            <div className="p-4 border-b flex justify-between items-center bg-indigo-50 rounded-t-lg">
              <h3 className="text-lg font-bold text-indigo-900">
                Tempo: {selectedTenureRange.range} ({selectedTenureRange.count} pessoas)
              </h3>
              <button 
                onClick={() => setSelectedTenureRange(null)}
                className="text-indigo-500 hover:text-indigo-700 font-bold text-xl"
              >
                &times;
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {selectedTenureRange.employees && selectedTenureRange.employees.length > 0 ? (
                <ul className="divide-y divide-gray-100">
                  {selectedTenureRange.employees.map((emp, i) => (
                    <li key={i} className="py-3 px-2 flex flex-col hover:bg-gray-50 transition-colors rounded-md">
                      <span className="font-medium text-gray-900 text-sm">{emp.name}</span>
                      <span className="text-xs text-gray-500 mt-1">{emp.department} • {emp.tenure}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 italic text-sm text-center py-4">Nenhum colaborador nesta faixa de tempo.</p>
              )}
            </div>
            <div className="p-4 border-t bg-gray-50 flex justify-end rounded-b-lg">
              <button 
                onClick={() => setSelectedTenureRange(null)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors text-sm font-medium"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tenure;
