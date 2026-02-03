import React, { useState, useEffect, useRef, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';
import ExportPDFButton from '../../components/ExportPDFButton';

const Leaves = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({
    years: [],
    months: [],
    divisions: [],
    leaveTypes: []
  });
  const [selectedFilters, setSelectedFilters] = useState({
    year: '',
    month: '',
    company: 'all',
    division: 'all',
    leave_type: 'all',
    months_range: 6
  });
  
  const [filtersReady, setFiltersReady] = useState(false);
  const initialLoadDone = useRef(false);

  // Cores para gráficos - expandido para suportar mais tipos de afastamento
  const COLORS = ['#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#EF4444', '#6366F1', '#14B8A6', '#F97316', '#84CC16', '#A855F7', '#06B6D4'];

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
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        year: selectedFilters.year,
        month: selectedFilters.month,
        months_range: selectedFilters.months_range
      });
      
      if (selectedFilters.company !== 'all') {
        params.append('company', selectedFilters.company);
      }
      if (selectedFilters.division !== 'all') {
        params.append('division', selectedFilters.division);
      }
      if (selectedFilters.leave_type !== 'all') {
        params.append('leave_type', selectedFilters.leave_type);
      }
      
      const response = await fetch(`http://localhost:8002/api/v1/indicators/leaves?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Erro ao carregar dados');
      
      const result = await response.json();
      setData(result);
      
      // Atualizar tipos de afastamento disponíveis
      if (result.leave_types && result.leave_types.length > 0) {
        setFilters(prev => ({ ...prev, leaveTypes: result.leave_types }));
      }
    } catch (error) {
      console.error('Erro ao carregar dados de afastamentos:', error);
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  }, [selectedFilters]);

  // Carregar dados quando filtros estiverem prontos ou mudarem
  useEffect(() => {
    if (filtersReady) {
      loadData();
    }
  }, [filtersReady, loadData]);

  const formatMonth = (year, month) => {
    const monthNames = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    return `${monthNames[month - 1]}/${year}`;
  };

  const handleFilterChange = (field, value) => {
    setSelectedFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Processar dados antes do early return (hooks não podem ser condicionais)
  const current = data?.current || {};
  const evolution = data?.evolution || [];
  const { by_type = [], by_department = [] } = current;

  // Agregar tipos de afastamento de todo o período de evolução
  const aggregatedByType = React.useMemo(() => {
    if (!evolution || evolution.length === 0) return [];
    
    const typeMap = {};
    evolution.forEach(period => {
      (period.by_type || []).forEach(item => {
        if (typeMap[item.type]) {
          typeMap[item.type] += item.count;
        } else {
          typeMap[item.type] = item.count;
        }
      });
    });
    
    const total = Object.values(typeMap).reduce((sum, count) => sum + count, 0);
    return Object.entries(typeMap).map(([type, count]) => ({
      type,
      count,
      percentage: total > 0 ? parseFloat((count / total * 100).toFixed(1)) : 0
    })).sort((a, b) => b.count - a.count);
  }, [evolution]);

  // Preparar dados para gráfico de evolução
  const chartData = React.useMemo(() => {
    if (!evolution || evolution.length === 0) return [];
    return evolution.map(item => ({
      period: formatMonth(item.year, item.month),
      afastados: item.total_on_leave,
      taxa: item.absenteeism_rate
    }));
  }, [evolution]);

  // Preparar dados para gráfico de evolução por tipo
  const chartDataByType = React.useMemo(() => {
    if (!evolution || evolution.length === 0) return [];
    
    // Coletar todos os tipos únicos
    const allTypes = new Set();
    evolution.forEach(period => {
      (period.by_type || []).forEach(item => allTypes.add(item.type));
    });
    
    // Criar dados para cada período
    return evolution.map(period => {
      const periodData = {
        period: formatMonth(period.year, period.month)
      };
      
      // Adicionar contagem de cada tipo
      allTypes.forEach(type => {
        const typeItem = (period.by_type || []).find(t => t.type === type);
        periodData[type] = typeItem ? typeItem.count : 0;
      });
      
      return periodData;
    });
  }, [evolution]);

  // Empresas fixas
  const companies = [
    { code: '0059', name: 'Infraestrutura' },
    { code: '0060', name: 'Empreendimentos' }
  ];

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Carregando dados de afastamentos...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">🏥 Afastamentos</h2>
          <ExportPDFButton className="no-print" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
            <select
              value={selectedFilters.year}
              onChange={(e) => handleFilterChange('year', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {filters.years.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
            <select
              value={selectedFilters.month}
              onChange={(e) => handleFilterChange('month', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {filters.months.map(m => (
                <option key={m.number} value={m.number}>{m.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
            <select
              value={selectedFilters.company}
              onChange={(e) => handleFilterChange('company', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">Todas</option>
              {companies.map(c => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Setor</label>
            <select
              value={selectedFilters.division}
              onChange={(e) => handleFilterChange('division', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">Todos</option>
              {filters.divisions.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Afastamento</label>
            <select
              value={selectedFilters.leave_type}
              onChange={(e) => handleFilterChange('leave_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">Todos</option>
              {filters.leaveTypes.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Período Evolução</label>
            <select
              value={selectedFilters.months_range}
              onChange={(e) => handleFilterChange('months_range', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value={3}>3 meses</option>
              <option value={6}>6 meses</option>
              <option value={12}>12 meses</option>
            </select>
          </div>
        </div>
      </div>

      {/* Cards de Métricas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Afastados</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{current.total_on_leave || 0}</p>
            </div>
            <div className="text-4xl">🏥</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Taxa de Absenteísmo</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{current.absenteeism_rate || 0}%</p>
            </div>
            <div className="text-4xl">📊</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Duração Média</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{current.average_duration_days || 0}</p>
              <p className="text-sm text-gray-500">dias</p>
            </div>
            <div className="text-4xl">⏱️</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Colaboradores</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{current.total_employees || 0}</p>
            </div>
            <div className="text-4xl">👥</div>
          </div>
        </div>
      </div>

      {/* Gráficos de Evolução */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Evolução de Afastamentos</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="afastados" stroke="#8B5CF6" strokeWidth={2} name="Total Afastados" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Evolução da Taxa de Absenteísmo</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="taxa" stroke="#EC4899" strokeWidth={2} name="Taxa (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Evolução por Tipo de Afastamento */}
      {chartDataByType && chartDataByType.length > 0 && aggregatedByType.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📅 Evolução por Tipo de Afastamento</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartDataByType}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip />
              <Legend />
              {aggregatedByType.map((typeData, index) => (
                <Line
                  key={typeData.type}
                  type="monotone"
                  dataKey={typeData.type}
                  stroke={COLORS[index % COLORS.length]}
                  strokeWidth={2}
                  name={typeData.type}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Afastamentos por Tipo */}
      {aggregatedByType && aggregatedByType.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Afastamentos por Tipo (Período Completo)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={aggregatedByType}
                    dataKey="count"
                    nameKey="type"
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    label={(entry) => `${entry.percentage}%`}
                    labelLine={true}
                  >
                    {aggregatedByType.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value, name, props) => [`${value} (${props.payload.percentage}%)`, props.payload.type]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {aggregatedByType.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className="w-4 h-4 rounded mr-2"
                      style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                    ></div>
                    <span className="text-sm font-medium text-gray-700">{item.type}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-gray-900">{item.count}</span>
                    <span className="text-xs text-gray-500 ml-1">({item.percentage}%)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Afastamentos por Departamento */}
      {by_department && by_department.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🏢 Afastamentos por Departamento</h3>
          <div className="space-y-3">
            {by_department.map((dept, idx) => {
              const maxCount = Math.max(...by_department.map(d => d.count));
              const percentage = maxCount > 0 ? (dept.count / maxCount) * 100 : 0;
              
              return (
                <div key={idx}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{dept.department}</span>
                    <span className="text-gray-600">{dept.count} ({dept.percentage}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div 
                      className="bg-purple-500 h-4 rounded-full transition-all duration-500"
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

export default Leaves;
