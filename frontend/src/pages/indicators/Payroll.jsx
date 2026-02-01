import React, { useState, useEffect, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import api from '../../services/api';
import toast from 'react-hot-toast';
import MultiSelect from '../../components/MultiSelect';

/**
 * VERSÃO V2 - REFATORADA
 * Organizada nas 7 seções especificadas pelo RH
 * Sem filtros complexos de 13º (agora é período separado)
 */
const PayrollV2 = () => {
  const { config, theme } = useTheme();
  const isDarkMode = theme === 'dark';
  
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [showFilters, setShowFilters] = useState(true); // Controle de expansão dos filtros
  
  // Dados brutos dos filtros
  const [allPeriods, setAllPeriods] = useState([]);
  const [allYears, setAllYears] = useState([]);
  const [allMonths, setAllMonths] = useState([]);
  const [allDepartments, setAllDepartments] = useState([]);
  const [allEmployees, setAllEmployees] = useState([]);
  
  // Seleções
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [selectedYears, setSelectedYears] = useState([]);
  const [selectedMonths, setSelectedMonths] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);

  // Carregar filtros disponíveis
  useEffect(() => {
    loadFilters();
  }, []);

  // Carregar estatísticas quando mudar qualquer filtro
  useEffect(() => {
    if (selectedPeriods.length > 0 || selectedYears.length > 0 || selectedMonths.length > 0) {
      loadStatistics();
    }
  }, [selectedPeriods, selectedYears, selectedMonths, selectedDepartments, selectedEmployees]);

  // ============================================
  // FILTROS CASCATA (DRILL-THROUGH)
  // ============================================
  
  // Períodos filtrados baseado em ano/mês selecionado
  const filteredPeriods = useMemo(() => {
    let filtered = allPeriods;
    
    if (selectedYears.length > 0) {
      filtered = filtered.filter(p => selectedYears.includes(p.year));
    }
    
    if (selectedMonths.length > 0) {
      filtered = filtered.filter(p => selectedMonths.includes(p.month));
    }
    
    return filtered;
  }, [allPeriods, selectedYears, selectedMonths]);

  // Anos disponíveis baseado nos períodos selecionados
  const filteredYears = useMemo(() => {
    if (selectedPeriods.length > 0) {
      const yearsFromPeriods = allPeriods
        .filter(p => selectedPeriods.includes(p.id))
        .map(p => p.year);
      return allYears.filter(y => yearsFromPeriods.includes(y));
    }
    return allYears;
  }, [allPeriods, allYears, selectedPeriods]);

  // Meses disponíveis baseado nos períodos/anos selecionados
  const filteredMonths = useMemo(() => {
    let relevantPeriods = allPeriods;
    
    if (selectedPeriods.length > 0) {
      relevantPeriods = relevantPeriods.filter(p => selectedPeriods.includes(p.id));
    } else if (selectedYears.length > 0) {
      relevantPeriods = relevantPeriods.filter(p => selectedYears.includes(p.year));
    }
    
    const monthsFromPeriods = relevantPeriods.map(p => p.month);
    return allMonths.filter(m => monthsFromPeriods.includes(m.number));
  }, [allPeriods, allMonths, selectedPeriods, selectedYears]);

  // Departamentos disponíveis (sem filtro por enquanto, mas pode ser implementado)
  const filteredDepartments = useMemo(() => {
    return allDepartments;
  }, [allDepartments]);

  // Colaboradores disponíveis (sem filtro por enquanto, mas pode ser implementado)
  const filteredEmployees = useMemo(() => {
    return allEmployees;
  }, [allEmployees]);

  const loadFilters = async () => {
    try {
      // Carregar períodos
      const periodsRes = await api.get('/payroll/periods');
      setAllPeriods(periodsRes.data.periods || []);
      
      // Selecionar último período por padrão
      if (periodsRes.data.periods && periodsRes.data.periods.length > 0) {
        setSelectedPeriods([periodsRes.data.periods[0].id]);
      }

      // Carregar anos disponíveis
      const yearsRes = await api.get('/payroll/years');
      setAllYears(yearsRes.data.years || []);

      // Carregar meses disponíveis
      const monthsRes = await api.get('/payroll/months');
      setAllMonths(monthsRes.data.months || []);

      // Carregar departamentos
      const deptsRes = await api.get('/payroll/divisions');
      setAllDepartments(deptsRes.data.departments || []);

      // Carregar colaboradores
      const empsRes = await api.get('/payroll/employees');
      setAllEmployees(empsRes.data.employees || []);
      
    } catch (error) {
      console.error('Erro ao carregar filtros:', error);
      toast.error('Erro ao carregar filtros');
    }
  };

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedPeriods.length > 0) params.append('periods', selectedPeriods.join(','));
      if (selectedYears.length > 0) params.append('years', selectedYears.join(','));
      if (selectedMonths.length > 0) params.append('months', selectedMonths.join(','));
      if (selectedDepartments.length > 0) params.append('departments', selectedDepartments.join(','));
      if (selectedEmployees.length > 0) params.append('employees', selectedEmployees.join(','));
      
      const response = await api.get(`/payroll/statistics?${params}`);
      setData(response.data);
    } catch (error) {
      console.error('Erro ao carregar estatísticas:', error);
      toast.error('Erro ao carregar estatísticas');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value || 0);
  };

  // Contar total de filtros ativos
  const totalActiveFilters = selectedPeriods.length + selectedYears.length + 
                             selectedMonths.length + selectedDepartments.length + 
                             selectedEmployees.length;

  // Limpar todos os filtros
  const clearAllFilters = () => {
    setSelectedPeriods([]);
    setSelectedYears([]);
    setSelectedMonths([]);
    setSelectedDepartments([]);
    setSelectedEmployees([]);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-gray-500 py-12">
        Nenhum dado disponível
      </div>
    );
  }

  const { resumo_filtro, informacoes_salariais, adicionais_beneficios, encargos_trabalhistas, horas_extras, atestados_faltas, emprestimos } = data;

  return (
    <div className="space-y-6">
      {/* Header com Filtros */}
      <div className={`${config.classes.card} rounded-lg shadow`}>
        {/* Cabeçalho dos Filtros */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className={`text-2xl font-bold ${config.classes.text}`}>
              📊 Indicadores de Folha de Pagamento
            </h2>
            
            <div className="flex items-center gap-3">
              {totalActiveFilters > 0 && (
                <>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {totalActiveFilters} {totalActiveFilters === 1 ? 'filtro ativo' : 'filtros ativos'}
                  </span>
                  <button
                    onClick={clearAllFilters}
                    className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
                  >
                    Limpar tudo
                  </button>
                </>
              )}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  showFilters 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200' 
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                {showFilters ? '🔽 Ocultar Filtros' : '🔼 Mostrar Filtros'}
              </button>
            </div>
          </div>
        </div>

        {/* Grid de Filtros - Colapsável */}
        {showFilters && (
          <div className="p-6 bg-gray-50 dark:bg-gray-800/50">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Filtro de Períodos */}
              <MultiSelect
                label="Períodos"
                options={filteredPeriods.map(p => ({ value: p.id, label: p.period_name }))}
                selected={selectedPeriods}
                onChange={setSelectedPeriods}
                placeholder="Todos os períodos"
              />

              {/* Filtro de Anos */}
              <MultiSelect
                label="Anos"
                options={filteredYears.map(y => ({ value: y, label: y.toString() }))}
                selected={selectedYears}
                onChange={setSelectedYears}
                placeholder="Todos os anos"
              />

              {/* Filtro de Meses */}
              <MultiSelect
                label="Meses"
                options={filteredMonths.map(m => ({ value: m.number, label: m.name }))}
                selected={selectedMonths}
                onChange={setSelectedMonths}
                placeholder="Todos os meses"
              />

              {/* Filtro de Setores */}
              <MultiSelect
                label="Setores"
                options={filteredDepartments.map(d => ({ value: d.name, label: d.name }))}
                selected={selectedDepartments}
                onChange={setSelectedDepartments}
                placeholder="Todos os setores"
                searchable={true}
              />

              {/* Filtro de Colaboradores */}
              <MultiSelect
                label="Colaboradores"
                options={filteredEmployees.map(e => ({ value: e.id, label: e.name }))}
                selected={selectedEmployees}
                onChange={setSelectedEmployees}
                placeholder="Todos os colaboradores"
                searchable={true}
              />
            </div>
          </div>
        )}

        {/* Resumo Compacto dos Filtros Ativos - Sempre Visível */}
        {totalActiveFilters > 0 && (
          <div className="px-6 py-3 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-100 dark:border-blue-800">
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Filtros aplicados:
              </span>
              
              {/* Períodos */}
              {selectedPeriods.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filteredPeriods.filter(p => selectedPeriods.includes(p.id)).slice(0, 2).map(p => (
                    <span key={p.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                      {p.period_name}
                    </span>
                  ))}
                  {selectedPeriods.length > 2 && (
                    <span className="px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300">
                      +{selectedPeriods.length - 2} períodos
                    </span>
                  )}
                </div>
              )}

              {/* Anos */}
              {selectedYears.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedYears.map(y => (
                    <span key={y} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200">
                      {y}
                    </span>
                  ))}
                </div>
              )}

              {/* Meses */}
              {selectedMonths.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {filteredMonths.filter(m => selectedMonths.includes(m.number)).slice(0, 3).map(m => (
                    <span key={m.number} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                      {m.name}
                    </span>
                  ))}
                  {selectedMonths.length > 3 && (
                    <span className="px-2 py-0.5 text-xs text-green-700 dark:text-green-300">
                      +{selectedMonths.length - 3} meses
                    </span>
                  )}
                </div>
              )}

              {/* Setores */}
              {selectedDepartments.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                    {selectedDepartments.length} {selectedDepartments.length === 1 ? 'setor' : 'setores'}
                  </span>
                </div>
              )}

              {/* Colaboradores */}
              {selectedEmployees.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-teal-100 dark:bg-teal-900 text-teal-800 dark:text-teal-200">
                    {selectedEmployees.length} {selectedEmployees.length === 1 ? 'colaborador' : 'colaboradores'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SEÇÃO 1: Resumo de Filtro */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          📋 Resumo Filtrado
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <CardStat 
            icon="👥"
            label="Funcionários"
            value={resumo_filtro.funcionarios}
            color="blue"
            isNumber
          />
          <CardStat 
            icon="💰"
            label="Total Proventos"
            value={resumo_filtro.total_proventos}
            color="green"
            prefix="R$"
          />
          <CardStat 
            icon="💸"
            label="Total Descontos"
            value={resumo_filtro.total_descontos}
            color="red"
            prefix="R$"
          />
          <CardStat 
            icon="💵"
            label="Total Líquido"
            value={resumo_filtro.total_liquido}
            color="teal"
            prefix="R$"
          />
        </div>
      </div>

      {/* SEÇÃO 2: Informações Salariais */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💼 Informações Salariais
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardStat 
            icon="💵"
            label="Total Salários Base"
            value={informacoes_salariais.total_salarios_base}
            color="blue"
            prefix="R$"
            subtitle="Soma de todos os salários"
          />
          <CardStat 
            icon="📊"
            label="Salário Médio"
            value={informacoes_salariais.salario_medio}
            color="indigo"
            prefix="R$"
            subtitle="Média por funcionário"
          />
          <CardStat 
            icon="💎"
            label="Líquido Médio"
            value={informacoes_salariais.liquido_medio}
            color="purple"
            prefix="R$"
            subtitle="Média por funcionário"
          />
        </div>
      </div>

      {/* SEÇÃO 3: Adicionais e Benefícios */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💎 Adicionais e Benefícios
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <CardStatMini icon="🎁" label="Gratificações" value={adicionais_beneficios.gratificacoes} color="amber" />
          <CardStatMini icon="⚠️" label="Periculosidade" value={adicionais_beneficios.periculosidade} color="orange" />
          <CardStatMini icon="🏥" label="Insalubridade" value={adicionais_beneficios.insalubridade} color="yellow" />
          <CardStatMini icon="🚌" label="Vale Transporte" value={adicionais_beneficios.vale_transporte} color="gray" />
          <CardStatMini icon="🏥" label="Plano de Saúde" value={adicionais_beneficios.plano_saude} color="blue" />
          <CardStatMini icon="🚗" label="Vale Mobilidade" value={adicionais_beneficios.vale_mobilidade} color="gray" />
          <CardStatMini icon="🍽️" label="Vale Refeição" value={adicionais_beneficios.vale_refeicao} color="gray" />
          <CardStatMini icon="🛒" label="Vale Alimentação" value={adicionais_beneficios.vale_alimentacao} color="gray" />
          <CardStatMini icon="💰" label="Saldo Livre" value={adicionais_beneficios.saldo_livre} color="gray" />
          <CardStatMini icon="🔄" label="Transferência Filial" value={adicionais_beneficios.transferencia_filial} color="cyan" />
          <CardStatMini icon="💵" label="Ajuda de Custo" value={adicionais_beneficios.ajuda_custo} color="teal" />
          <CardStatMini icon="👶" label="Licença Paternidade" value={adicionais_beneficios.licenca_paternidade} color="pink" />
        </div>
      </div>

      {/* SEÇÃO 4: Encargos Trabalhistas */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          🏛️ Encargos Trabalhistas
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardStat icon="🏛️" label="INSS" value={encargos_trabalhistas.inss} color="blue" prefix="R$" />
          <CardStat icon="📝" label="IRRF" value={encargos_trabalhistas.irrf} color="indigo" prefix="R$" />
          <CardStat icon="🏦" label="FGTS" value={encargos_trabalhistas.fgts} color="green" prefix="R$" />
        </div>
      </div>

      {/* SEÇÃO 5: Horas Extras */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          ⏰ Horas Extras
        </h3>
        
        {/* Horas Extras Diurnas */}
        <div className="mb-4">
          <h4 className={`text-sm font-medium ${config.classes.text} mb-2`}>☀️ Diurnas</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <CardStatMini icon="☀️" label="DSR Diurno" value={horas_extras.dsr_diurno} color="yellow" />
            <CardStatMini icon="⏰" label="HE 50% Diurno" value={horas_extras.he50_diurno} color="amber" />
            <CardStatMini icon="⏰⏰" label="HE 100% Diurno" value={horas_extras.he100_diurno} color="orange" />
          </div>
        </div>
        
        {/* Horas Extras Noturnas */}
        <div>
          <h4 className={`text-sm font-medium ${config.classes.text} mb-2`}>🌙 Noturnas</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <CardStatMini icon="🌙" label="Adicional Noturno" value={horas_extras.adicional_noturno} color="indigo" />
            <CardStatMini icon="🌙" label="DSR Noturno" value={horas_extras.dsr_noturno} color="blue" />
            <CardStatMini icon="🌙⏰" label="HE 50% Noturno" value={horas_extras.he50_noturno} color="purple" />
            <CardStatMini icon="🌙⏰⏰" label="HE 100% Noturno" value={horas_extras.he100_noturno} color="violet" />
          </div>
        </div>
      </div>

      {/* SEÇÃO 6: Atestados Médicos e Horas Faltas */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          🏥 Atestados Médicos e Horas Faltas
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardStat icon="❌" label="Horas Faltas" value={atestados_faltas.horas_faltas} color="red" prefix="R$" />
          <CardStat icon="🏥" label="Atestados Médicos" value={atestados_faltas.atestados_medicos} color="blue" prefix="R$" />
        </div>
      </div>

      {/* SEÇÃO 7: Empréstimos */}
      <div className={`${config.classes.card} p-6 rounded-lg shadow`}>
        <h3 className={`text-lg font-semibold ${config.classes.text} mb-4`}>
          💳 Empréstimos
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardStat icon="💳" label="Empréstimo do Trabalhador" value={emprestimos.emprestimo_trabalhador} color="orange" prefix="R$" />
          <CardStat icon="💰" label="Adiantamentos" value={emprestimos.adiantamentos} color="amber" prefix="R$" />
        </div>
      </div>
    </div>
  );
};

// Componente para cards grandes
const CardStat = ({ icon, label, value, color, prefix = '', subtitle = '', isNumber = false }) => {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    green: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    red: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    teal: 'bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-800',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800',
    purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
    amber: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    orange: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
  };

  const formatValue = (val) => {
    if (isNumber) return val;
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val || 0);
  };

  return (
    <div className={`border rounded-lg p-4 ${colorClasses[color] || colorClasses.blue}`}>
      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 flex items-center gap-2">
        <span>{icon}</span>
        {label}
      </p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
        {prefix && <span className="text-lg">{prefix} </span>}
        {formatValue(value)}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
      )}
    </div>
  );
};

// Componente para cards pequenos
const CardStatMini = ({ icon, label, value, color }) => {
  const colorClasses = {
    amber: 'bg-amber-50 dark:bg-amber-900/20',
    orange: 'bg-orange-50 dark:bg-orange-900/20',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20',
    blue: 'bg-blue-50 dark:bg-blue-900/20',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20',
    purple: 'bg-purple-50 dark:bg-purple-900/20',
    violet: 'bg-violet-50 dark:bg-violet-900/20',
    cyan: 'bg-cyan-50 dark:bg-cyan-900/20',
    teal: 'bg-teal-50 dark:bg-teal-900/20',
    pink: 'bg-pink-50 dark:bg-pink-900/20',
    gray: 'bg-gray-50 dark:bg-gray-800/50',
    green: 'bg-green-50 dark:bg-green-900/20',
    red: 'bg-red-50 dark:bg-red-900/20',
  };

  const formatValue = (val) => {
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val || 0);
  };

  return (
    <div className={`border rounded-lg p-3 ${colorClasses[color] || colorClasses.gray}`}>
      <p className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center gap-1">
        <span>{icon}</span>
        {label}
      </p>
      <p className="text-lg font-bold text-gray-900 dark:text-white mt-1">
        R$ {formatValue(value)}
      </p>
    </div>
  );
};

export default PayrollV2;
