import React, { useState, useEffect } from 'react';
import { PlusIcon, DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const Employees = () => {
  const { config } = useTheme();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importing, setImporting] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  
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
    position: ''
  });

  useEffect(() => {
    loadEmployees();
  }, []);

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
        position: ''
      });
      setShowForm(false);
      setEditingEmployee(null);
      loadEmployees();
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar colaborador');
    }
  };

  const handleEdit = (employee) => {
    setEditingEmployee(employee);
    setFormData({
      unique_id: employee.unique_id,
      full_name: employee.full_name,
      phone_number: employee.phone_number,
      email: employee.email || '',
      department: employee.department || '',
      position: employee.position || ''
    });
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingEmployee(null);
    setFormData({
      unique_id: '',
      full_name: '',
      phone_number: '',
      email: '',
      department: '',
      position: ''
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

      const { imported, errors } = response.data;
      
      if (imported > 0) {
        toast.success(`${imported} colaboradores importados com sucesso!`);
        loadEmployees();
      }
      
      if (errors.length > 0) {
        toast.error(`${errors.length} erros encontrados. Verifique o console.`);
        console.error('Erros na importação:', errors);
      }

      setShowImport(false);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao importar arquivo');
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
                position: ''
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
          <div className={`relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md ${config.classes.card} ${config.classes.border}`}>
            <div className="mt-3">
              <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>
                Importar Colaboradores
              </h3>
              
              <div className="mb-4">
                <p className={`text-sm ${config.classes.textSecondary} mb-2`}>
                  Selecione um arquivo Excel (.xlsx ou .xls) com as colunas:
                </p>
                <ul className={`text-xs ${config.classes.textSecondary} list-disc list-inside mb-4`}>
                  <li><strong>unique_id</strong> - ID único do colaborador</li>
                  <li><strong>full_name</strong> - Nome completo</li>
                  <li><strong>cpf</strong> - CPF do colaborador (obrigatório)</li>
                  <li><strong>phone_number</strong> - Telefone</li>
                  <li><em>email</em> - Email (opcional)</li>
                  <li><em>department</em> - Departamento (opcional)</li>
                  <li><em>position</em> - Cargo (opcional)</li>
                </ul>
              </div>
              
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileImport}
                disabled={importing}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              
              {importing && (
                <div className="mt-4 flex items-center">
                  <div className="spinner w-5 h-5 mr-2"></div>
                  <span className="text-sm text-gray-600">Importando...</span>
                </div>
              )}
              
              <div className="flex justify-end mt-6 space-x-3">
                <button
                  onClick={() => setShowImport(false)}
                  disabled={importing}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancelar
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
              <label className="block text-sm font-medium text-gray-700">ID Único</label>
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
              <label className="block text-sm font-medium text-gray-700">Nome Completo</label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Telefone</label>
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
          <h3 className={`text-lg font-medium ${config.classes.text}`}>
            Lista de Colaboradores ({employees.length})
          </h3>
        </div>
        
        {employees.length === 0 ? (
          <div className={`p-6 text-center ${config.classes.textSecondary}`}>
            Nenhum colaborador cadastrado ainda.
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
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    ID
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Nome
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Telefone
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Departamento
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium ${config.classes.textSecondary} uppercase tracking-wider`}>
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className={`${config.classes.card} divide-y ${config.classes.border}`}>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={selectedEmployees.includes(employee.id)}
                        onChange={(e) => handleSelectEmployee(employee.id, e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {employee.unique_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {employee.full_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {employee.phone_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {employee.department}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button 
                          onClick={() => handleEdit(employee)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Editar
                        </button>
                        <button 
                          onClick={() => handleDelete(employee)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Employees;
