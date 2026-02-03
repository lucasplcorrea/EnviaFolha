import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ClockIcon,
  ExclamationTriangleIcon,
  UsersIcon
} from '@heroicons/react/24/outline';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { MetricCard, LoadingSpinner, EmptyState } from './components';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const Tenure = () => {
  const { config } = useTheme();
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
  const { tenure_ranges, average_tenure_years, average_tenure_months, total_employees, by_department } = current;

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Filtros</h2>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Tempo Médio de Casa"
          value={formatTenure(average_tenure_years || 0, average_tenure_months || 0)}
          icon={ClockIcon}
          color="indigo"
        />
        <MetricCard
          title="Total de Colaboradores"
          value={total_employees || 0}
          icon={UsersIcon}
          color="blue"
        />
        <MetricCard
          title="Faixas de Tempo"
          value={tenure_ranges?.length || 0}
          icon={ClockIcon}
          color="purple"
        />
      </div>

      {/* Gráfico de Evolução do Tempo Médio */}
      {evolution && evolution.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📊 Evolução do Tempo Médio de Casa
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month_name" />
              <YAxis label={{ value: 'Anos', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="average_tenure_years"
                stroke="#6366f1"
                strokeWidth={2}
                name="Tempo Médio (anos)"
                dot={{ fill: '#6366f1', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Faixas de Tempo de Casa */}
      {tenure_ranges && tenure_ranges.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            ⏰ Distribuição por Tempo de Casa (Período Atual)
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
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
                <div key={idx} className={`p-4 rounded-lg border ${color.bg} ${color.border}`}>
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

      {/* Tempo Médio por Departamento */}
      {by_department && by_department.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            🏢 Tempo Médio por Departamento
          </h3>
          <div className="space-y-3">
            {by_department.map((dept, idx) => {
              const maxYears = Math.max(...by_department.map(d => d.avg_years));
              const percentage = maxYears > 0 ? (dept.avg_years / maxYears) * 100 : 0;
              
              return (
                <div key={idx}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{dept.department}</span>
                    <span className="text-gray-600">{dept.avg_years} {dept.avg_years === 1 ? 'ano' : 'anos'}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div 
                      className="bg-indigo-500 h-4 rounded-full transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default Tenure;
