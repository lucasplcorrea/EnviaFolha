import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import {
  UsersIcon,
  ExclamationTriangleIcon,
  CalendarIcon
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

const Demographics = () => {
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
      
      const response = await api.get(`/indicators/demographics?${params}`);
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar demografia:', error);
      toast.error('Erro ao carregar indicadores demográficos');
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

  if (loading) {
    return <LoadingSpinner message="Carregando indicadores demográficos..." />;
  }

  if (!data) {
    return <EmptyState icon={ExclamationTriangleIcon} message="Nenhum dado demográfico disponível" />;
  }

  const { current, evolution } = data;
  const { by_sex, age_ranges, average_age, total_employees, male_count, female_count } = current;

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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <MetricCard
          title="Idade Média"
          value={average_age || 0}
          unit="anos"
          icon={CalendarIcon}
          color="yellow"
        />
        <MetricCard
          title="Total de Colaboradores"
          value={total_employees || 0}
          icon={UsersIcon}
          color="blue"
        />
        <MetricCard
          title="Masculino"
          value={male_count || 0}
          icon={UsersIcon}
          color="indigo"
        />
        <MetricCard
          title="Feminino"
          value={female_count || 0}
          icon={UsersIcon}
          color="pink"
        />
      </div>

      {/* Gráfico de Evolução da Idade Média */}
      {evolution && evolution.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📊 Evolução da Idade Média
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month_name" />
              <YAxis label={{ value: 'Idade (anos)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="average_age"
                stroke="#f59e0b"
                strokeWidth={2}
                name="Idade Média"
                dot={{ fill: '#f59e0b', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Gráfico de Evolução por Sexo */}
      {evolution && evolution.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            👥 Evolução da Distribuição por Sexo
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month_name" />
              <YAxis label={{ value: 'Quantidade', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="male_count"
                stroke="#3b82f6"
                strokeWidth={2}
                name="Masculino"
                dot={{ fill: '#3b82f6', r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="female_count"
                stroke="#ec4899"
                strokeWidth={2}
                name="Feminino"
                dot={{ fill: '#ec4899', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Distribuição por Sexo (cards) */}
      {by_sex && by_sex.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            👥 Distribuição por Sexo (Período Atual)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {by_sex.map((item, idx) => {
              const percentage = total_employees > 0 ? ((item.count / total_employees) * 100).toFixed(1) : 0;
              const isMale = item.sex === 'M';
              return (
                <div 
                  key={idx} 
                  className={`p-6 rounded-lg border ${
                    isMale 
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' 
                      : 'bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className={`text-lg font-medium ${isMale ? 'text-blue-700 dark:text-blue-400' : 'text-pink-700 dark:text-pink-400'}`}>
                      {isMale ? '👨 Masculino' : '👩 Feminino'}
                    </span>
                    <span className={`text-3xl font-bold ${isMale ? 'text-blue-700 dark:text-blue-300' : 'text-pink-700 dark:text-pink-300'}`}>
                      {item.count}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div 
                      className={`h-3 rounded-full ${isMale ? 'bg-blue-500' : 'bg-pink-500'}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <p className={`text-sm mt-2 ${config.classes.textSecondary}`}>
                    {percentage}% do total
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Faixas Etárias */}
      {age_ranges && age_ranges.length > 0 && (
        <div className={`${config.classes.card} p-6 rounded-lg shadow ${config.classes.border}`}>
          <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
            📊 Distribuição por Faixa Etária (Período Atual)
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {age_ranges.map((range, idx) => {
              const totalRange = age_ranges.reduce((sum, r) => sum + r.count, 0);
              const percentage = totalRange > 0 ? ((range.count / totalRange) * 100).toFixed(1) : 0;
              
              // Cores progressivas por faixa
              const colors = [
                'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
                'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
                'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
                'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
                'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
              ];
              
              return (
                <div key={idx} className={`p-4 rounded-lg border ${colors[idx % colors.length]}`}>
                  <p className={`text-sm font-medium ${config.classes.textSecondary}`}>{range.range}</p>
                  <p className={`text-3xl font-bold ${config.classes.text} mt-2`}>{range.count}</p>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full"
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
    </div>
  );
};

export default Demographics;
