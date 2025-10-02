import React, { useState, useEffect } from 'react';
import { PaperAirplaneIcon, DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';

const CommunicationSender = () => {
  const [employees, setEmployees] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [message, setMessage] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectionMode, setSelectionMode] = useState('individual'); // individual, department, all

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const response = await api.get('/employees');
      setEmployees(response.data);
    } catch (error) {
      toast.error('Erro ao carregar colaboradores');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Tipo de arquivo não suportado. Use JPG, PNG, GIF ou PDF');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/files/upload', formData);
      setUploadedFile(response.data);
      toast.success('Arquivo enviado com sucesso!');
    } catch (error) {
      toast.error('Erro ao enviar arquivo');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const handleSelectionModeChange = (mode) => {
    setSelectionMode(mode);
    setSelectedEmployees([]);
  };

  const handleEmployeeSelection = (employeeId) => {
    setSelectedEmployees(prev => {
      if (prev.includes(employeeId)) {
        return prev.filter(id => id !== employeeId);
      } else {
        return [...prev, employeeId];
      }
    });
  };

  const handleDepartmentSelection = (department) => {
    const employeesInDept = employees
      .filter(emp => emp.department === department)
      .map(emp => emp.id);
    
    setSelectedEmployees(employeesInDept);
  };

  const selectAllEmployees = () => {
    setSelectedEmployees(employees.map(emp => emp.id));
  };

  const handleSendCommunication = async () => {
    if (!message.trim() && !uploadedFile) {
      toast.error('Digite uma mensagem ou envie um arquivo');
      return;
    }

    if (selectedEmployees.length === 0) {
      toast.error('Selecione pelo menos um destinatário');
      return;
    }

    setSending(true);
    
    try {
      const response = await api.post('/communications/send', {
        selectedEmployees,
        message,
        uploadedFile
      });
      
      const { success_count, failed_employees, message: result_message } = response.data;
      
      if (success_count > 0) {
        toast.success(result_message);
      }
      
      if (failed_employees && failed_employees.length > 0) {
        toast.error(`${failed_employees.length} envios falharam. Verifique os logs.`);
        console.warn('Envios que falharam:', failed_employees);
      }
      
      // Limpar formulário após envio bem-sucedido
      if (success_count === selectedEmployees.length) {
        setMessage('');
        setSelectedEmployees([]);
        setUploadedFile(null);
      }
      
    } catch (error) {
      console.error('Erro ao enviar comunicado:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar comunicado');
    } finally {
      setSending(false);
    }
  };

  const departments = [...new Set(employees.map(emp => emp.department).filter(Boolean))];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Envio de Comunicados</h1>
      </div>

      {/* Conteúdo do Comunicado */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          1. Conteúdo do Comunicado
        </h2>
        
        <div className="space-y-4">
          {/* Mensagem de Texto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mensagem
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="Digite a mensagem do comunicado..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Upload de Arquivo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Arquivo Anexo (Opcional)
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
              <div className="text-center">
                <DocumentArrowUpIcon className="mx-auto h-8 w-8 text-gray-400" />
                <div className="mt-2">
                  <label htmlFor="communication-file" className="cursor-pointer">
                    <span className="text-sm font-medium text-gray-900">
                      Clique para enviar arquivo
                    </span>
                    <input
                      id="communication-file"
                      type="file"
                      accept="image/*,.pdf"
                      onChange={handleFileUpload}
                      disabled={uploading}
                      className="hidden"
                    />
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    JPG, PNG, GIF ou PDF até 25MB
                  </p>
                </div>
              </div>
              
              {uploading && (
                <div className="mt-2 flex items-center justify-center">
                  <div className="spinner w-5 h-5 mr-2"></div>
                  <span className="text-sm text-gray-600">Enviando...</span>
                </div>
              )}
            </div>

            {uploadedFile && (
              <div className="mt-2 p-3 bg-gray-50 rounded border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {uploadedFile.original_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    onClick={() => setUploadedFile(null)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remover
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Seleção de Destinatários */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          2. Selecionar Destinatários
        </h2>

        {/* Modo de Seleção */}
        <div className="mb-4">
          <div className="flex space-x-4">
            <button
              onClick={() => handleSelectionModeChange('individual')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                selectionMode === 'individual'
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              Individual
            </button>
            <button
              onClick={() => handleSelectionModeChange('department')}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                selectionMode === 'department'
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              Por Departamento
            </button>
            <button
              onClick={() => {
                handleSelectionModeChange('all');
                selectAllEmployees();
              }}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                selectionMode === 'all'
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              Todos
            </button>
          </div>
        </div>

        {/* Seleção por Departamento */}
        {selectionMode === 'department' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Selecionar Departamento
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {departments.map((dept) => (
                <button
                  key={dept}
                  onClick={() => handleDepartmentSelection(dept)}
                  className="px-3 py-2 text-left border border-gray-300 rounded hover:bg-gray-50 text-sm"
                >
                  {dept}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Lista de Colaboradores */}
        {(selectionMode === 'individual' || selectionMode === 'department') && (
          <div className="max-h-96 overflow-y-auto">
            <div className="space-y-2">
              {employees.map((employee) => (
                <div
                  key={employee.id}
                  className="flex items-center p-3 border rounded-lg hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedEmployees.includes(employee.id)}
                    onChange={() => handleEmployeeSelection(employee.id)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div className="ml-3 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {employee.full_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Tel: {employee.phone_number}
                      {employee.department && ` | Depto: ${employee.department}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 text-sm text-gray-600">
          {selectedEmployees.length} destinatário(s) selecionado(s)
        </div>
      </div>

      {/* Botão de Envio */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-medium text-gray-900">3. Enviar Comunicado</h2>
            <p className="text-sm text-gray-600 mt-1">
              O comunicado será enviado via WhatsApp usando a Evolution API
            </p>
          </div>
          
          <button
            onClick={handleSendCommunication}
            disabled={sending || selectedEmployees.length === 0 || (!message.trim() && !uploadedFile)}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? (
              <>
                <div className="spinner w-5 h-5 mr-2"></div>
                Enviando...
              </>
            ) : (
              <>
                <PaperAirplaneIcon className="h-5 w-5 mr-2" />
                Enviar Comunicado
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommunicationSender;
