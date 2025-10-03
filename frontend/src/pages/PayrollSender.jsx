import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import {
  PaperAirplaneIcon,
  TrashIcon,
  PhoneIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  UserIcon,
  ChatBubbleLeftIcon
} from '@heroicons/react/24/outline';

const PayrollSender = () => {
  const [payrollFiles, setPayrollFiles] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [loading, setLoading] = useState(true);
  const [sendingBulk, setSendingBulk] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [messageTemplate, setMessageTemplate] = useState(
    'Olá {nome}, este é seu holerite de {mes_anterior}. A senha são os 4 primeiros dígitos do seu CPF. A {empresa} agradece sua dedicação e esforço!'
  );
  
  // Estados para envio individual
  const [individualSending, setIndividualSending] = useState({});
  const [manualPhone, setManualPhone] = useState('');
  const [manualMessage, setManualMessage] = useState('');
  const [showManualSend, setShowManualSend] = useState(null);
  
  // Estados para filtros
  const [monthFilter, setMonthFilter] = useState('');
  const [availableMonths, setAvailableMonths] = useState([]);

  useEffect(() => {
    loadPayrollFiles();
  }, [monthFilter]);

  const loadPayrollFiles = async () => {
    try {
      setLoading(true);
      const params = monthFilter ? `?month=${encodeURIComponent(monthFilter)}` : '';
      const response = await api.get(`/payrolls/processed${params}`);
      setPayrollFiles(response.data.files || []);
      setStatistics(response.data.statistics || {});
      
      // Extrair meses disponíveis para o filtro
      if (!monthFilter) {
        const months = [...new Set(response.data.files?.map(f => f.month_year) || [])];
        setAvailableMonths(months.filter(m => m !== 'desconhecido').sort());
      }
    } catch (error) {
      console.error('Erro ao carregar holerites:', error);
      toast.error('Erro ao carregar holerites processados');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectFile = (file, checked) => {
    if (checked) {
      if (file.can_send) {
        setSelectedFiles(prev => [...prev, file]);
      } else {
        toast.error('Este arquivo não pode ser enviado (colaborador sem telefone)');
      }
    } else {
      setSelectedFiles(prev => prev.filter(f => f.filename !== file.filename));
    }
  };

  const handleSelectAll = (type) => {
    if (type === 'ready') {
      const readyFiles = payrollFiles.filter(f => f.can_send);
      setSelectedFiles(readyFiles);
    } else if (type === 'none') {
      setSelectedFiles([]);
    }
  };

  const handleDeleteFile = async (filename) => {
    if (!window.confirm(`Tem certeza que deseja remover o arquivo: ${filename}?`)) {
      return;
    }

    try {
      await api.post('/payrolls/delete-file', { filename });
      toast.success('Arquivo removido com sucesso');
      loadPayrollFiles(); // Recarregar lista
    } catch (error) {
      console.error('Erro ao remover arquivo:', error);
      toast.error(error.response?.data?.detail || 'Erro ao remover arquivo');
    }
  };

  const handleIndividualSend = async (file) => {
    const phone = manualPhone.trim();
    const message = manualMessage.trim();

    if (!phone) {
      toast.error('Digite o número do telefone');
      return;
    }

    if (phone.length < 10) {
      toast.error('Número de telefone deve ter pelo menos 10 dígitos');
      return;
    }

    try {
      setIndividualSending(prev => ({ ...prev, [file.filename]: true }));

      await api.post('/payrolls/send-individual', {
        filename: file.filename,
        phone_number: phone,
        message: message
      });

      toast.success(`Holerite enviado para ${phone}`);
      setShowManualSend(null);
      setManualPhone('');
      setManualMessage('');
      
    } catch (error) {
      console.error('Erro no envio individual:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar holerite');
    } finally {
      setIndividualSending(prev => ({ ...prev, [file.filename]: false }));
    }
  };

  const handleBulkSend = async () => {
    if (selectedFiles.length === 0) {
      toast.error('Selecione pelo menos um arquivo para enviar');
      return;
    }

    if (!messageTemplate.trim()) {
      toast.error('Digite uma mensagem para acompanhar os holerites');
      return;
    }

    // Aviso sobre o tempo estimado com delay anti-bot
    const estimatedTime = selectedFiles.length > 1 ? 
      Math.round((selectedFiles.length - 1) * 27) : 0; // Média de 27 segundos entre envios
    
    if (selectedFiles.length > 1) {
      const confirmMessage = `Atenção: O envio de ${selectedFiles.length} holerites incluirá delays aleatórios entre 7-47 segundos para evitar detecção de bot.\n\nTempo estimado: ${Math.floor(estimatedTime / 60)}min ${estimatedTime % 60}s\n\nDeseja continuar?`;
      
      if (!window.confirm(confirmMessage)) {
        return;
      }
    }

    try {
      setSendingBulk(true);

      const filesToSend = selectedFiles.map(file => ({
        filename: file.filename,
        employee: file.associated_employee,
        month_year: file.month_year
      }));

      toast.loading('Iniciando envio de holerites...', { duration: 3000 });

      const response = await api.post('/payrolls/bulk-send', {
        selected_files: filesToSend,
        message_template: messageTemplate
      });

      const { success_count, total_count, failed_count } = response.data;
      
      if (failed_count === 0) {
        toast.success(`Todos os ${success_count} holerites foram enviados e movidos para a pasta 'enviados'!`);
      } else {
        toast.success(`${success_count}/${total_count} holerites enviados com sucesso`);
        if (failed_count > 0) {
          toast.error(`${failed_count} envios falharam. Verifique o log.`);
        }
      }

      // Limpar seleção
      setSelectedFiles([]);
      
      // Recarregar lista (arquivos enviados não aparecerão mais)
      setTimeout(() => {
        loadPayrollFiles();
      }, 1000);

    } catch (error) {
      console.error('Erro no envio em lote:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar holerites');
    } finally {
      setSendingBulk(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusBadge = (file) => {
    if (file.is_orphan) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <ExclamationTriangleIcon className="w-3 h-3 mr-1" />
          Órfão
        </span>
      );
    }
    
    if (file.can_send) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircleIcon className="w-3 h-3 mr-1" />
          Pronto
        </span>
      );
    }
    
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <ExclamationTriangleIcon className="w-3 h-3 mr-1" />
        Sem telefone
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Envio de Holerites</h1>
        
        {/* Estatísticas */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-center">
              <DocumentTextIcon className="h-8 w-8 text-blue-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-blue-600">Total de Arquivos</p>
                <p className="text-2xl font-bold text-blue-900">{statistics.total || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="flex items-center">
              <CheckCircleIcon className="h-8 w-8 text-green-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-green-600">Prontos para Envio</p>
                <p className="text-2xl font-bold text-green-900">{statistics.ready || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-8 w-8 text-yellow-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-yellow-600">Arquivos Órfãos</p>
                <p className="text-2xl font-bold text-yellow-900">{statistics.orphan || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="flex items-center">
              <UserIcon className="h-8 w-8 text-purple-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-purple-600">Associados</p>
                <p className="text-2xl font-bold text-purple-900">{statistics.associated || 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-white p-4 rounded-lg shadow mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Filtros</h3>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-64">
              <label htmlFor="monthFilter" className="block text-sm font-medium text-gray-700 mb-2">
                Filtrar por Mês/Ano
              </label>
              <select
                id="monthFilter"
                value={monthFilter}
                onChange={(e) => setMonthFilter(e.target.value)}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos os meses</option>
                {availableMonths.map(month => (
                  <option key={month} value={month}>
                    {month.charAt(0).toUpperCase() + month.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            
            {monthFilter && (
              <div className="flex items-end">
                <button
                  onClick={() => setMonthFilter('')}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Limpar Filtro
                </button>
              </div>
            )}
          </div>
          
          {monthFilter && (
            <div className="mt-2 text-sm text-gray-600">
              Mostrando apenas holerites de: <strong>{monthFilter}</strong>
            </div>
          )}
        </div>

        {/* Controles de seleção */}
        {payrollFiles.filter(f => f.can_send).length > 0 && (
          <div className="bg-white p-4 rounded-lg shadow mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Envio em Lote</h3>
            
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                onClick={() => handleSelectAll('ready')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Selecionar Todos Prontos
              </button>
              <button
                onClick={() => handleSelectAll('none')}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Desmarcar Todos
              </button>
              <span className="text-sm text-gray-500 self-center">
                {selectedFiles.length} arquivo(s) selecionado(s)
              </span>
            </div>

            <div className="mb-4">
              <label htmlFor="messageTemplate" className="block text-sm font-medium text-gray-700 mb-2">
                Mensagem para acompanhar os holerites
              </label>
              <textarea
                id="messageTemplate"
                value={messageTemplate}
                onChange={(e) => setMessageTemplate(e.target.value)}
                rows={3}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="Digite a mensagem que acompanhará todos os holerites..."
              />
              <p className="mt-1 text-xs text-gray-500">
                Variáveis disponíveis: {'{nome}'}, {'{primeiro_nome}'}, {'{mes_anterior}'}, {'{empresa}'}
              </p>
            </div>

            <button
              onClick={handleBulkSend}
              disabled={selectedFiles.length === 0 || sendingBulk}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sendingBulk ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Enviando...
                </>
              ) : (
                <>
                  <PaperAirplaneIcon className="h-4 w-4 mr-2" />
                  Enviar {selectedFiles.length} Holerite(s)
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Lista de arquivos */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {payrollFiles.length === 0 ? (
            <li className="px-6 py-8 text-center">
              <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhum holerite processado</h3>
              <p className="mt-1 text-sm text-gray-500">
                Processe alguns PDFs de holerites primeiro na tela "Processar Holerites".
              </p>
            </li>
          ) : (
            payrollFiles.map((file) => (
              <li key={file.filename} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center flex-1">
                    {file.can_send && (
                      <input
                        type="checkbox"
                        checked={selectedFiles.some(f => f.filename === file.filename)}
                        onChange={(e) => handleSelectFile(file, e.target.checked)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-4"
                      />
                    )}
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-medium text-gray-900">{file.filename}</h3>
                          <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                            <span>ID: {file.unique_id}</span>
                            <span>{formatFileSize(file.size)}</span>
                            <span>{file.month_year}</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(file)}
                        </div>
                      </div>
                      
                      {file.associated_employee && (
                        <div className="mt-2 flex items-center text-sm text-gray-600">
                          <UserIcon className="h-4 w-4 mr-1" />
                          <span>{file.associated_employee.full_name}</span>
                          {file.associated_employee.phone_number && (
                            <>
                              <PhoneIcon className="h-4 w-4 ml-3 mr-1" />
                              <span>{file.associated_employee.phone_number}</span>
                            </>
                          )}
                        </div>
                      )}
                      
                      {file.is_orphan && (
                        <div className="mt-2 text-sm text-yellow-600">
                          ⚠️ Arquivo sem colaborador cadastrado - necessário cadastrar colaborador com unique_id: {file.unique_id}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    {/* Envio individual manual */}
                    <button
                      onClick={() => setShowManualSend(showManualSend === file.filename ? null : file.filename)}
                      className="inline-flex items-center p-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                      title="Envio manual"
                    >
                      <ChatBubbleLeftIcon className="h-4 w-4" />
                    </button>
                    
                    {/* Remover arquivo */}
                    <button
                      onClick={() => handleDeleteFile(file.filename)}
                      className="inline-flex items-center p-2 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-white hover:bg-red-50"
                      title="Remover arquivo"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                
                {/* Painel de envio manual */}
                {showManualSend === file.filename && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Envio Manual</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Número do WhatsApp
                        </label>
                        <input
                          type="text"
                          value={manualPhone}
                          onChange={(e) => setManualPhone(e.target.value)}
                          placeholder="11999999999"
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Mensagem (opcional)
                        </label>
                        <input
                          type="text"
                          value={manualMessage}
                          onChange={(e) => setManualMessage(e.target.value)}
                          placeholder="Seu holerite está anexo..."
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex justify-end space-x-2">
                      <button
                        onClick={() => setShowManualSend(null)}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                      >
                        Cancelar
                      </button>
                      <button
                        onClick={() => handleIndividualSend(file)}
                        disabled={individualSending[file.filename]}
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        {individualSending[file.filename] ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Enviando...
                          </>
                        ) : (
                          <>
                            <PaperAirplaneIcon className="h-4 w-4 mr-2" />
                            Enviar
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
};

export default PayrollSender;