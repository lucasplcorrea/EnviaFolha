import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
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
  const { config } = useTheme();
  const [payrollFiles, setPayrollFiles] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [loading, setLoading] = useState(true);
  const [sendingBulk, setSendingBulk] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // Estados para job em background
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [showProgressModal, setShowProgressModal] = useState(false);
  
  // Estados para filas ativas do sistema
  const [activeQueues, setActiveQueues] = useState([]);
  const [queuesPollingInterval, setQueuesPollingInterval] = useState(null);
  
  // Múltiplos templates de mensagem para randomização (8 templates)
  const [messageTemplate1, setMessageTemplate1] = useState(
    'Olá {nome}, segue seu holerite de {mes_anterior}. A senha para abrir o arquivo são os 4 primeiros dígitos do seu CPF. Esta é uma mensagem automática, em caso de dúvidas contate o RH. Por favor, confirme o recebimento com um 👍'
  );
  const [messageTemplate2, setMessageTemplate2] = useState(
    'Prezado(a) {nome}, está disponível seu holerite de {mes_anterior}. Para abrir o documento, utilize os 4 primeiros dígitos do seu CPF como senha. Qualquer dúvida, entre em contato com o Recursos Humanos. Responda "OK" quando visualizar! 📄'
  );
  const [messageTemplate3, setMessageTemplate3] = useState(
    'Oi {nome}! Seu holerite referente ao período de {mes_anterior} já está disponível. A senha de acesso é composta pelos 4 primeiros números do seu CPF. Em caso de dúvidas, procure o setor de RH. Confirme o recebimento respondendo "Recebi" ✅'
  );
  const [messageTemplate4, setMessageTemplate4] = useState(
    'Olá {nome}, encaminhamos o holerite do mês {mes_anterior}. Utilize os 4 primeiros dígitos do CPF para acessar o arquivo. Caso tenha alguma dúvida, favor contatar o departamento de RH. Aguardamos sua confirmação de recebimento! 📩'
  );
  const [messageTemplate5, setMessageTemplate5] = useState(
    'Bom dia {nome}! Segue em anexo seu contracheque referente a {mes_anterior}. Para acessar, use os 4 primeiros dígitos do CPF como senha. Qualquer questão, estamos à disposição no RH. Por gentileza, reaja com ❤️ ao receber'
  );
  const [messageTemplate6, setMessageTemplate6] = useState(
    'Oi {nome}, tudo bem? Seu holerite de {mes_anterior} já foi processado e está anexo nesta mensagem. Senha: 4 primeiros números do CPF. Dúvidas? Fale com o RH! Manda um "Valeu!" pra confirmar que recebeu 😊'
  );
  const [messageTemplate7, setMessageTemplate7] = useState(
    'Prezado(a) {nome}, encaminhamos o comprovante de pagamento de {mes_anterior}. O arquivo está protegido com os 4 primeiros dígitos do seu CPF. Para esclarecimentos, procure o departamento pessoal. Confirme o recebimento com 👍 ou "Recebido"'
  );
  const [messageTemplate8, setMessageTemplate8] = useState(
    'Olá {nome}! Disponibilizamos seu holerite do período {mes_anterior}. A senha de acesso corresponde aos 4 primeiros números do CPF cadastrado. Em caso de necessidade, contate o RH. Reaja com ✅ para confirmar que visualizou'
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
    loadActiveQueues();
    
    // Verificar se há job ativo ao carregar página
    const savedJobId = localStorage.getItem('activeJobId');
    if (savedJobId) {
      setActiveJobId(savedJobId);
      // Iniciar polling
      const interval = setInterval(() => {
        pollJobStatus(savedJobId);
      }, 2000);
      setPollingInterval(interval);
      pollJobStatus(savedJobId);
    }
    
    // Polling de filas ativas a cada 5 segundos
    const queuesInterval = setInterval(loadActiveQueues, 5000);
    setQueuesPollingInterval(queuesInterval);
    
    return () => {
      if (queuesInterval) clearInterval(queuesInterval);
    };
  }, [monthFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup do polling quando componente é desmontado
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Função para fazer polling do status do job
  const pollJobStatus = async (jobId) => {
    try {
      const response = await api.get(`/payrolls/bulk-send/${jobId}/status`);
      const status = response.data;
      setJobStatus(status);

      // Se job completou ou falhou, parar polling
      if (status.status === 'completed' || status.status === 'failed') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        
        // Remover do localStorage
        localStorage.removeItem('activeJobId');
        
        // Mostrar resultado final
        if (status.status === 'completed') {
          const failedCount = status.failed_sends || 0;
          if (failedCount === 0) {
            toast.success(`✅ Todos os ${status.successful_sends} holerites foram enviados!`);
          } else {
            toast.success(`${status.successful_sends}/${status.total_files} holerites enviados`);
            if (failedCount > 0) {
              toast.error(`${failedCount} envios falharam`);
            }
          }
        } else if (status.status === 'failed') {
          toast.error(`Erro no envio: ${status.error_message}`);
        }

        // Limpar estados
        setSendingBulk(false);
        setSelectedFiles([]);
        
        // Recarregar lista após 2 segundos
        setTimeout(() => {
          loadPayrollFiles();
          setShowProgressModal(false);
        }, 2000);
      }
    } catch (error) {
      console.error('Erro ao verificar status do job:', error);
      // Não mostrar erro para não poluir a UI durante polling
    }
  };

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

  const loadActiveQueues = async () => {
    try {
      const response = await api.get('/queue/active');
      setActiveQueues(response.data.queues || []);
    } catch (error) {
      console.error('Erro ao carregar filas ativas:', error);
      // Não mostrar toast para não poluir UI durante polling
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

    // Validar que pelo menos um template foi preenchido (agora com 8 templates)
    const templates = [
      messageTemplate1, messageTemplate2, messageTemplate3, messageTemplate4,
      messageTemplate5, messageTemplate6, messageTemplate7, messageTemplate8
    ].filter(t => t && t.trim());
    
    if (templates.length === 0) {
      toast.error('Preencha pelo menos um template de mensagem');
      return;
    }

    // Aviso sobre o tempo estimado com NOVOS delays anti-softban
    const avgDelay = 150; // 2.5 minutos em média (120-180s)
    const longPauses = Math.floor(selectedFiles.length / 20); // Pausas de 12.5min a cada 20 envios
    const estimatedTime = selectedFiles.length > 1 ? 
      Math.round((selectedFiles.length - 1) * avgDelay + longPauses * 750) : 0;
    
    if (selectedFiles.length > 1) {
      const hours = Math.floor(estimatedTime / 3600);
      const minutes = Math.floor((estimatedTime % 3600) / 60);
      const timeStr = hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`;
      
      const confirmMessage = `⚠️ SISTEMA ANTI-SOFTBAN AVANÇADO ⚠️\n\n` +
        `Arquivos a enviar: ${selectedFiles.length}\n` +
        `Templates ativos: ${templates.length}\n\n` +
        `PROTEÇÕES:\n` +
        `• Delay entre envios: 2-3 minutos (aleatório)\n` +
        `• Pausa estratégica: 10-15min a cada 20 envios\n` +
        `• Monitoramento: Evolution API (pausa se offline)\n` +
        `• Variação: ${templates.length} templates randomizados\n` +
        `• Presença "digitando": 5s antes de cada envio\n\n` +
        `⏱️ Tempo estimado: ${timeStr}\n\n` +
        `O sistema pausará automaticamente se detectar problemas.\n` +
        `Você pode navegar em outras páginas durante o envio.\n\n` +
        `Deseja continuar?`;
      
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

      toast.loading('Iniciando envio em background...', { duration: 2000 });

      const response = await api.post('/payrolls/bulk-send', {
        selected_files: filesToSend,
        message_templates: templates
      });

      // Backend retorna job_id e HTTP 202
      const { job_id, total_files } = response.data;
      
      if (job_id) {
        setActiveJobId(job_id);
        setShowProgressModal(true);
        
        // Salvar no localStorage para persistir entre páginas
        localStorage.setItem('activeJobId', job_id);
        
        // Iniciar polling a cada 2 segundos
        const interval = setInterval(() => {
          pollJobStatus(job_id);
        }, 2000);
        
        setPollingInterval(interval);
        
        // Fazer primeira checagem imediatamente
        pollJobStatus(job_id);
        
        toast.success(`Envio iniciado! Processando ${total_files} arquivo(s) em background...`);
      } else {
        // Fallback para comportamento antigo (se backend não retornar job_id)
        const { success_count, total_count, failed_count } = response.data;
        
        if (failed_count === 0) {
          toast.success(`Todos os ${success_count} holerites foram enviados!`);
        } else {
          toast.success(`${success_count}/${total_count} holerites enviados`);
          if (failed_count > 0) {
            toast.error(`${failed_count} envios falharam`);
          }
        }

        setSelectedFiles([]);
        setSendingBulk(false);
        
        setTimeout(() => {
          loadPayrollFiles();
        }, 1000);
      }

    } catch (error) {
      console.error('Erro no envio em lote:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar holerites');
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

  const getItemStatusClass = (file) => {
    if (file.is_orphan) {
      return 'border-l-4 border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
    }
    if (file.can_send) {
      return 'border-l-4 border-green-400 bg-green-50 dark:bg-green-900/20';
    }
    return 'border-l-4 border-red-400 bg-red-50 dark:bg-red-900/20';
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
        
        {/* Cards de Filas Ativas de Outros Usuários */}
        {activeQueues.length > 0 && activeQueues.some(q => q.is_active) && (
          <div className="mb-6 space-y-3">
            <h3 className="text-sm font-semibold text-gray-700">⚠️ Envios em Andamento no Sistema</h3>
            {activeQueues.filter(q => q.is_active).map((queue) => (
              <div key={queue.queue_id} className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-200 rounded-lg p-4 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="animate-pulse rounded-full h-3 w-3 bg-amber-500"></div>
                    <div>
                      <h4 className="text-sm font-semibold text-amber-900">
                        {queue.description || 'Envio de Holerites'}
                      </h4>
                      <p className="text-xs text-amber-700">
                        {queue.processed_items} de {queue.total_items} enviados ({queue.progress_percentage}%)
                        {queue.user_name && ` • Iniciado por: ${queue.user_name}`}
                        {queue.computer_name && ` • PC: ${queue.computer_name}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-xs text-amber-600">
                    ✅ {queue.successful_items} • ❌ {queue.failed_items}
                  </div>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-amber-200 rounded-full h-1.5">
                    <div 
                      className="bg-amber-600 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${queue.progress_percentage}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Card de Envio Ativo (Meu Envio) */}
        {jobStatus && jobStatus.status === 'running' && !showProgressModal && (
          <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-4 shadow-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-900">📨 Envio em Andamento</h3>
                  <p className="text-sm text-blue-700">
                    {jobStatus.processed_files} de {jobStatus.total_files} holerites enviados ({jobStatus.progress_percentage}%)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowProgressModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
              >
                Ver Detalhes
              </button>
            </div>
            <div className="mt-3">
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${jobStatus.progress_percentage}%` }}
                ></div>
              </div>
              <div className="mt-2 flex justify-between text-xs text-blue-700">
                <span>✅ {jobStatus.successful_sends} enviados</span>
                {jobStatus.failed_sends > 0 && <span>❌ {jobStatus.failed_sends} falhas</span>}
                <span>⏱️ {Math.floor(jobStatus.elapsed_seconds / 60)}m {jobStatus.elapsed_seconds % 60}s</span>
              </div>
            </div>
          </div>
        )}

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
        <div className={`${config.classes.card} p-4 rounded-lg shadow mb-6 ${config.classes.border}`}>
          <h3 className={`text-lg font-medium ${config.classes.text} mb-4`}>Filtros</h3>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-64">
              <label htmlFor="monthFilter" className={`block text-sm font-medium ${config.classes.text} mb-2`}>
                Filtrar por Mês/Ano
              </label>
              <select
                id="monthFilter"
                value={monthFilter}
                onChange={(e) => setMonthFilter(e.target.value)}
                className={`block w-full rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 ${config.classes.select}`}
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

            <div className="mb-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  📝 Templates de Mensagem (o sistema sorteará entre eles para cada envio)
                </label>
                <p className="text-xs text-gray-500 mb-3">
                  Preencha 2 ou mais templates diferentes. O sistema escolherá aleatoriamente qual usar para cada colaborador.
                  <br />
                  Variáveis: {'{nome}'} (nome completo), {'{primeiro_nome}'} (só primeiro nome)
                </p>
              </div>

              <div>
                <label htmlFor="template1" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 1 ⭐ (obrigatório)
                </label>
                <textarea
                  id="template1"
                  value={messageTemplate1}
                  onChange={(e) => setMessageTemplate1(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Olá {nome}, segue seu holerite... Confirme com 👍"
                />
              </div>

              <div>
                <label htmlFor="template2" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 2 (opcional)
                </label>
                <textarea
                  id="template2"
                  value={messageTemplate2}
                  onChange={(e) => setMessageTemplate2(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Prezado(a) {nome}, está disponível seu holerite..."
                />
              </div>

              <div>
                <label htmlFor="template3" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 3 (opcional)
                </label>
                <textarea
                  id="template3"
                  value={messageTemplate3}
                  onChange={(e) => setMessageTemplate3(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Oi {nome}! Seu holerite referente ao período..."
                />
              </div>

              <div>
                <label htmlFor="template4" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 4 (opcional)
                </label>
                <textarea
                  id="template4"
                  value={messageTemplate4}
                  onChange={(e) => setMessageTemplate4(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Prezado(a) {nome}, encaminhamos o holerite... Responda 'OK'!"
                />
              </div>

              <div>
                <label htmlFor="template5" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 5 (opcional)
                </label>
                <textarea
                  id="template5"
                  value={messageTemplate5}
                  onChange={(e) => setMessageTemplate5(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Bom dia {nome}! Segue em anexo seu contracheque..."
                />
              </div>

              <div>
                <label htmlFor="template6" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 6 (opcional)
                </label>
                <textarea
                  id="template6"
                  value={messageTemplate6}
                  onChange={(e) => setMessageTemplate6(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Oi {nome}, tudo bem? Seu holerite de..."
                />
              </div>

              <div>
                <label htmlFor="template7" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 7 (opcional)
                </label>
                <textarea
                  id="template7"
                  value={messageTemplate7}
                  onChange={(e) => setMessageTemplate7(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Prezado(a) {nome}, encaminhamos o comprovante..."
                />
              </div>

              <div>
                <label htmlFor="template8" className="block text-xs font-medium text-gray-600 mb-1">
                  Template 8 (opcional)
                </label>
                <textarea
                  id="template8"
                  value={messageTemplate8}
                  onChange={(e) => setMessageTemplate8(e.target.value)}
                  rows={2}
                  className="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Ex: Oi {nome}! Disponibilizamos seu holerite... Reaja com ✅"
                />
              </div>
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
      <div className={`${config.classes.card} shadow overflow-hidden sm:rounded-md ${config.classes.border}`}>
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
              <li key={file.filename} className={`px-6 py-4 ${getItemStatusClass(file)}`}>
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
                          <h3 className={`text-sm font-medium ${config.classes.text}`}>{file.filename}</h3>
                          <div className={`mt-1 flex items-center space-x-4 text-sm ${config.classes.textSecondary}`}>
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

      {/* Modal de Progresso */}
      {showProgressModal && jobStatus && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={() => {
              if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
                setShowProgressModal(false);
              }
            }}></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <div>
                <div className="text-center">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    {jobStatus.status === 'running' ? '📨 Enviando Holerites' : 
                     jobStatus.status === 'completed' ? '✅ Envio Concluído' : 
                     '❌ Erro no Envio'}
                  </h3>
                  
                  {/* Barra de progresso */}
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>{jobStatus.processed_files} / {jobStatus.total_files} arquivos</span>
                      <span>{jobStatus.progress_percentage}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div 
                        className={`h-2.5 rounded-full transition-all duration-500 ${
                          jobStatus.status === 'completed' ? 'bg-green-500' :
                          jobStatus.status === 'failed' ? 'bg-red-500' :
                          'bg-blue-600'
                        }`}
                        style={{ width: `${jobStatus.progress_percentage}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Informações detalhadas */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center p-2 bg-green-50 rounded">
                      <span className="text-gray-700">✅ Enviados com sucesso:</span>
                      <span className="font-semibold text-green-700">{jobStatus.successful_sends}</span>
                    </div>
                    
                    {jobStatus.failed_sends > 0 && (
                      <div className="flex justify-between items-center p-2 bg-red-50 rounded">
                        <span className="text-gray-700">❌ Falhas:</span>
                        <span className="font-semibold text-red-700">{jobStatus.failed_sends}</span>
                      </div>
                    )}

                    <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span className="text-gray-700">⏱️ Tempo decorrido:</span>
                      <span className="font-semibold text-gray-700">
                        {Math.floor(jobStatus.elapsed_seconds / 60)}m {jobStatus.elapsed_seconds % 60}s
                      </span>
                    </div>

                    {jobStatus.status === 'running' && jobStatus.current_file && (
                      <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
                        <p className="text-xs text-gray-600 mb-1">Processando agora:</p>
                        <p className="text-sm font-medium text-blue-900 truncate">{jobStatus.current_file}</p>
                      </div>
                    )}

                    {jobStatus.status === 'running' && (
                      <div className="mt-3 flex items-center justify-center text-gray-500">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-2"></div>
                        <span className="text-sm">Processando em background...</span>
                      </div>
                    )}

                    {jobStatus.error_message && (
                      <div className="mt-3 p-3 bg-red-50 rounded border border-red-200">
                        <p className="text-xs text-red-600 mb-1">Erro:</p>
                        <p className="text-sm text-red-900">{jobStatus.error_message}</p>
                      </div>
                    )}

                    {jobStatus.failed_employees && jobStatus.failed_employees.length > 0 && (
                      <div className="mt-3 p-3 bg-yellow-50 rounded border border-yellow-200 max-h-40 overflow-y-auto">
                        <p className="text-xs text-yellow-700 mb-2 font-semibold">Envios que falharam:</p>
                        <ul className="text-sm space-y-1">
                          {jobStatus.failed_employees.map((emp, idx) => (
                            <li key={idx} className="text-yellow-900">
                              <span className="font-medium">{emp.employee}</span>
                              <span className="text-xs text-yellow-700"> - {emp.reason}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Botões de ação */}
                  <div className="mt-5 space-y-2">
                    {jobStatus.status === 'running' && (
                      <button
                        onClick={() => setShowProgressModal(false)}
                        className="w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:text-sm"
                      >
                        Minimizar e continuar em background
                      </button>
                    )}
                    {(jobStatus.status === 'completed' || jobStatus.status === 'failed') && (
                      <button
                        onClick={() => setShowProgressModal(false)}
                        className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:text-sm"
                      >
                        Fechar
                      </button>
                    )}
                    {jobStatus.status === 'running' && (
                      <p className="text-xs text-gray-500 text-center">
                        💡 O envio continuará mesmo se você fechar esta janela
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PayrollSender;