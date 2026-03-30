import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PlusIcon, DocumentArrowUpIcon, ChevronUpIcon, ChevronDownIcon, MapPinIcon, PencilSquareIcon, TrashIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const Employees = () => {
  const navigate = useNavigate();
  const { config } = useTheme();
  const [searchParams] = useSearchParams();
  const [employees, setEmployees] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [workLocations, setWorkLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  
  // Estados de filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [positionFilter, setPositionFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [workLocationFilter, setWorkLocationFilter] = useState('');
  
  // Estado de ordenação
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  
  // Estados para seleção múltipla
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [showBulkEdit, setShowBulkEdit] = useState(false);
  const [bulkEditData, setBulkEditData] = useState({
    department: '',
    position: ''
  });
  
  const [formData, setFormData] = useState({
    unique_id: '',
    full_name: '',
    phone_number: '',
    email: '',
    department: '',
    position: '',
    birth_date: '',
    sex: '',
    marital_status: '',
    admission_date: '',
    contract_type: '',
    status_reason: '',
    company_id: '',
    work_location_id: ''
  });

  useEffect(() => {
    loadEmployees();
    api.get('/companies').then(res => setCompanies(res.data || [])).catch(() => {});
    api.get('/work-locations?active=false').then(res => setWorkLocations(res.data || [])).catch(() => {});
    
    // Check if coming from import page with refresh parameter
    const refresh = searchParams.get('refresh');
    if (refresh) {
      toast.success('Lista de colaboradores atualizada!');
    }
  }, [searchParams]);

  const loadEmployees = async () => {
    try {
      const response = await api.get('/employees');
      // Backend retorna { employees: [...], total: number, source: string }
      setEmployees(response.data.employees || []);
      
      // Limpar seleções inválidas quando os funcionários são recarregados
      const currentEmployeeIds = response.data.employees?.map(emp => emp.id) || [];
      setSelectedEmployees(prev => prev.filter(id => currentEmployeeIds.includes(id)));
      
    } catch (error) {
      console.error('Erro ao carregar colaboradores:', error);
      toast.error('Erro ao carregar colaboradores');
      setEmployees([]); // Garantir que employees seja sempre um array
      setSelectedEmployees([]); // Limpar seleções em caso de erro
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingEmployee) {
        // Atualizar colaborador existente
        await api.put(`/employees/${editingEmployee.id}`, formData);
        toast.success('Colaborador atualizado com sucesso!');
      } else {
        // Criar novo colaborador
        await api.post('/employees', formData);
        toast.success('Colaborador criado com sucesso!');
      }
      
      setFormData({
        unique_id: '',
        full_name: '',
        phone_number: '',
        email: '',
        department: '',
        position: '',
        birth_date: '',
        sex: '',
        marital_status: '',
        admission_date: '',
        contract_type: '',
        status_reason: '',
        company_id: '',
        work_location_id: ''
      });
      setShowForm(false);
      setShowEditModal(false);
      setEditingEmployee(null);
      loadEmployees();
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar colaborador');
    }
  };

  const handleEdit = (employee) => {
    setEditingEmployee(employee);
    setFormData({
      unique_id: employee.unique_id || '',
      full_name: employee.full_name || '',
      phone_number: employee.phone_number || '',
      email: employee.email || '',
      department: employee.department || '',
      position: employee.position || '',
      birth_date: employee.birth_date || '',
      sex: employee.sex || '',
      marital_status: employee.marital_status || '',
      admission_date: employee.admission_date || '',
      contract_type: employee.contract_type || '',
      status_reason: employee.status_reason || '',
      company_id: employee.company_id || '',
      work_location_id: employee.work_location_id || ''
    });
    setShowEditModal(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setShowEditModal(false);
    setEditingEmployee(null);
    setFormData({
      unique_id: '',
      full_name: '',
      phone_number: '',
      email: '',
      department: '',
      position: '',
      birth_date: '',
      sex: '',
      marital_status: '',
      admission_date: '',
      contract_type: '',
      status_reason: '',
      company_id: '',
      work_location_id: ''
    });
  };

  const handleDelete = async (employee) => {
    if (!window.confirm(`Tem certeza que deseja remover ${employee.full_name}?`)) {
      return;
    }

    try {
      await api.delete(`/employees/${employee.id}`);
      toast.success('Colaborador removido com sucesso!');
      loadEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao remover colaborador');
    }
  };

  const handleFileImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error('Por favor, selecione um arquivo Excel (.xlsx ou .xls)');
      return;
    }

    setImporting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/employees/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Usar os campos corretos da resposta
      const imported_count = response.data.imported_count || 0;
      const updated_count = response.data.updated_count || 0;
      const created_list = response.data.created_list || [];
      const updated_list = response.data.updated_list || [];
      const errors = response.data.errors || [];
      
      // Armazenar resultado detalhado
      setImportResult({
        imported_count,
        updated_count,
        created_list,
        updated_list,
        errors
      });
      
      if (imported_count > 0) {
        toast.success(`${imported_count} colaboradores criados com sucesso!`);
      }
      
      if (updated_count > 0) {
        toast.success(`${updated_count} colaboradores atualizados com sucesso!`);
      }
      
      if (errors.length > 0) {
        toast.error(`${errors.length} erros encontrados. Verifique os detalhes abaixo.`);
      }

      // Não fechar o modal automaticamente para mostrar resultado
      // setShowImport(false);
      
      // FORÇAR RELOAD após importação bem-sucedida
      if (imported_count > 0 || updated_count > 0) {
        // Invalidar cache no backend primeiro
        try {
          console.log('🔄 Invalidando cache no backend...');
          await api.post('/employees/cache/invalidate');
          console.log('✅ Cache invalidado com sucesso!');
        } catch (cacheError) {
          console.warn('⚠️ Erro ao invalidar cache:', cacheError);
        }
        
        // Aumentar delay para 1 segundo para garantir que cache foi invalidado
        console.log('🔄 Aguardando 1s antes de recarregar lista de colaboradores...');
        setTimeout(() => {
          console.log('📊 Recarregando lista de colaboradores...');
          loadEmployees();
        }, 1000);
      }
      
    } catch (error) {
      console.error('Erro na importação:', error);
      toast.error(error.response?.data?.error || error.response?.data?.detail || 'Erro ao importar arquivo');
    } finally {
      setImporting(false);
      event.target.value = '';
    }
  };

  // Funções para seleção múltipla
  const handleSelectEmployee = (employeeId, checked) => {
    if (checked) {
      setSelectedEmployees(prev => [...prev, employeeId]);
    } else {
      setSelectedEmployees(prev => prev.filter(id => id !== employeeId));
    }
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedEmployees(employees.map(emp => emp.id));
    } else {
      setSelectedEmployees([]);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedEmployees.length === 0) return;
    
    if (!window.confirm(`Tem certeza que deseja remover ${selectedEmployees.length} colaboradores selecionados?`)) {
      return;
    }

    try {
      await api.delete('/employees/bulk', {
        data: { employee_ids: selectedEmployees }
      });
      
      toast.success(`${selectedEmployees.length} colaboradores removidos com sucesso!`);
      setSelectedEmployees([]);
      loadEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao remover colaboradores');
    }
  };

  const handleBulkEdit = async () => {
    console.log('handleBulkEdit chamado!');
    console.log('selectedEmployees:', selectedEmployees);
    console.log('bulkEditData:', bulkEditData);
    
    if (selectedEmployees.length === 0) {
      console.log('Nenhum funcionário selecionado');
      toast.error('Selecione pelo menos um funcionário para editar');
      return;
    }
    
    try {
      const updateData = {};
      if (bulkEditData.department && bulkEditData.department.trim()) {
        updateData.department = bulkEditData.department.trim();
      }
      if (bulkEditData.position && bulkEditData.position.trim()) {
        updateData.position = bulkEditData.position.trim();
      }
      
      console.log('updateData preparado:', updateData);
      
      if (Object.keys(updateData).length === 0) {
        toast.error('Selecione pelo menos um campo para atualizar');
        return;
      }

      console.log('Enviando bulk edit:', {
        employee_ids: selectedEmployees,
        updates: updateData
      });

      const response = await api.patch('/employees/bulk', {
        employee_ids: selectedEmployees,
        updates: updateData
      });
      
      console.log('Resposta do bulk edit:', response.data);
      
      const updated_count = response.data.updated_count || 0;
      if (updated_count > 0) {
        toast.success(`${updated_count} colaboradores atualizados com sucesso!`);
      } else {
        toast.warning('Nenhum colaborador foi atualizado. Verifique se os funcionários selecionados ainda existem.');
      }
      
      setSelectedEmployees([]);
      setShowBulkEdit(false);
      setBulkEditData({ department: '', position: '' });
      loadEmployees();
    } catch (error) {
      console.error('Erro no bulk edit:', error);
      toast.error(error.response?.data?.detail || error.response?.data?.error || 'Erro ao atualizar colaboradores');
    }
  };

  // Filtrar colaboradores
  const filteredEmployees = employees.filter(employee => {
    const matchesSearch = searchTerm === '' || 
      employee.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      employee.unique_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      employee.phone_number?.includes(searchTerm);
    
    const matchesDepartment = departmentFilter === '' || 
      employee.department?.toLowerCase().includes(departmentFilter.toLowerCase());
    
    const matchesPosition = positionFilter === '' || 
      employee.position?.toLowerCase().includes(positionFilter.toLowerCase());
      
    const matchesCompany = companyFilter === '' ||
      String(employee.company_id) === companyFilter;
      
    const matchesWorkLocation = workLocationFilter === '' ||
      String(employee.work_location_id) === workLocationFilter;
    
    return matchesSearch && matchesDepartment && matchesPosition && matchesCompany && matchesWorkLocation;
  });

  // Ordenar colaboradores filtrados
  const sortedAndFilteredEmployees = useMemo(() => {
    if (!sortConfig.key) return filteredEmployees;
    
    return [...filteredEmployees].sort((a, b) => {
      let aValue, bValue;
      
      if (sortConfig.key === 'unique_id') {
        // Ordenação numérica para ID
        aValue = parseInt(a.unique_id) || 0;
        bValue = parseInt(b.unique_id) || 0;
      } else {
        // Ordenação alfabética para nome e departamento
        aValue = (a[sortConfig.key] || '').toLowerCase();
        bValue = (b[sortConfig.key] || '').toLowerCase();
      }
      
      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [filteredEmployees, sortConfig]);

  // Função para alternar ordenação
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Obter listas únicas para filtros
  const uniqueDepartments = [...new Set(employees.map(e => e.department).filter(Boolean))];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className={`text-2xl font-semibold ${config.classes.text}`}>Colaboradores</h1>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowImport(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
            Importar Excel
          </button>
          <button
            onClick={() => {
              setEditingEmployee(null);
              setFormData({
                unique_id: '',
                full_name: '',
                phone_number: '',
                email: '',
                department: '',
                position: '',
                birth_date: '',
                sex: '',
                marital_status: '',
                admission_date: '',
                contract_type: '',
                status_reason: ''
              });
              setShowForm(true);
            }}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Adicionar Colaborador
          </button>
        </div>
      </div>

      {/* Barra de ações em lote */}
      {selectedEmployees.length > 0 && (
        <div className={`${config.classes.card} shadow rounded-lg p-4 mb-6 ${config.classes.border}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <span className={`text-sm font-medium ${config.classes.text}`}>
                {selectedEmployees.length} colaborador(es) selecionado(s)
              </span>
              <button
                onClick={() => setSelectedEmployees([])}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Limpar seleção
              </button>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowBulkEdit(true)}
                className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Editar em Lote
              </button>
              <button
                onClick={handleBulkDelete}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Excluir Selecionados
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Importação */}
      {showImport && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className={`relative top-20 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md ${config.classes.card} ${config.classes.border}`}>
            <div className="mt-3">
              <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
                Importar Colaboradores
              </h3>
              
              <div className="mb-4">
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
                  <p className="text-sm text-blue-800 font-medium mb-2">
                    📋 Campos obrigatórios no arquivo Excel:
                  </p>
                  <ul className="text-xs text-blue-700 list-disc list-inside grid grid-cols-2 gap-2">
                    <li><strong>nome</strong> - Nome completo</li>
                    <li><strong>cpf</strong> - CPF (11 dígitos, sem pontos)</li>
                    <li><strong>matricula</strong> - Número da matrícula</li>
                    <li><strong>company_code</strong> - Código da empresa (ex: 0059)</li>
                    <li><strong>data_admissao</strong> - Data de admissão</li>
                  </ul>
                </div>

                <div className="bg-gray-50 border border-gray-200 rounded-md p-4 mb-4">
                  <p className="text-sm text-gray-700 font-medium mb-2">
                    📝 Campos opcionais:
                  </p>
                  <ul className="text-xs text-gray-600 list-disc list-inside grid grid-cols-2 gap-2">
                    <li>cargo</li>
                    <li>departamento</li>
                    <li>sexo (M/F)</li>
                    <li>data_nascimento <em>(DD-MM-AAAA)</em></li>
                    <li>estado_civil</li>
                    <li>tipo_contrato</li>
                    <li>telefone</li>
                    <li>email</li>
                    <li>situacao</li>
                    <li>data_demissao <em>(DD-MM-AAAA)</em></li>
                  </ul>
                </div>

                <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
                  <p className="text-xs text-green-800">
                    <strong>✨ Identificação Automática:</strong> O campo <code className="bg-green-100 px-1 rounded">absolute_id</code> é{' '}
                    <strong>gerado automaticamente</strong> pelo sistema com base no{' '}
                    <code className="bg-green-100 px-1 rounded">company_code</code> +{' '}
                    <code className="bg-green-100 px-1 rounded">matricula</code> +{' '}
                    <code className="bg-green-100 px-1 rounded">cpf</code>. Não inclua essa coluna.
                  </p>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                  <p className="text-xs text-yellow-800">
                    <strong>💡 Dica:</strong> Se o colaborador já existir (mesmo CPF + matrícula + empresa),
                    o cadastro será <strong>atualizado</strong>. Caso contrário, será <strong>criado</strong>.
                  </p>
                </div>

                <div className="mb-4">
                  <a
                    href="/modelo_importacao_colaboradores.xlsx"
                    download
                    className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Baixar Modelo Excel (atualizado)
                  </a>
                </div>
              </div>
              
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileImport}
                disabled={importing}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
              />
              
              {importing && (
                <div className="mt-4 flex items-center">
                  <div className="spinner w-5 h-5 mr-2"></div>
                  <span className="text-sm text-gray-600">Importando e validando dados...</span>
                </div>
              )}
              
              {/* Resultado da Importação */}
              {importResult && !importing && (
                <div className="mt-4 space-y-3">
                  {/* Resumo */}
                  <div className="bg-green-50 border border-green-200 rounded-md p-3">
                    <p className="text-sm font-medium text-green-800 mb-2">
                      ✅ Importação concluída
                    </p>
                    <div className="text-xs text-green-700 space-y-1">
                      {importResult.imported > 0 && (
                        <p>• {importResult.imported} novo(s) colaborador(es) criado(s)</p>
                      )}
                      {importResult.updated > 0 && (
                        <p>• {importResult.updated} colaborador(es) atualizado(s)</p>
                      )}
                    </div>
                  </div>
                  
                  {/* Lista de criados */}
                  {importResult.created_list && importResult.created_list.length > 0 && (
                    <details className="bg-blue-50 border border-blue-200 rounded-md p-3">
                      <summary className="text-sm font-medium text-blue-800 cursor-pointer">
                        📝 Ver {importResult.created_list.length} colaborador(es) criado(s)
                      </summary>
                      <ul className="mt-2 text-xs text-blue-700 space-y-1 max-h-32 overflow-y-auto">
                        {importResult.created_list.map((item, idx) => (
                          <li key={idx}>
                            Linha {item.row}: {item.name} (ID: {item.unique_id})
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  
                  {/* Lista de atualizados */}
                  {importResult.updated_list && importResult.updated_list.length > 0 && (
                    <details className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                      <summary className="text-sm font-medium text-yellow-800 cursor-pointer">
                        🔄 Ver {importResult.updated_list.length} colaborador(es) atualizado(s)
                      </summary>
                      <ul className="mt-2 text-xs text-yellow-700 space-y-1 max-h-32 overflow-y-auto">
                        {importResult.updated_list.map((item, idx) => (
                          <li key={idx}>
                            Linha {item.row}: {item.name} (ID: {item.unique_id})
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  
                  {/* Erros */}
                  {importResult.errors && importResult.errors.length > 0 && (
                    <details className="bg-red-50 border border-red-200 rounded-md p-3">
                      <summary className="text-sm font-medium text-red-800 cursor-pointer">
                        ❌ Ver {importResult.errors.length} erro(s) encontrado(s)
                      </summary>
                      <ul className="mt-2 text-xs text-red-700 space-y-1 max-h-32 overflow-y-auto">
                        {importResult.errors.map((err, idx) => (
                          <li key={idx}>
                            Linha {err.row}: {err.error}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}
              
              <div className="flex justify-end mt-6 space-x-3">
                <button
                  onClick={() => {
                    setShowImport(false);
                    setImportResult(null);
                  }}
                  disabled={importing}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
                >
                  {importResult ? 'Fechar' : 'Cancelar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Edição em Lote */}
      {showBulkEdit && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className={`relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md ${config.classes.card} ${config.classes.border}`}>
            <div className="mt-3">
              <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
                Editar {selectedEmployees.length} Colaborador(es)
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Departamento
                  </label>
                  <input
                    type="text"
                    value={bulkEditData.department}
                    onChange={(e) => setBulkEditData({...bulkEditData, department: e.target.value})}
                    placeholder="Deixe em branco para não alterar"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cargo
                  </label>
                  <input
                    type="text"
                    value={bulkEditData.position}
                    onChange={(e) => setBulkEditData({...bulkEditData, position: e.target.value})}
                    placeholder="Deixe em branco para não alterar"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              
              <div className="flex justify-end mt-6 space-x-3">
                <button
                  onClick={() => {
                    setShowBulkEdit(false);
                    setBulkEditData({ department: '', position: '' });
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleBulkEdit}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Atualizar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Formulário */}
      {showForm && (
        <div className={`${config.classes.card} shadow rounded-lg p-6 mb-6 ${config.classes.border}`}>
          <h2 className={`text-lg font-medium ${config.classes.text} mb-4`}>
            {editingEmployee ? 'Editar Colaborador' : 'Novo Colaborador'}
          </h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">ID Único *</label>
              <input
                type="text"
                required
                value={formData.unique_id}
                onChange={(e) => setFormData({...formData, unique_id: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                placeholder="000012345"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Nome Completo *</label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Telefone *</label>
              <input
                type="tel"
                required
                value={formData.phone_number}
                onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                placeholder="(47) 99999-9999"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Empresa Responsável</label>
              <select
                value={formData.company_id || ''}
                onChange={(e) => {
                  const companyId = e.target.value;
                  const company = companies.find(c => String(c.id) === companyId);
                  
                  let newUniqueId = formData.unique_id;
                  if (company && company.payroll_prefix) {
                      const prefix = company.payroll_prefix.replace(/\D/g, '').padStart(4, '0');
                      const matricula = newUniqueId.slice(-5).padStart(5, '0');
                      newUniqueId = `${prefix}${matricula}`;
                  }

                  setFormData({
                    ...formData, 
                    company_id: companyId ? parseInt(companyId) : '',
                    unique_id: newUniqueId
                  });
                }}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              >
                <option value="">Selecione...</option>
                {companies.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} (Prefixo {c.payroll_prefix})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Local de Trabalho / Obra</label>
              <select
                value={formData.work_location_id || ''}
                onChange={(e) => setFormData({
                  ...formData, 
                  work_location_id: e.target.value ? parseInt(e.target.value) : ''
                })}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              >
                <option value="">Selecione...</option>
                {workLocations
                  .filter(loc => !formData.company_id || loc.company_id === formData.company_id)
                  .map(loc => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Departamento</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({...formData, department: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Cargo</label>
              <input
                type="text"
                value={formData.position}
                onChange={(e) => setFormData({...formData, position: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Data de Nascimento</label>
              <input
                type="date"
                value={formData.birth_date}
                onChange={(e) => setFormData({...formData, birth_date: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Sexo</label>
              <select
                value={formData.sex}
                onChange={(e) => setFormData({...formData, sex: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              >
                <option value="">Selecione...</option>
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Estado Civil</label>
              <select
                value={formData.marital_status}
                onChange={(e) => setFormData({...formData, marital_status: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              >
                <option value="">Selecione...</option>
                <option value="Solteiro">Solteiro(a)</option>
                <option value="Casado">Casado(a)</option>
                <option value="Divorciado">Divorciado(a)</option>
                <option value="Viúvo">Viúvo(a)</option>
                <option value="União Estável">União Estável</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Data de Admissão</label>
              <input
                type="date"
                value={formData.admission_date}
                onChange={(e) => setFormData({...formData, admission_date: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Tipo de Contrato</label>
              <select
                value={formData.contract_type}
                onChange={(e) => setFormData({...formData, contract_type: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              >
                <option value="">Selecione...</option>
                <option value="CLT">CLT</option>
                <option value="PJ">PJ</option>
                <option value="Estágio">Estágio</option>
                <option value="Temporário">Temporário</option>
                <option value="Terceirizado">Terceirizado</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700">Observações / Motivo Status</label>
              <textarea
                value={formData.status_reason}
                onChange={(e) => setFormData({...formData, status_reason: e.target.value})}
                rows="3"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                placeholder="Motivo de desligamento, transferência, etc."
              />
            </div>
            
            <div className="sm:col-span-2 flex justify-end space-x-3">
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                {editingEmployee ? 'Atualizar' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista de colaboradores */}
      <div className={`${config.classes.card} shadow rounded-lg ${config.classes.border}`}>
        <div className={`px-6 py-4 border-b ${config.classes.border}`}>
          <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
            Lista de Colaboradores ({sortedAndFilteredEmployees.length} de {employees.length})
          </h3>
          
          {/* Filtros de Busca */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                🔍 Buscar por Nome, ID ou Telefone
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Digite para buscar..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                🏢 Filtrar por Empresa
              </label>
              <select
                value={companyFilter}
                onChange={(e) => setCompanyFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todas empresas</option>
                {companies.map(c => (
                  <option key={c.id} value={c.id.toString()}>{c.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📍 Local de Trabalho
              </label>
              <select
                value={workLocationFilter}
                onChange={(e) => setWorkLocationFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                disabled={!companyFilter}
              >
                <option value="">{companyFilter ? 'Todos locais' : 'Selecione empresa...'}</option>
                {workLocations.filter(c => companyFilter === '' || String(c.company_id) === companyFilter).map(w => (
                  <option key={w.id} value={w.id.toString()}>{w.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                💼 Departamento
              </label>
              <select
                value={departmentFilter}
                onChange={(e) => setDepartmentFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos departamentos</option>
                {uniqueDepartments.sort().map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Botão para limpar filtros */}
          {(searchTerm || departmentFilter || positionFilter || companyFilter || workLocationFilter) && (
            <div className="mt-3">
              <button
                onClick={() => {
                  setSearchTerm('');
                  setDepartmentFilter('');
                  setPositionFilter('');
                  setCompanyFilter('');
                  setWorkLocationFilter('');
                }}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                ✕ Limpar todos os filtros
              </button>
            </div>
          )}
        </div>
        
        {sortedAndFilteredEmployees.length === 0 ? (
          <div className={`p-6 text-center ${config.classes.textSecondary}`}>
            {employees.length === 0 ? 
              'Nenhum colaborador cadastrado ainda.' :
              'Nenhum colaborador encontrado com os filtros aplicados.'
            }
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className={config.classes.tableHeader}>
                <tr>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    <input
                      type="checkbox"
                      checked={employees.length > 0 && selectedEmployees.length === employees.length}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <th 
                    onClick={() => handleSort('full_name')}
                    className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none`}
                  >
                    <div className="flex items-center space-x-1">
                      <span>👤 Colaborador</span>
                      {sortConfig.key === 'full_name' && (
                        sortConfig.direction === 'asc' ? 
                          <ChevronUpIcon className="h-4 w-4" /> : 
                          <ChevronDownIcon className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    🏢 Alocação
                  </th>
                  <th 
                    onClick={() => handleSort('department')}
                    className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none`}
                  >
                    <div className="flex items-center space-x-1">
                      <span>💼 Área/Cargo</span>
                      {sortConfig.key === 'department' && (
                        sortConfig.direction === 'asc' ? 
                          <ChevronUpIcon className="h-4 w-4" /> : 
                          <ChevronDownIcon className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Status
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                {sortedAndFilteredEmployees.map((employee) => {
                  const companyInfo = companies.find(c => c.id === employee.company_id);
                  const locationInfo = workLocations.find(l => l.id === employee.work_location_id);
                  
                  const getInitials = (name) => {
                    if (!name) return '??';
                    const parts = name.trim().split(' ').filter(Boolean);
                    if (parts.length >= 2) return `${parts[0][0]}${parts[parts.length-1][0]}`.toUpperCase();
                    return name.substring(0, 2).toUpperCase();
                  };

                  return (
                    <tr key={employee.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={selectedEmployees.includes(employee.id)}
                          onChange={(e) => handleSelectEmployee(employee.id, e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-sm">
                              {getInitials(employee.full_name)}
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{employee.full_name}</div>
                            <div className="text-xs text-gray-500 flex items-center mt-0.5">
                              <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded text-gray-600 border mr-2">ID: {employee.unique_id}</span>
                              {employee.phone_number}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 font-medium">
                          {companyInfo ? companyInfo.name : <span className="text-gray-400 italic">Empresa não informada</span>}
                        </div>
                        <div className="text-xs text-gray-500 flex items-center mt-1">
                          <MapPinIcon className="h-3 w-3 mr-1 text-gray-400" />
                          {locationInfo ? locationInfo.name : 'Local não informado'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{employee.department || '-'}</div>
                        <div className="text-xs text-gray-500 mt-1">{employee.position || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${employee.is_active ? 'bg-green-100 text-green-800 border border-green-200' : 'bg-red-100 text-red-800 border border-red-200'}`}>
                          {employee.is_active ? 'Ativo' : 'Desligado'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex space-x-2">
                          <button 
                            onClick={() => navigate(`/employees/${employee.id}`)}
                            title="Ver Perfil"
                            className="text-blue-600 hover:text-blue-900 bg-blue-50 p-1.5 rounded-md border border-blue-100 shadow-sm transition-colors hover:bg-blue-100"
                          >
                            Ver Perfil
                          </button>
                          <button 
                            onClick={() => handleEdit(employee)}
                            title="Editar"
                            className="text-gray-500 hover:text-gray-700 bg-gray-50 p-1.5 rounded-md border border-gray-100 shadow-sm transition-colors hover:bg-gray-100 flex items-center"
                          >
                            <PencilSquareIcon className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => handleDelete(employee)}
                            title="Excluir"
                            className="text-red-500 hover:text-red-700 bg-red-50 p-1.5 rounded-md border border-red-100 shadow-sm transition-colors hover:bg-red-100 flex items-center"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de Edição Rápida */}
      {showEditModal && editingEmployee && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
          <div className={`relative mx-auto p-6 border w-full max-w-3xl shadow-xl rounded-lg ${config.classes.card} ${config.classes.border}`}>
            {/* Header do Modal */}
            <div className="flex justify-between items-center mb-4 pb-3 border-b">
              <div>
                <h3 className={`text-xl font-semibold ${config.classes.text}`}>
                  ✏️ Editar Colaborador
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  {editingEmployee.full_name} - ID: {editingEmployee.unique_id}
                </p>
              </div>
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>

            {/* Formulário */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">ID / Matrícula*</label>
                  <input
                    type="text"
                    required
                    value={formData.unique_id}
                    onChange={(e) => setFormData({...formData, unique_id: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Nome Completo*</label>
                  <input
                    type="text"
                    required
                    value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Telefone*</label>
                  <input
                    type="text"
                    required
                    value={formData.phone_number}
                    onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Departamento</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({...formData, department: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Cargo</label>
                  <input
                    type="text"
                    value={formData.position}
                    onChange={(e) => setFormData({...formData, position: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Tipo de Contrato</label>
                  <select
                    value={formData.contract_type}
                    onChange={(e) => setFormData({...formData, contract_type: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  >
                    <option value="">Selecione...</option>
                    <option value="CLT">CLT</option>
                    <option value="PJ">PJ</option>
                    <option value="Estágio">Estágio</option>
                    <option value="Temporário">Temporário</option>
                    <option value="Terceirizado">Terceirizado</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Sexo</label>
                  <select
                    value={formData.sex}
                    onChange={(e) => setFormData({...formData, sex: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  >
                    <option value="">Selecione...</option>
                    <option value="M">Masculino</option>
                    <option value="F">Feminino</option>
                    <option value="Outro">Outro</option>
                  </select>
                </div>
              </div>

              {/* Botões de Ação */}
              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  💾 Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Employees;

