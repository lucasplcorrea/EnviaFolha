import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  UserCircleIcon, 
  ClockIcon, 
  DocumentTextIcon,
  CalendarIcon,
  BriefcaseIcon,
  CurrencyDollarIcon,
  HeartIcon,
  ArrowLeftIcon,
  PencilIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const EmployeeDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { config } = useTheme();
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');
  const [editingStatus, setEditingStatus] = useState(false);
  const [editingInfo, setEditingInfo] = useState(false);
  
  console.log('🔍 EmployeeDetail montado! ID da URL:', id);
  
  const [statusForm, setStatusForm] = useState({
    employment_status: '',
    termination_date: '',
    leave_start_date: '',
    leave_end_date: '',
    status_reason: ''
  });

  const [infoForm, setInfoForm] = useState({
    unique_id: '',
    full_name: '',
    cpf: '',
    phone_number: '',
    email: '',
    department: '',
    position: '',
    birth_date: '',
    sex: '',
    marital_status: '',
    admission_date: '',
    contract_type: ''
  });

  const loadEmployee = React.useCallback(async () => {
    try {
      console.log('📡 Fazendo requisição para /employees/' + id);
      const response = await api.get(`/employees/${id}`);
      console.log('✅ Dados recebidos:', response.data);
      setEmployee(response.data);
      setStatusForm({
        employment_status: response.data.employment_status || 'Ativo',
        termination_date: response.data.termination_date || '',
        leave_start_date: response.data.leave_start_date || '',
        leave_end_date: response.data.leave_end_date || '',
        status_reason: response.data.status_reason || ''
      });
      setInfoForm({
        unique_id: response.data.unique_id || '',
        full_name: response.data.full_name || '',
        cpf: response.data.cpf || '',
        phone_number: response.data.phone_number || '',
        email: response.data.email || '',
        department: response.data.department || '',
        position: response.data.position || '',
        birth_date: response.data.birth_date || '',
        sex: response.data.sex || '',
        marital_status: response.data.marital_status || '',
        admission_date: response.data.admission_date || '',
        contract_type: response.data.contract_type || ''
      });
    } catch (error) {
      console.error('❌ Erro ao carregar colaborador:', error);
      toast.error('Erro ao carregar dados do colaborador');
      // Se houver erro 404 ou não autorizado, voltar para lista
      if (error.response?.status === 404) {
        console.log('❌ Colaborador não encontrado, redirecionando...');
        navigate('/employees');
      }
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    console.log('🔄 useEffect chamado, carregando employee com ID:', id);
    loadEmployee();
  }, [id, loadEmployee]);

  const handleStatusUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/employees/${id}`, statusForm);
      toast.success('Status atualizado com sucesso!');
      setEditingStatus(false);
      loadEmployee();
    } catch (error) {
      toast.error('Erro ao atualizar status');
    }
  };

  const handleInfoUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.put(`/employees/${id}`, infoForm);
      toast.success('Informações atualizadas com sucesso!');
      setEditingInfo(false);
      loadEmployee();
    } catch (error) {
      toast.error('Erro ao atualizar informações');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('pt-BR');
  };

  const getStatusBadge = (status) => {
    const badges = {
      'Ativo': 'bg-green-100 text-green-800',
      'Afastado': 'bg-yellow-100 text-yellow-800',
      'Férias': 'bg-blue-100 text-blue-800',
      'Desligado': 'bg-red-100 text-red-800',
      'Licença': 'bg-purple-100 text-purple-800'
    };
    return badges[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Colaborador não encontrado</p>
        <button onClick={() => navigate('/employees')} className="mt-4 text-blue-600 hover:text-blue-800">
          Voltar para lista
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={() => navigate('/employees')}
            className="mr-4 p-2 hover:bg-gray-100 rounded-full"
          >
            <ArrowLeftIcon className="h-6 w-6 text-gray-600" />
          </button>
          <div>
            <h1 className={`text-2xl font-semibold ${config.classes.text}`}>
              {employee.full_name}
            </h1>
            <p className="text-sm text-gray-500">ID: {employee.unique_id}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(statusForm.employment_status)}`}>
            {statusForm.employment_status || 'Ativo'}
          </span>
          {!editingInfo && (
            <button
              onClick={() => setEditingInfo(true)}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <PencilIcon className="h-5 w-5 mr-2" />
              Editar Cadastro
            </button>
          )}
          {editingInfo && (
            <div className="flex space-x-2">
              <button
                onClick={handleInfoUpdate}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                Salvar
              </button>
              <button
                onClick={() => {
                  setEditingInfo(false);
                  loadEmployee(); // Recarregar para reverter mudanças
                }}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancelar
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'info', label: 'Informações', icon: UserCircleIcon },
            { id: 'status', label: 'Status', icon: ClockIcon },
            { id: 'movements', label: 'Movimentações', icon: BriefcaseIcon },
            { id: 'leaves', label: 'Afastamentos', icon: CalendarIcon },
            { id: 'payroll', label: 'Folha de Pagamento', icon: CurrencyDollarIcon },
            { id: 'benefits', label: 'Benefícios', icon: HeartIcon }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm`}
            >
              <tab.icon className={`${
                activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
              } -ml-0.5 mr-2 h-5 w-5`} />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className={`${config.classes.card} shadow rounded-lg p-6 ${config.classes.border}`}>
        
        {/* Informações Básicas */}
        {activeTab === 'info' && !editingInfo && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium mb-4">Dados Pessoais</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">ID Único (Matrícula)</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.unique_id || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">CPF</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.cpf || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Data de Nascimento</dt>
                  <dd className="mt-1 text-sm text-gray-900">{formatDate(employee.birth_date)}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Sexo</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.sex || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Estado Civil</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.marital_status || '-'}</dd>
                </div>
              </dl>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4">Contato</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Telefone</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.phone_number || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Email</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.email || '-'}</dd>
                </div>
              </dl>

              <h3 className="text-lg font-medium mb-4 mt-6">Dados Profissionais</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Departamento</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.department || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Cargo</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.position || '-'}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Data de Admissão</dt>
                  <dd className="mt-1 text-sm text-gray-900">{formatDate(employee.admission_date)}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Tipo de Contrato</dt>
                  <dd className="mt-1 text-sm text-gray-900">{employee.contract_type || '-'}</dd>
                </div>
              </dl>
            </div>
          </div>
        )}

        {/* Formulário de Edição de Informações */}
        {activeTab === 'info' && editingInfo && (
          <form onSubmit={handleInfoUpdate} className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h3 className="text-lg font-medium mb-4">Dados Pessoais</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">ID Único (Matrícula) *</label>
                <input
                  type="text"
                  required
                  value={infoForm.unique_id}
                  onChange={(e) => setInfoForm({...infoForm, unique_id: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  placeholder="000012345"
                />
                <p className="mt-1 text-xs text-gray-500">Código da empresa + matrícula do colaborador</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Nome Completo *</label>
                <input
                  type="text"
                  required
                  value={infoForm.full_name}
                  onChange={(e) => setInfoForm({...infoForm, full_name: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">CPF</label>
                <input
                  type="text"
                  value={infoForm.cpf}
                  onChange={(e) => setInfoForm({...infoForm, cpf: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  placeholder="000.000.000-00"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Data de Nascimento</label>
                <input
                  type="date"
                  value={infoForm.birth_date}
                  onChange={(e) => setInfoForm({...infoForm, birth_date: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Sexo</label>
                <select
                  value={infoForm.sex}
                  onChange={(e) => setInfoForm({...infoForm, sex: e.target.value})}
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
                  value={infoForm.marital_status}
                  onChange={(e) => setInfoForm({...infoForm, marital_status: e.target.value})}
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
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium mb-4">Contato e Profissional</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Telefone *</label>
                <input
                  type="tel"
                  required
                  value={infoForm.phone_number}
                  onChange={(e) => setInfoForm({...infoForm, phone_number: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                  placeholder="(47) 99999-9999"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={infoForm.email}
                  onChange={(e) => setInfoForm({...infoForm, email: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Departamento</label>
                <input
                  type="text"
                  value={infoForm.department}
                  onChange={(e) => setInfoForm({...infoForm, department: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Cargo</label>
                <input
                  type="text"
                  value={infoForm.position}
                  onChange={(e) => setInfoForm({...infoForm, position: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Data de Admissão</label>
                <input
                  type="date"
                  value={infoForm.admission_date}
                  onChange={(e) => setInfoForm({...infoForm, admission_date: e.target.value})}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Tipo de Contrato</label>
                <select
                  value={infoForm.contract_type}
                  onChange={(e) => setInfoForm({...infoForm, contract_type: e.target.value})}
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
            </div>
          </form>
        )}

        {/* Status */}
        {activeTab === 'status' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-medium">Gestão de Status</h3>
              {!editingStatus && (
                <button
                  onClick={() => setEditingStatus(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Atualizar Status
                </button>
              )}
            </div>

            {!editingStatus ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-500 mb-2">Status Atual</p>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(statusForm.employment_status)}`}>
                    {statusForm.employment_status || 'Ativo'}
                  </span>
                </div>

                {statusForm.termination_date && (
                  <div className="p-4 bg-red-50 rounded-lg">
                    <p className="text-sm font-medium text-red-900 mb-1">Data de Desligamento</p>
                    <p className="text-sm text-red-700">{formatDate(statusForm.termination_date)}</p>
                  </div>
                )}

                {(statusForm.leave_start_date || statusForm.leave_end_date) && (
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <p className="text-sm font-medium text-yellow-900 mb-2">Período de Afastamento/Férias</p>
                    <div className="text-sm text-yellow-700">
                      <p>Início: {formatDate(statusForm.leave_start_date)}</p>
                      <p>Retorno Previsto: {formatDate(statusForm.leave_end_date)}</p>
                    </div>
                  </div>
                )}

                {statusForm.status_reason && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm font-medium text-blue-900 mb-1">Motivo/Observações</p>
                    <p className="text-sm text-blue-700 whitespace-pre-wrap">{statusForm.status_reason}</p>
                  </div>
                )}
              </div>
            ) : (
              <form onSubmit={handleStatusUpdate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Status
                  </label>
                  <select
                    value={statusForm.employment_status}
                    onChange={(e) => setStatusForm({...statusForm, employment_status: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="Ativo">Ativo</option>
                    <option value="Afastado">Afastado</option>
                    <option value="Férias">Férias</option>
                    <option value="Licença">Licença</option>
                    <option value="Desligado">Desligado</option>
                  </select>
                </div>

                {statusForm.employment_status === 'Desligado' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Data de Desligamento
                    </label>
                    <input
                      type="date"
                      value={statusForm.termination_date}
                      onChange={(e) => setStatusForm({...statusForm, termination_date: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                )}

                {['Afastado', 'Férias', 'Licença'].includes(statusForm.employment_status) && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Data de Início
                      </label>
                      <input
                        type="date"
                        value={statusForm.leave_start_date}
                        onChange={(e) => setStatusForm({...statusForm, leave_start_date: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Data Prevista de Retorno
                      </label>
                      <input
                        type="date"
                        value={statusForm.leave_end_date}
                        onChange={(e) => setStatusForm({...statusForm, leave_end_date: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Motivo/Observações
                  </label>
                  <textarea
                    value={statusForm.status_reason}
                    onChange={(e) => setStatusForm({...statusForm, status_reason: e.target.value})}
                    rows="4"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Descreva o motivo ou adicione observações relevantes..."
                  />
                </div>

                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setEditingStatus(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Salvar Status
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Outras tabs - placeholder */}
        {['movements', 'leaves', 'payroll', 'benefits'].includes(activeTab) && (
          <div className="text-center py-12">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">Em Desenvolvimento</h3>
            <p className="mt-1 text-sm text-gray-500">
              Esta funcionalidade estará disponível em breve.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmployeeDetail;
