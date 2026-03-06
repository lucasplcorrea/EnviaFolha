import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import {
  DocumentArrowDownIcon,
  ChartBarIcon,
  UserGroupIcon,
  ArrowPathIcon,
  UsersIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  CheckIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline';

const ReportGenerator = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
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
    months_range: 6
  });
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedSections, setSelectedSections] = useState([]);

  // Tipos de relatórios disponíveis
  const reportTypes = [
    {
      id: 'consolidated',
      name: 'Relatório Consolidado RH',
      description: 'Visão geral com todos os principais indicadores de RH',
      icon: ChartBarIcon,
      color: 'bg-purple-100 text-purple-600',
      sections: ['overview', 'headcount', 'turnover', 'demographics', 'tenure', 'leaves']
    },
    {
      id: 'headcount',
      name: 'Relatório de Efetivo',
      description: 'Análise detalhada do quadro de funcionários por setor e empresa',
      icon: UserGroupIcon,
      color: 'bg-blue-100 text-blue-600',
      sections: ['headcount']
    },
    {
      id: 'turnover',
      name: 'Relatório de Rotatividade',
      description: 'Taxa de turnover, admissões e demissões por período',
      icon: ArrowPathIcon,
      color: 'bg-orange-100 text-orange-600',
      sections: ['turnover']
    },
    {
      id: 'demographics',
      name: 'Relatório Demográfico',
      description: 'Distribuição por idade, gênero e escolaridade',
      icon: UsersIcon,
      color: 'bg-green-100 text-green-600',
      sections: ['demographics']
    },
    {
      id: 'tenure',
      name: 'Relatório de Tempo de Casa',
      description: 'Análise de permanência e senioridade dos colaboradores',
      icon: ClockIcon,
      color: 'bg-indigo-100 text-indigo-600',
      sections: ['tenure']
    },
    {
      id: 'leaves',
      name: 'Relatório de Afastamentos',
      description: 'Férias, licenças e ausências por tipo e período',
      icon: ExclamationTriangleIcon,
      color: 'bg-red-100 text-red-600',
      sections: ['leaves']
    },
    {
      id: 'payroll',
      name: 'Relatório de Folha de Pagamento',
      description: 'Resumo de salários, proventos e descontos por setor',
      icon: CurrencyDollarIcon,
      color: 'bg-emerald-100 text-emerald-600',
      sections: ['payroll']
    },
    {
      id: 'custom',
      name: 'Relatório Customizado',
      description: 'Monte seu relatório escolhendo as seções desejadas',
      icon: DocumentTextIcon,
      color: 'bg-gray-100 text-gray-600',
      sections: []
    }
  ];

  // Seções disponíveis para relatório customizado
  const availableSections = [
    { id: 'overview', name: 'Visão Geral', icon: ChartBarIcon },
    { id: 'headcount', name: 'Efetivo', icon: UserGroupIcon },
    { id: 'turnover', name: 'Rotatividade', icon: ArrowPathIcon },
    { id: 'demographics', name: 'Demografia', icon: UsersIcon },
    { id: 'tenure', name: 'Tempo de Casa', icon: ClockIcon },
    { id: 'leaves', name: 'Afastamentos', icon: ExclamationTriangleIcon },
    { id: 'payroll', name: 'Folha de Pagamento', icon: CurrencyDollarIcon }
  ];

  // Empresas fixas
  const companies = [
    { code: '0059', name: 'Infraestrutura' },
    { code: '0060', name: 'Empreendimentos' }
  ];

  // Carregar filtros na montagem
  useEffect(() => {
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
        
        const divisionNames = (divisionsData.departments || []).map(d => 
          typeof d === 'object' ? d.name : d
        ).filter(Boolean);
        
        const years = yearsData.years || [];
        const months = monthsData.months || [];
        
        setFilters({ years, months, divisions: divisionNames });
        
        if (years.length > 0 && months.length > 0) {
          const latestYear = Math.max(...years);
          const latestMonth = months[months.length - 1].number;
          setSelectedFilters(prev => ({ ...prev, year: latestYear, month: latestMonth }));
        }
      } catch (error) {
        console.error('Erro ao carregar filtros:', error);
        toast.error('Erro ao carregar filtros');
      }
    };
    
    loadFilters();
  }, []);

  const handleFilterChange = (field, value) => {
    setSelectedFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleReportSelect = (report) => {
    setSelectedReport(report);
    if (report.id !== 'custom') {
      setSelectedSections(report.sections);
    } else {
      setSelectedSections([]);
    }
  };

  const toggleSection = (sectionId) => {
    setSelectedSections(prev => 
      prev.includes(sectionId) 
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };

  const handleGenerateReport = async () => {
    if (!selectedReport) {
      toast.error('Selecione um tipo de relatório');
      return;
    }
    
    if (selectedSections.length === 0) {
      toast.error('Selecione pelo menos uma seção para o relatório');
      return;
    }
    
    if (!selectedFilters.year || !selectedFilters.month) {
      toast.error('Selecione o período do relatório');
      return;
    }
    
    setGenerating(true);
    
    try {
      const token = localStorage.getItem('token');
      
      const params = new URLSearchParams({
        report_type: selectedReport.id,
        sections: selectedSections.join(','),
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
      
      const response = await fetch(`http://localhost:8002/api/v1/reports/generate?${params}`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Erro ao gerar relatório');
      }
      
      // Novo sistema: recebe JSON com caminho do arquivo HTML
      const responseData = await response.json();
      
      if (responseData.success) {
        toast.success(
          '✅ Relatório aberto no navegador! Use Ctrl+P para imprimir ou salvar como PDF.',
          { duration: 6000 }
        );
      } else {
        throw new Error(responseData.message || 'Erro ao gerar relatório');
      }
      
    } catch (error) {
      console.error('Erro ao gerar relatório:', error);
      toast.error(error.message || 'Erro ao gerar relatório');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">📄 Geração de Relatórios</h2>
          <p className="text-sm text-gray-600 mt-1">
            Gere relatórios em PDF com os indicadores de RH
          </p>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔍 Filtros do Relatório</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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

      {/* Seleção de Tipo de Relatório */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 Tipo de Relatório</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {reportTypes.map((report) => (
            <div
              key={report.id}
              onClick={() => handleReportSelect(report)}
              className={`cursor-pointer p-4 rounded-lg border-2 transition-all ${
                selectedReport?.id === report.id
                  ? 'border-indigo-500 bg-indigo-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${report.color}`}>
                  <report.icon className="h-6 w-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900 text-sm">{report.name}</h4>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{report.description}</p>
                </div>
                {selectedReport?.id === report.id && (
                  <CheckIcon className="h-5 w-5 text-indigo-600 flex-shrink-0" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Seções do Relatório Customizado */}
      {selectedReport?.id === 'custom' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">✏️ Seções do Relatório</h3>
          <p className="text-sm text-gray-600 mb-4">Selecione as seções que deseja incluir no relatório:</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {availableSections.map((section) => (
              <div
                key={section.id}
                onClick={() => toggleSection(section.id)}
                className={`cursor-pointer p-3 rounded-lg border-2 text-center transition-all ${
                  selectedSections.includes(section.id)
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <section.icon className={`h-6 w-6 mx-auto mb-2 ${
                  selectedSections.includes(section.id) ? 'text-indigo-600' : 'text-gray-400'
                }`} />
                <span className={`text-sm font-medium ${
                  selectedSections.includes(section.id) ? 'text-indigo-600' : 'text-gray-600'
                }`}>
                  {section.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Preview e Botão de Gerar */}
      {selectedReport && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📑 Resumo do Relatório</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Informações do Relatório</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Tipo:</span>
                  <span className="text-sm font-medium text-gray-900">{selectedReport.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Período:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {filters.months.find(m => m.number === selectedFilters.month)?.name || ''} / {selectedFilters.year}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Empresa:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {selectedFilters.company === 'all' ? 'Todas' : companies.find(c => c.code === selectedFilters.company)?.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Setor:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {selectedFilters.division === 'all' ? 'Todos' : selectedFilters.division}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Evolução:</span>
                  <span className="text-sm font-medium text-gray-900">{selectedFilters.months_range} meses</span>
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Seções Incluídas</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {selectedSections.map(sectionId => {
                    const section = availableSections.find(s => s.id === sectionId);
                    return section ? (
                      <span key={sectionId} className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">
                        <section.icon className="h-4 w-4" />
                        {section.name}
                      </span>
                    ) : null;
                  })}
                  {selectedSections.length === 0 && (
                    <span className="text-sm text-gray-500">Nenhuma seção selecionada</span>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleGenerateReport}
              disabled={generating || selectedSections.length === 0}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                generating || selectedSections.length === 0
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}
            >
              {generating ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Gerando...
                </>
              ) : (
                <>
                  <DocumentArrowDownIcon className="h-5 w-5" />
                  Gerar Relatório PDF
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Histórico de Relatórios (opcional) */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📚 Dicas</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
            <div className="text-2xl">💡</div>
            <div>
              <h4 className="font-medium text-blue-900 text-sm">Relatório Consolidado</h4>
              <p className="text-xs text-blue-700 mt-1">Ideal para reuniões gerenciais e apresentações executivas</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
            <div className="text-2xl">📊</div>
            <div>
              <h4 className="font-medium text-green-900 text-sm">Relatórios Específicos</h4>
              <p className="text-xs text-green-700 mt-1">Use para análises detalhadas de indicadores específicos</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-purple-50 rounded-lg">
            <div className="text-2xl">✏️</div>
            <div>
              <h4 className="font-medium text-purple-900 text-sm">Relatório Customizado</h4>
              <p className="text-xs text-purple-700 mt-1">Monte seu próprio relatório selecionando as seções desejadas</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportGenerator;
