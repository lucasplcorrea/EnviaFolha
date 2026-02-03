import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { UserGroupIcon, UserPlusIcon, UserMinusIcon, ChartBarIcon, CalendarDaysIcon, CalendarIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function Turnover() {
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
    monthsRange: 12
  });
  
  const [turnoverData, setTurnoverData] = useState(null);
  const [loading, setLoading] = useState(true);
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
        
        // Extrair apenas os nomes das divisões (vem como objetos {name, total_employees})
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

  // Carregar dados quando filtros estão prontos
  const loadTurnoverData = useCallback(async () => {
    if (!selectedFilters.year || !selectedFilters.month) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        year: String(selectedFilters.year),
        month: String(selectedFilters.month),
        company: selectedFilters.company,
        division: selectedFilters.division,
        months_range: String(selectedFilters.monthsRange)
      });
      
      const response = await fetch(`http://localhost:8002/api/v1/indicators/turnover?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Erro ao carregar dados');
      
      const data = await response.json();
      setTurnoverData(data);
    } catch (error) {
      console.error('Erro ao carregar turnover:', error);
      toast.error('Erro ao carregar dados de turnover');
    } finally {
      setLoading(false);
    }
  }, [selectedFilters]);

  // Trigger load when filters are ready or change
  useEffect(() => {
    if (filtersReady) {
      loadTurnoverData();
    }
  }, [filtersReady, loadTurnoverData]);

  // Calcular métricas acumuladas para diferentes períodos
  const periodMetrics = useMemo(() => {
    if (!turnoverData?.evolution || turnoverData.evolution.length === 0) {
      return { month: null, sixMonths: null, year: null, eighteenMonths: null, twentyFourMonths: null };
    }
    
    const evolution = turnoverData.evolution;
    
    const calculatePeriodMetrics = (data) => {
      if (!data || data.length === 0) return null;
      
      const totalAdmissions = data.reduce((sum, m) => sum + (m.admissions || 0), 0);
      const totalTerminations = data.reduce((sum, m) => sum + (m.terminations || 0), 0);
      const avgHeadcount = data.reduce((sum, m) => sum + (m.avg_headcount || 0), 0) / data.length;
      
      // Taxa de turnover acumulada: média das taxas mensais
      const avgTurnoverRate = data.reduce((sum, m) => sum + (m.turnover_rate || 0), 0) / data.length;
      
      return {
        turnover_rate: avgTurnoverRate,
        admissions: totalAdmissions,
        terminations: totalTerminations,
        avg_headcount: avgHeadcount,
        months: data.length
      };
    };
    
    // Mês selecionado (último da lista)
    const monthData = evolution.length > 0 ? evolution[evolution.length - 1] : null;
    
    // Últimos 6 meses
    const sixMonthsData = evolution.slice(-6);
    
    // Últimos 12 meses (ou ano)
    const yearData = evolution.slice(-12);
    
    // Últimos 18 meses
    const eighteenMonthsData = evolution.slice(-18);
    
    // Últimos 24 meses
    const twentyFourMonthsData = evolution.slice(-24);
    
    return {
      month: monthData ? {
        turnover_rate: monthData.turnover_rate,
        admissions: monthData.admissions,
        terminations: monthData.terminations,
        avg_headcount: monthData.avg_headcount,
        months: 1
      } : null,
      sixMonths: calculatePeriodMetrics(sixMonthsData),
      year: calculatePeriodMetrics(yearData),
      eighteenMonths: calculatePeriodMetrics(eighteenMonthsData),
      twentyFourMonths: calculatePeriodMetrics(twentyFourMonthsData)
    };
  }, [turnoverData]);

  // Dados do gráfico ordenados cronologicamente (antigo → recente)
  const chartData = useMemo(() => {
    if (!turnoverData?.evolution) return [];
    // evolution já vem do mais antigo para o mais recente do backend
    // NÃO precisamos reverter para o gráfico
    return turnoverData.evolution;
  }, [turnoverData]);

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '0.00%';
    return `${Number(value).toFixed(2)}%`;
  };

  const handleFilterChange = (key, value) => {
    setSelectedFilters(prev => ({ ...prev, [key]: value }));
  };

  // Loading state
  if (loading && !turnoverData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-500">Carregando dados de turnover...</span>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Turnover (Rotatividade)</h1>
        <p className="mt-1 text-sm text-gray-500">
          Métricas de entrada e saída de colaboradores
        </p>
      </div>
      
      {/* Filtros */}
      <div className="bg-white shadow rounded-lg p-6">
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
              value={selectedFilters.monthsRange}
              onChange={(e) => handleFilterChange('monthsRange', parseInt(e.target.value))}
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
      
      {/* Conteúdo principal */}
      {turnoverData && turnoverData.current ? (
        <>
          {/* Cards do Mês Selecionado */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <CalendarIcon className="h-5 w-5 mr-2 text-gray-600" />
              Mês Selecionado ({turnoverData.evolution?.[turnoverData.evolution.length - 1]?.month_name || '-'})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-500">Taxa de Turnover</p>
                    <p className="text-xl font-bold text-blue-600 mt-1">
                      {formatPercent(periodMetrics.month?.turnover_rate)}
                    </p>
                  </div>
                  <ChartBarIcon className="h-8 w-8 text-blue-600" />
                </div>
              </div>
              
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-500">Admissões</p>
                    <p className="text-xl font-bold text-green-600 mt-1">
                      {periodMetrics.month?.admissions || 0}
                    </p>
                  </div>
                  <UserPlusIcon className="h-8 w-8 text-green-600" />
                </div>
              </div>
              
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-500">Desligamentos</p>
                    <p className="text-xl font-bold text-red-600 mt-1">
                      {periodMetrics.month?.terminations || 0}
                    </p>
                  </div>
                  <UserMinusIcon className="h-8 w-8 text-red-600" />
                </div>
              </div>
              
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-500">Headcount Médio</p>
                    <p className="text-xl font-bold text-gray-900 mt-1">
                      {Math.round(periodMetrics.month?.avg_headcount || 0)}
                    </p>
                  </div>
                  <UserGroupIcon className="h-8 w-8 text-gray-600" />
                </div>
              </div>
            </div>
          </div>
          
          {/* Cards de Períodos Acumulados */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <CalendarDaysIcon className="h-5 w-5 mr-2 text-gray-600" />
              Métricas Acumuladas por Período
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* 6 Meses */}
              <div className={`shadow rounded-lg p-4 border ${periodMetrics.sixMonths && periodMetrics.sixMonths.months >= 6 ? 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
                <h3 className={`text-sm font-semibold mb-2 ${periodMetrics.sixMonths && periodMetrics.sixMonths.months >= 6 ? 'text-blue-800' : 'text-gray-400'}`}>Últimos 6 Meses</h3>
                {periodMetrics.sixMonths && periodMetrics.sixMonths.months >= 6 ? (
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Taxa Média</span>
                      <span className="text-sm font-bold text-blue-700">{formatPercent(periodMetrics.sixMonths.turnover_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Admissões</span>
                      <span className="text-sm font-medium text-green-600">+{periodMetrics.sixMonths.admissions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Desligamentos</span>
                      <span className="text-sm font-medium text-red-600">-{periodMetrics.sixMonths.terminations}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-blue-200">
                      <span className="text-xs text-gray-600">HC Médio</span>
                      <span className="text-sm font-medium text-gray-700">{Math.round(periodMetrics.sixMonths.avg_headcount)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Dados insuficientes</p>
                )}
              </div>
              
              {/* 12 Meses */}
              <div className={`shadow rounded-lg p-4 border ${periodMetrics.year && periodMetrics.year.months >= 12 ? 'bg-gradient-to-br from-green-50 to-green-100 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                <h3 className={`text-sm font-semibold mb-2 ${periodMetrics.year && periodMetrics.year.months >= 12 ? 'text-green-800' : 'text-gray-400'}`}>Últimos 12 Meses</h3>
                {periodMetrics.year && periodMetrics.year.months >= 12 ? (
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Taxa Média</span>
                      <span className="text-sm font-bold text-green-700">{formatPercent(periodMetrics.year.turnover_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Admissões</span>
                      <span className="text-sm font-medium text-green-600">+{periodMetrics.year.admissions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Desligamentos</span>
                      <span className="text-sm font-medium text-red-600">-{periodMetrics.year.terminations}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-green-200">
                      <span className="text-xs text-gray-600">HC Médio</span>
                      <span className="text-sm font-medium text-gray-700">{Math.round(periodMetrics.year.avg_headcount)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Dados insuficientes</p>
                )}
              </div>
              
              {/* 18 Meses */}
              <div className={`shadow rounded-lg p-4 border ${periodMetrics.eighteenMonths && periodMetrics.eighteenMonths.months >= 18 ? 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200' : 'bg-gray-50 border-gray-200'}`}>
                <h3 className={`text-sm font-semibold mb-2 ${periodMetrics.eighteenMonths && periodMetrics.eighteenMonths.months >= 18 ? 'text-purple-800' : 'text-gray-400'}`}>Últimos 18 Meses</h3>
                {periodMetrics.eighteenMonths && periodMetrics.eighteenMonths.months >= 18 ? (
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Taxa Média</span>
                      <span className="text-sm font-bold text-purple-700">{formatPercent(periodMetrics.eighteenMonths.turnover_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Admissões</span>
                      <span className="text-sm font-medium text-green-600">+{periodMetrics.eighteenMonths.admissions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Desligamentos</span>
                      <span className="text-sm font-medium text-red-600">-{periodMetrics.eighteenMonths.terminations}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-purple-200">
                      <span className="text-xs text-gray-600">HC Médio</span>
                      <span className="text-sm font-medium text-gray-700">{Math.round(periodMetrics.eighteenMonths.avg_headcount)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Dados insuficientes</p>
                )}
              </div>
              
              {/* 24 Meses */}
              <div className={`shadow rounded-lg p-4 border ${periodMetrics.twentyFourMonths && periodMetrics.twentyFourMonths.months >= 24 ? 'bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200' : 'bg-gray-50 border-gray-200'}`}>
                <h3 className={`text-sm font-semibold mb-2 ${periodMetrics.twentyFourMonths && periodMetrics.twentyFourMonths.months >= 24 ? 'text-orange-800' : 'text-gray-400'}`}>Últimos 24 Meses</h3>
                {periodMetrics.twentyFourMonths && periodMetrics.twentyFourMonths.months >= 24 ? (
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Taxa Média</span>
                      <span className="text-sm font-bold text-orange-700">{formatPercent(periodMetrics.twentyFourMonths.turnover_rate)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Admissões</span>
                      <span className="text-sm font-medium text-green-600">+{periodMetrics.twentyFourMonths.admissions}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Desligamentos</span>
                      <span className="text-sm font-medium text-red-600">-{periodMetrics.twentyFourMonths.terminations}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-orange-200">
                      <span className="text-xs text-gray-600">HC Médio</span>
                      <span className="text-sm font-medium text-gray-700">{Math.round(periodMetrics.twentyFourMonths.avg_headcount)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Dados insuficientes</p>
                )}
              </div>
            </div>
          </div>
          
          {/* Gráfico de Evolução - ordem cronológica (esquerda=antigo, direita=recente) */}
          {chartData && chartData.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Evolução Temporal</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month_name" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="turnover_rate" stroke="#3b82f6" name="Taxa Turnover (%)" />
                  <Line yAxisId="right" type="monotone" dataKey="admissions" stroke="#10b981" name="Admissões" />
                  <Line yAxisId="right" type="monotone" dataKey="terminations" stroke="#ef4444" name="Desligamentos" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          
          {/* Tabela de Evolução - ordem cronológica reversa (recente primeiro) */}
          {turnoverData.evolution && turnoverData.evolution.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Detalhamento Mensal</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mês</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Taxa Turnover</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Admissões</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Desligamentos</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Headcount Médio</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {[...turnoverData.evolution].reverse().map((item, idx) => (
                      <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-4 py-3 text-sm text-gray-900">{item.month_name}</td>
                        <td className="px-4 py-3 text-sm text-right text-blue-600 font-medium">
                          {formatPercent(item.turnover_rate)}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-green-600">
                          {item.admissions}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-red-600">
                          {item.terminations}
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-700">
                          {Math.round(item.avg_headcount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
          Selecione os filtros para visualizar os dados de turnover
        </div>
      )}
    </div>
  );
}

export default Turnover;
