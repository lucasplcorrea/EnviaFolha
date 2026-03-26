import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { ComposedChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
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
    leave_type: [], // Array para multiplos filtros
    months_range: 6
  });
  
  const [filtersReady, setFiltersReady] = useState(false);
  const [selectedLeaveRange, setSelectedLeaveRange] = useState(null);
  const [isLeaveTypeDropdownOpen, setIsLeaveTypeDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const initialLoadDone = useRef(false);

  // Fechar dropdown de checkboxes ao clicar fora
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsLeaveTypeDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
      
      if (selectedFilters.leave_type && selectedFilters.leave_type.length > 0) {
        selectedFilters.leave_type.forEach(t => params.append('leave_type', t));
      } else {
        params.append('leave_type', 'all');
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
  const current = useMemo(() => data?.current || {}, [data]);
  const evolution = useMemo(() => data?.evolution || [], [data]);

  // Agregar tipos de afastamento de todo o período de evolução
  const aggregatedByType = useMemo(() => {
    if (!evolution || evolution.length === 0) return [];
    
    const typeMap = {};
    evolution.forEach(period => {
      const periodName = formatMonth(period.year, period.month);
      (period.by_type || []).forEach(item => {
        if (!typeMap[item.type]) {
          typeMap[item.type] = { count: 0, employees: [] };
        }
        typeMap[item.type].count += item.count;
        if (item.employees) {
          typeMap[item.type].employees.push(...item.employees.map(e => ({...e, period: periodName})));
        }
      });
    });
    
    const total = Object.values(typeMap).reduce((sum, data) => sum + data.count, 0);
    return Object.entries(typeMap).map(([type, data]) => ({
      type,
      count: data.count,
      percentage: total > 0 ? parseFloat((data.count / total * 100).toFixed(1)) : 0,
      employees: data.employees.sort((a,b) => a.name.localeCompare(b.name))
    })).sort((a, b) => b.count - a.count);
  }, [evolution]);

  const sortedDepartmentData = useMemo(() => {
    if (!current?.by_department) return [];
    return [...current.by_department].sort((a, b) => b.count - a.count);
  }, [current]);

  const sortedRoleData = useMemo(() => {
    if (!current?.by_role) return [];
    return current.by_role; // já vem ordenado e top 10 do back
  }, [current]);

  const sortedCompanyData = useMemo(() => {
    if (!current?.by_company) return [];
    return [...current.by_company].sort((a, b) => b.count - a.count);
  }, [current]);

  // Preparar dados para gráfico de evolução
  const chartData = useMemo(() => {
    if (!evolution || evolution.length === 0) return [];
    return evolution.map(item => ({
      period: formatMonth(item.year, item.month),
      afastados: item.total_on_leave,
      taxa: item.absenteeism_rate
    }));
  }, [evolution]);

  // Preparar dados para gráfico de evolução por tipo
  const chartDataByType = useMemo(() => {
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

          <div ref={dropdownRef} className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Afastamento</label>
            <div 
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white cursor-pointer flex justify-between items-center"
              onClick={() => setIsLeaveTypeDropdownOpen(!isLeaveTypeDropdownOpen)}
            >
              <span className="truncate text-sm">
                {selectedFilters.leave_type.length === 0 
                  ? 'Todos' 
                  : selectedFilters.leave_type.length === 1 
                    ? selectedFilters.leave_type[0] 
                    : `${selectedFilters.leave_type.length} selecionados`}
              </span>
              <span className="text-gray-400 text-xs">▼</span>
            </div>
            
            {isLeaveTypeDropdownOpen && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                <div 
                  className="px-3 py-2 hover:bg-gray-50 flex items-center cursor-pointer border-b text-sm"
                  onClick={() => handleFilterChange('leave_type', [])}
                >
                  <input 
                    type="checkbox" 
                    checked={selectedFilters.leave_type.length === 0}
                    onChange={() => {}} 
                    className="mr-2 h-4 w-4 text-purple-600 focus:ring-purple-500 rounded border-gray-300"
                  />
                  <span className={selectedFilters.leave_type.length === 0 ? "font-medium" : ""}>Selecionar Todos</span>
                </div>
                {filters.leaveTypes.map(t => (
                  <div 
                    key={t} 
                    className="px-3 py-2 hover:bg-gray-50 flex items-center cursor-pointer text-sm"
                    onClick={() => {
                      const isSelected = selectedFilters.leave_type.includes(t);
                      if (isSelected) {
                        handleFilterChange('leave_type', selectedFilters.leave_type.filter(item => item !== t));
                      } else {
                        handleFilterChange('leave_type', [...selectedFilters.leave_type, t]);
                      }
                    }}
                  >
                    <input 
                      type="checkbox" 
                      checked={selectedFilters.leave_type.includes(t)}
                      onChange={() => {}}
                      className="mr-2 h-4 w-4 text-purple-600 focus:ring-purple-500 rounded border-gray-300"
                    />
                    <span className="truncate">{t}</span>
                  </div>
                ))}
              </div>
            )}
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

      {/* Gráfico de Evolução Consolidado */}
      {chartData && chartData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Evolução Mensal (Afastados vs. Taxa)</h3>
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis dataKey="period" axisLine={false} tickLine={false} tick={{fill: '#6b7280', fontSize: 11}} />
              <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{fill: '#6b7280', fontSize: 11}} />
              <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{fill: '#6b7280', fontSize: 11}} tickFormatter={(val) => `${val}%`} />
              <Tooltip cursor={{fill: 'transparent'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }} />
              <Legend verticalAlign="top" height={36} />
              <Area yAxisId="left" type="monotone" dataKey="afastados" fill="#8B5CF6" stroke="#8B5CF6" fillOpacity={0.15} strokeWidth={2} name="Total Afastados" />
              <Line yAxisId="right" type="monotone" dataKey="taxa" stroke="#EC4899" strokeWidth={3} name="Taxa de Absenteísmo (%)" dot={{r: 4, fill: '#EC4899'}} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

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

      {/* Grid para Tipo e Empresa */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Afastamentos por Tipo (2 colunas no XL) */}
        {aggregatedByType && aggregatedByType.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 xl:col-span-2">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Carga de Afastamentos por Tipo (Período Selecionado)</h3>
            <p className="text-sm text-gray-500 mb-6">Clique nas categorias para detalhar a lista de colaboradores afastados.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={aggregatedByType}
                      dataKey="count"
                      nameKey="type"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label={(entry) => `${entry.percentage}%`}
                      labelLine={true}
                    >
                      {aggregatedByType.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={COLORS[index % COLORS.length]} 
                          className="cursor-pointer hover:opacity-80 transition-opacity"
                          onClick={() => setSelectedLeaveRange({range: entry.type, count: entry.count, employees: entry.employees})}
                        />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name, props) => [`${value} afastamento(s) (${props.payload.percentage}%)`, props.payload.type]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-3 overflow-y-auto max-h-[300px] pr-2">
                {aggregatedByType.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-md cursor-pointer transition-colors"
                    onClick={() => setSelectedLeaveRange({range: item.type, count: item.count, employees: item.employees})}
                  >
                    <div className="flex items-center">
                      <div
                        className="w-4 h-4 rounded mr-2"
                        style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                      ></div>
                      <span className="text-sm font-medium text-gray-700">{item.type}</span>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{item.count}</span>
                      <span className="text-xs text-gray-500 w-12 text-right">({item.percentage}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Afastamentos por Empresa (1 coluna no XL) */}
        {sortedCompanyData && sortedCompanyData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 xl:col-span-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🏢 Afastamentos por Empresa</h3>
            <p className="text-sm text-gray-500 mb-6">Distribuição entre matriz e filiais</p>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={sortedCompanyData}
                  dataKey="count"
                  nameKey="company"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={60}
                  label={(entry) => `${entry.percentage}%`}
                  labelLine={true}
                >
                  {sortedCompanyData.map((entry, index) => {
                    const companyColors = ['#F59E0B', '#3B82F6', '#10B981', '#8B5CF6'];
                    return (
                      <Cell 
                        key={`cell-comp-${index}`} 
                        fill={companyColors[index % companyColors.length]} 
                        className="cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={() => setSelectedLeaveRange({range: entry.company, count: entry.count, employees: entry.employees})}
                      />
                    );
                  })}
                </Pie>
                <Tooltip formatter={(value, name, props) => [`${value} afastamento(s)`, props.payload.company]} />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Setores e Cargos Lado a Lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Afastamentos por Departamento */}
        {sortedDepartmentData && sortedDepartmentData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900">
                🏢 Afastamentos por Departamento
              </h3>
              <p className="text-sm text-gray-500">Setores com maior carga de incidência</p>
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
                  formatter={(value) => [`${value} incidência(s)`, 'Volume']}
                />
                <Bar 
                  dataKey="count" 
                  radius={[4, 4, 0, 0]} 
                  maxBarSize={40}
                  onClick={(data) => setSelectedLeaveRange({range: data.department, count: data.count, employees: data.employees})}
                  className="cursor-pointer"
                >
                  {sortedDepartmentData.map((entry, index) => {
                    const colors = ['#8B5CF6', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#06B6D4'];
                    return <Cell key={`cell-dept-${index}`} fill={colors[index % colors.length]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Afastamentos por Cargo */}
        {sortedRoleData && sortedRoleData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900">
                👔 Top 10 Cargos com Afastamento
              </h3>
              <p className="text-sm text-gray-500">Cargos hierárquicos com as maiores cargas</p>
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
                  formatter={(value) => [`${value} incidência(s)`, 'Volume']}
                />
                <Bar 
                  dataKey="count" 
                  radius={[4, 4, 0, 0]} 
                  maxBarSize={40}
                  onClick={(data) => setSelectedLeaveRange({range: data.role, count: data.count, employees: data.employees})}
                  className="cursor-pointer"
                >
                  {sortedRoleData.map((entry, index) => {
                    const colors = ['#F59E0B', '#3B82F6', '#8B5CF6', '#10B981', '#EC4899', '#06B6D4'];
                    return <Cell key={`cell-role-${index}`} fill={colors[index % colors.length]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Modal de Detalhamento Nominal */}
      {selectedLeaveRange && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
            <div className="p-4 border-b flex justify-between items-center bg-purple-50 rounded-t-lg">
              <h3 className="text-lg font-bold text-purple-900">
                Foco: {selectedLeaveRange.range} ({selectedLeaveRange.count} incidências)
              </h3>
              <button 
                onClick={() => setSelectedLeaveRange(null)}
                className="text-purple-500 hover:text-purple-700 font-bold text-xl"
              >
                &times;
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {selectedLeaveRange.employees && selectedLeaveRange.employees.length > 0 ? (
                <ul className="divide-y divide-gray-100 border rounded-md">
                  {selectedLeaveRange.employees.map((emp, i) => (
                    <li key={i} className="py-3 px-3 flex flex-col hover:bg-gray-50 transition-colors">
                      <span className="font-medium text-gray-900 text-sm">{emp.name}</span>
                      <span className="text-xs text-gray-500 mt-1">
                        {emp.department} • {emp.type} • {emp.days ? `${emp.days} dias` : 'Período aberto'}
                        {emp.period && ` • ${emp.period}`}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 italic text-sm text-center py-4">Nenhum colaborador rastreável.</p>
              )}
            </div>
            <div className="p-4 border-t bg-gray-50 flex justify-end rounded-b-lg">
              <button 
                onClick={() => setSelectedLeaveRange(null)}
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

export default Leaves;
