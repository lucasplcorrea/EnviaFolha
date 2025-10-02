import React, { useState, useEffect } from 'react';
import { DocumentArrowUpIcon, CloudArrowUpIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';

const PayrollSender = () => {
  const [employees, setEmployees] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [monthYear, setMonthYear] = useState('');
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);

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
    const files = Array.from(event.target.files);
    
    if (files.length === 0) return;

    setUploading(true);
    const uploadedFilesList = [];

    for (const file of files) {
      if (!file.type.includes('pdf')) {
        toast.error(`${file.name} não é um arquivo PDF válido`);
        continue;
      }

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post('/files/upload', formData);
        uploadedFilesList.push({
          ...response.data,
          originalFile: file
        });
        
        toast.success(`${file.name} enviado com sucesso!`);
      } catch (error) {
        toast.error(`Erro ao enviar ${file.name}`);
      }
    }

    setUploadedFiles(prev => [...prev, ...uploadedFilesList]);
    setUploading(false);
    event.target.value = '';
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

  const selectAllEmployees = () => {
    if (selectedEmployees.length === employees.length) {
      setSelectedEmployees([]);
    } else {
      setSelectedEmployees(employees.map(emp => emp.id));
    }
  };

  const handleSendPayrolls = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Faça upload dos arquivos PDF primeiro');
      return;
    }

    if (selectedEmployees.length === 0) {
      toast.error('Selecione pelo menos um colaborador');
      return;
    }

    if (!monthYear.trim()) {
      toast.error('Informe o mês/ano de referência');
      return;
    }

    setSending(true);
    
    try {
      const response = await api.post('/payrolls/send', {
        selectedEmployees,
        uploadedFiles,
        monthYear
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
        setSelectedEmployees([]);
        setUploadedFiles([]);
        setMonthYear('');
      }
      
    } catch (error) {
      console.error('Erro ao enviar holerites:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar holerites');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900">Envio de Holerites</h1>
      </div>

      {/* Upload de Arquivos */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          1. Upload dos Holerites (PDF)
        </h2>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
          <div className="mt-4">
            <label htmlFor="pdf-upload" className="cursor-pointer">
              <span className="mt-2 block text-sm font-medium text-gray-900">
                Clique para enviar arquivos PDF ou arraste aqui
              </span>
              <input
                id="pdf-upload"
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
            <p className="mt-2 text-xs text-gray-500">
              PDF até 25MB (múltiplos arquivos permitidos)
            </p>
          </div>
          
          {uploading && (
            <div className="mt-4 flex items-center justify-center">
              <div className="spinner w-6 h-6 mr-2"></div>
              <span className="text-sm text-gray-600">Enviando arquivos...</span>
            </div>
          )}
        </div>

        {uploadedFiles.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-900 mb-2">
              Arquivos Enviados ({uploadedFiles.length})
            </h3>
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.original_name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <span className="text-xs text-green-600 font-medium">✓ Enviado</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Configurações do Envio */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          2. Configurações do Envio
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mês/Ano de Referência
            </label>
            <input
              type="text"
              value={monthYear}
              onChange={(e) => setMonthYear(e.target.value)}
              placeholder="Ex: Janeiro 2024"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Seleção de Colaboradores */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">
            3. Selecionar Colaboradores
          </h2>
          <button
            onClick={selectAllEmployees}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {selectedEmployees.length === employees.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
          </button>
        </div>

        {employees.length === 0 ? (
          <p className="text-gray-500 text-center py-4">
            Nenhum colaborador cadastrado. Vá para a seção "Colaboradores" para adicionar.
          </p>
        ) : (
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
                      ID: {employee.unique_id} | Tel: {employee.phone_number}
                    </p>
                    {employee.department && (
                      <p className="text-xs text-gray-500">
                        {employee.department}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 text-sm text-gray-600">
          {selectedEmployees.length} de {employees.length} colaboradores selecionados
        </div>
      </div>

      {/* Botão de Envio */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-medium text-gray-900">4. Enviar Holerites</h2>
            <p className="text-sm text-gray-600 mt-1">
              Os holerites serão enviados via WhatsApp usando a Evolution API
            </p>
          </div>
          
          <button
            onClick={handleSendPayrolls}
            disabled={sending || uploadedFiles.length === 0 || selectedEmployees.length === 0}
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
                Enviar Holerites
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PayrollSender;
