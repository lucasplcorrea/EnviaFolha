import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  UserCircleIcon, 
  ClockIcon, 

  CalendarIcon,
  BriefcaseIcon,
  CurrencyDollarIcon,
  HeartIcon,
  ArrowLeftIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
  PhoneIcon,
  EnvelopeIcon,
  BuildingOfficeIcon,
  IdentificationIcon,
  CakeIcon,
  UserIcon,
  MapPinIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  ClipboardDocumentListIcon,
  ArrowTrendingUpIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

const EmployeeDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { config } = useTheme();
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');
  const [editingStatus, setEditingStatus] = useState(false);
  const [editingInfo, setEditingInfo] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [workLocations, setWorkLocations] = useState([]);
  
  // Lógica de Navegação
  const [allEmployees, setAllEmployees] = useState([]);
  const listIds = location.state?.fromList || [];
  const currentIndex = listIds.indexOf(parseInt(id));
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < listIds.length - 1;

  const goToPrev = () => {
    if (hasPrev) navigate(`/employees/${listIds[currentIndex - 1]}`, { state: location.state });
  };
  
  const goToNext = () => {
    if (hasNext) navigate(`/employees/${listIds[currentIndex + 1]}`, { state: location.state });
  };
  
  // Estados para Afastamentos
  const [leaves, setLeaves] = useState([]);
  const [loadingLeaves, setLoadingLeaves] = useState(false);
  const [showLeaveForm, setShowLeaveForm] = useState(false);
  
  // Estados para Movimentações
  const [movements, setMovements] = useState([]);
  const [loadingMovements, setLoadingMovements] = useState(false);
  const [payrollRecords, setPayrollRecords] = useState([]);
  const [payrollSummary, setPayrollSummary] = useState(null);
  const [loadingPayroll, setLoadingPayroll] = useState(false);
  const [benefitRecords, setBenefitRecords] = useState([]);
  const [benefitsSummary, setBenefitsSummary] = useState(null);
  const [loadingBenefits, setLoadingBenefits] = useState(false);
  const [timecardRecords, setTimecardRecords] = useState([]);
  const [timecardSummary, setTimecardSummary] = useState(null);
  const [loadingTimecard, setLoadingTimecard] = useState(false);
  const [loadingEvolution, setLoadingEvolution] = useState(false);
  const [editingLeave, setEditingLeave] = useState(null);
  const [leaveForm, setLeaveForm] = useState({
    leave_type: '',
    start_date: '',
    end_date: '',
    days: '',
    notes: ''
  });
  
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
    contract_type: '',
    company_id: '',
    work_location_id: '',
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
        contract_type: response.data.contract_type || '',
        company_id: response.data.company_id || '',
        work_location_id: response.data.work_location_id || '',
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
    loadEmployee();
    // Carregar empresas e locais para os dropdowns
    api.get('/companies').then(r => setCompanies(r.data || [])).catch(() => {});
    api.get('/work-locations?active=false').then(r => setWorkLocations(r.data || [])).catch(() => {});
    api.get('/employees?status=all').then(res => setAllEmployees(res.data.employees || [])).catch(() => {});
  }, [id, loadEmployee]);

  useEffect(() => {
    if (activeTab === 'leaves') {
      loadLeaves();
    } else if (activeTab === 'movements') {
      loadMovements();
    } else if (activeTab === 'evolution') {
      loadEvolution();
    } else if (activeTab === 'payroll') {
      loadPayroll();
    } else if (activeTab === 'benefits') {
      loadBenefits();
    } else if (activeTab === 'timesheet') {
      loadTimecard();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const loadMovements = async () => {
    setLoadingMovements(true);
    try {
      const response = await api.get(`/employees/${id}/movements`);
      setMovements(response.data.movements || []);
    } catch (error) {
      console.error('Erro ao carregar movimentações:', error);
      toast.error('Erro ao carregar movimentações');
      setMovements([]);
    } finally {
      setLoadingMovements(false);
    }
  };

  const loadLeaves = async () => {
    setLoadingLeaves(true);
    try {
      const response = await api.get(`/employees/${id}/leaves`);
      setLeaves(response.data || []);
    } catch (error) {
      console.error('Erro ao carregar afastamentos:', error);
      if (error.response?.status !== 404) {
        toast.error('Erro ao carregar afastamentos');
      }
      setLeaves([]);
    } finally {
      setLoadingLeaves(false);
    }
  };

  const loadPayroll = async () => {
    setLoadingPayroll(true);
    try {
      const response = await api.get(`/employees/${id}/payroll?limit=24`);
      setPayrollRecords(response.data.payrolls || []);
      setPayrollSummary(response.data.summary || null);
    } catch (error) {
      console.error('Erro ao carregar folha do colaborador:', error);
      if (error.response?.status !== 404) {
        toast.error('Erro ao carregar folha de pagamento');
      }
      setPayrollRecords([]);
      setPayrollSummary(null);
    } finally {
      setLoadingPayroll(false);
    }
  };

  const loadBenefits = async () => {
    setLoadingBenefits(true);
    try {
      const response = await api.get(`/employees/${id}/benefits?limit=24`);
      setBenefitRecords(response.data.benefits || []);
      setBenefitsSummary(response.data.summary || null);
    } catch (error) {
      console.error('Erro ao carregar benefícios do colaborador:', error);
      if (error.response?.status !== 404) {
        toast.error('Erro ao carregar benefícios');
      }
      setBenefitRecords([]);
      setBenefitsSummary(null);
    } finally {
      setLoadingBenefits(false);
    }
  };

  const loadTimecard = async () => {
    setLoadingTimecard(true);
    try {
      const response = await api.get(`/employees/${id}/timecard?limit=24`);
      setTimecardRecords(response.data.timecards || []);
      setTimecardSummary(response.data.summary || null);
    } catch (error) {
      console.error('Erro ao carregar cartão ponto do colaborador:', error);
      if (error.response?.status !== 404) {
        toast.error('Erro ao carregar cartão ponto');
      }
      setTimecardRecords([]);
      setTimecardSummary(null);
    } finally {
      setLoadingTimecard(false);
    }
  };

  const loadEvolution = async () => {
    setLoadingEvolution(true);
    try {
      const [movementsRes, payrollRes, benefitsRes] = await Promise.allSettled([
        api.get(`/employees/${id}/movements`),
        api.get(`/employees/${id}/payroll?limit=24`),
        api.get(`/employees/${id}/benefits?limit=24`)
      ]);

      if (movementsRes.status === 'fulfilled') {
        setMovements(movementsRes.value.data.movements || []);
      } else {
        console.error('Erro ao carregar movimentos para evolução:', movementsRes.reason);
      }

      if (payrollRes.status === 'fulfilled') {
        setPayrollRecords(payrollRes.value.data.payrolls || []);
        setPayrollSummary(payrollRes.value.data.summary || null);
      } else {
        console.error('Erro ao carregar folha para evolução:', payrollRes.reason);
      }

      if (benefitsRes.status === 'fulfilled') {
        setBenefitRecords(benefitsRes.value.data.benefits || []);
        setBenefitsSummary(benefitsRes.value.data.summary || null);
      } else {
        console.error('Erro ao carregar benefícios para evolução:', benefitsRes.reason);
      }
    } catch (error) {
      console.error('Erro ao carregar evolução profissional:', error);
      toast.error('Erro ao carregar evolução profissional');
    } finally {
      setLoadingEvolution(false);
    }
  };

  const handleLeaveSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingLeave) {
        await api.put(`/employees/${id}/leaves/${editingLeave.id}`, leaveForm);
        toast.success('Afastamento atualizado com sucesso!');
      } else {
        await api.post(`/employees/${id}/leaves`, leaveForm);
        toast.success('Afastamento registrado com sucesso!');
      }
      setShowLeaveForm(false);
      setEditingLeave(null);
      setLeaveForm({ leave_type: '', start_date: '', end_date: '', days: '', notes: '' });
      loadLeaves();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar afastamento');
    }
  };

  const handleDeleteLeave = async (leaveId) => {
    if (!window.confirm('Tem certeza que deseja excluir este afastamento?')) return;
    
    try {
      await api.delete(`/employees/${id}/leaves/${leaveId}`);
      toast.success('Afastamento excluído com sucesso!');
      loadLeaves();
    } catch (error) {
      toast.error('Erro ao excluir afastamento');
    }
  };

  const handleEditLeave = (leave) => {
    setEditingLeave(leave);
    setLeaveForm({
      leave_type: leave.leave_type || '',
      start_date: leave.start_date || '',
      end_date: leave.end_date || '',
      days: leave.days || '',
      notes: leave.notes || ''
    });
    setShowLeaveForm(true);
  };

  const calculateDays = (startDate, endDate) => {
    if (!startDate || !endDate) return '';
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end - start);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 para incluir ambos os dias
    return diffDays;
  };

  useEffect(() => {
    if (leaveForm.start_date && leaveForm.end_date) {
      const days = calculateDays(leaveForm.start_date, leaveForm.end_date);
      setLeaveForm(prev => ({ ...prev, days: days.toString() }));
    }
  }, [leaveForm.start_date, leaveForm.end_date]);

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

  const formatCurrency = (value) => {
    const num = Number(value || 0);
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formatMonthYear = (year, month) => {
    if (!year || !month) return '-';
    const monthNames = [
      'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];
    return `${monthNames[month - 1] || month}/${year}`;
  };

  const formatHours = (value) => {
    const num = Number(value || 0);
    return `${num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}h`;
  };

  const timecardTimeline = useMemo(() => {
    const grouped = new Map();

    timecardRecords.forEach((item) => {
      const periodKey = item.period?.id ?? `${item.period?.year || ''}-${item.period?.month || ''}`;
      const current = grouped.get(periodKey) || {
        period: item.period,
        employee_number: item.employee_number || null,
        company: item.company || null,
        normal_hours: 0,
        overtime_50: 0,
        overtime_100: 0,
        night_overtime_50: 0,
        night_overtime_100: 0,
        night_hours: 0,
        absences: 0,
        dsr_debit: 0,
        bonus_hours: 0,
        total_overtime: 0,
        total_night: 0,
        records: 0,
        upload_filename: item.upload_filename,
      };

      current.normal_hours += Number(item.normal_hours || 0);
      current.overtime_50 += Number(item.overtime_50 || 0);
      current.overtime_100 += Number(item.overtime_100 || 0);
      current.night_overtime_50 += Number(item.night_overtime_50 || 0);
      current.night_overtime_100 += Number(item.night_overtime_100 || 0);
      current.night_hours += Number(item.night_hours || 0);
      current.absences += Number(item.absences || 0);
      current.dsr_debit += Number(item.dsr_debit || 0);
      current.bonus_hours += Number(item.bonus_hours || 0);
      current.total_overtime += Number(item.total_overtime || 0);
      current.total_night += Number(item.total_night || 0);
      current.records += 1;
      current.upload_filename = item.upload_filename || current.upload_filename;
      current.employee_number = current.employee_number || item.employee_number || null;
      current.company = current.company || item.company || null;

      grouped.set(periodKey, current);
    });

    return Array.from(grouped.values()).sort((a, b) => {
      const yearA = a.period?.year || 0;
      const yearB = b.period?.year || 0;
      if (yearA !== yearB) return yearB - yearA;
      const monthA = a.period?.month || 0;
      const monthB = b.period?.month || 0;
      return monthB - monthA;
    });
  }, [timecardRecords]);

  const benefitTimeline = useMemo(() => {
    const grouped = new Map();

    benefitRecords.forEach((item) => {
      const periodKey = item.period?.id ?? `${item.period?.year || ''}-${item.period?.month || ''}-${item.period?.company || ''}`;
      const current = grouped.get(periodKey) || {
        period: item.period,
        refeicao: 0,
        alimentacao: 0,
        mobilidade: 0,
        livre: 0,
        total: 0,
      };

      const refeicao = Number(item.refeicao || 0);
      const alimentacao = Number(item.alimentacao || 0);
      const mobilidade = Number(item.mobilidade || 0);
      const livre = Number(item.livre || 0);
      const total = refeicao + alimentacao + mobilidade + livre;

      current.refeicao += refeicao;
      current.alimentacao += alimentacao;
      current.mobilidade += mobilidade;
      current.livre += livre;
      current.total += total;

      grouped.set(periodKey, current);
    });

    return Array.from(grouped.values()).sort((a, b) => {
      const yearA = a.period?.year || 0;
      const yearB = b.period?.year || 0;
      if (yearA !== yearB) return yearB - yearA;
      const monthA = a.period?.month || 0;
      const monthB = b.period?.month || 0;
      if (monthA !== monthB) return monthB - monthA;
      return String(a.period?.company || '').localeCompare(String(b.period?.company || ''));
    });
  }, [benefitRecords]);

  const benefitsSnapshot = useMemo(() => {
    const latest = benefitTimeline[0] || null;
    const highest = benefitTimeline.reduce((acc, item) => {
      if (!acc || item.total > acc.total) return item;
      return acc;
    }, null);

    return {
      latest,
      highest,
      totalPeriods: benefitTimeline.length,
      totalValue: benefitTimeline.reduce((sum, item) => sum + item.total, 0),
    };
  }, [benefitTimeline]);

  const payrollTimeline = useMemo(() => {
    const grouped = new Map();

    payrollRecords.forEach((item) => {
      const periodKey = item.period?.id ?? `${item.period?.year || ''}-${item.period?.month || ''}-${item.period?.company || ''}`;
      const current = grouped.get(periodKey);
      const snapshot = {
        period: item.period,
        gross_salary: Number(item.gross_salary || 0),
        net_salary: Number(item.net_salary || 0),
        upload_date: item.upload_date || item.updated_at || null,
        id: item.id,
      };

      if (!current || snapshot.id > current.id) {
        grouped.set(periodKey, snapshot);
      }
    });

    return Array.from(grouped.values()).sort((a, b) => {
      const yearA = a.period?.year || 0;
      const yearB = b.period?.year || 0;
      if (yearA !== yearB) return yearB - yearA;
      const monthA = a.period?.month || 0;
      const monthB = b.period?.month || 0;
      return monthB - monthA;
    });
  }, [payrollRecords]);

  const evolutionEvents = useMemo(() => {
    const events = [];

    if (employee?.admission_date) {
      events.push({
        type: 'admission',
        date: employee.admission_date,
        title: 'Admissão',
        subtitle: employee.position || 'Cargo inicial não informado',
        description: `${employee.department || 'Sem departamento'} · ${employee.company_code || 'Empresa não informada'}`,
      });
    }

    if (employee?.termination_date) {
      events.push({
        type: 'termination',
        date: employee.termination_date,
        title: 'Desligamento',
        subtitle: employee.employment_status || 'Desligado',
        description: employee.status_reason || 'Sem justificativa registrada',
      });
    }

    movements.forEach((movement) => {
      const changes = [];
      if (movement.previous_department !== movement.new_department) {
        changes.push(`Depto: ${movement.previous_department || '-'} → ${movement.new_department || '-'}`);
      }
      if (movement.previous_position !== movement.new_position) {
        changes.push(`Cargo: ${movement.previous_position || '-'} → ${movement.new_position || '-'}`);
      }
      if (movement.previous_work_location_id !== movement.new_work_location_id) {
        changes.push('Local de trabalho alterado');
      }

      events.push({
        type: 'movement',
        date: movement.date,
        title: movement.movement_type || 'Movimentação',
        subtitle: movement.reason || 'Atualização cadastral',
        description: changes.length > 0 ? changes.join(' · ') : 'Sem detalhes adicionais',
      });
    });

    payrollTimeline.forEach((snapshot) => {
      events.push({
        type: 'payroll',
        date: snapshot.period ? `${snapshot.period.year}-${String(snapshot.period.month).padStart(2, '0')}-01` : snapshot.upload_date,
        title: 'Folha de pagamento',
        subtitle: `${formatMonthYear(snapshot.period?.year, snapshot.period?.month)} · ${snapshot.period?.company || '-'}`,
        description: `Bruto ${formatCurrency(snapshot.gross_salary)} · Líquido ${formatCurrency(snapshot.net_salary)}`,
      });
    });

    benefitTimeline.forEach((snapshot) => {
      events.push({
        type: 'benefits',
        date: snapshot.period ? `${snapshot.period.year}-${String(snapshot.period.month).padStart(2, '0')}-01` : null,
        title: 'Benefícios iFood',
        subtitle: `${formatMonthYear(snapshot.period?.year, snapshot.period?.month)} · ${snapshot.period?.company || '-'}`,
        description: `Refeição ${formatCurrency(snapshot.refeicao)} · Mobilidade ${formatCurrency(snapshot.mobilidade)} · Total ${formatCurrency(snapshot.total)}`,
      });
    });

    return events
      .filter(event => event.date)
      .sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [benefitTimeline, employee, movements, payrollTimeline]);

  const evolutionStats = useMemo(() => {
    const today = new Date();
    const admission = employee?.admission_date ? new Date(employee.admission_date) : null;
    const endDate = employee?.termination_date ? new Date(employee.termination_date) : today;
    const tenureDays = admission ? Math.max(0, Math.ceil((endDate - admission) / (1000 * 60 * 60 * 24))) : 0;
    const tenureYears = tenureDays / 365.25;

    const distinctPositions = new Set([
      employee?.position,
      ...movements.flatMap((movement) => [movement.previous_position, movement.new_position])
    ].filter(Boolean));

    const distinctDepartments = new Set([
      employee?.department,
      ...movements.flatMap((movement) => [movement.previous_department, movement.new_department])
    ].filter(Boolean));

    const latestPayroll = payrollTimeline[0] || null;
    const latestBenefit = benefitTimeline[0] || null;
    const latestMovement = movements[0] || null;

    return {
      tenureDays,
      tenureYears,
      distinctPositions: distinctPositions.size,
      distinctDepartments: distinctDepartments.size,
      latestPayroll,
      latestBenefit,
      latestMovement,
      totalMovements: movements.length,
    };
  }, [benefitTimeline, employee, movements, payrollTimeline]);

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
    <div className="max-w-7xl mx-auto pb-10">
      {/* Header Estilo Banner Moderno */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-3 sm:space-y-0 mb-4">
          <button
            onClick={() => navigate('/employees')}
            className="inline-flex items-center text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm hover:shadow hover:border-blue-300"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2 text-blue-500" />
            Voltar para a Lista
          </button>
          
          {listIds.length > 0 && (
            <div className="flex items-center space-x-1.5 bg-white p-1 rounded-lg border border-gray-200 shadow-sm">
              <button 
                onClick={goToPrev}
                disabled={!hasPrev}
                className={`p-1.5 rounded-md flex items-center transition-colors ${hasPrev ? 'text-gray-700 hover:bg-gray-100 hover:text-blue-600' : 'text-gray-300 cursor-not-allowed'}`}
                title="Colaborador Anterior"
              >
                <ChevronLeftIcon className="w-5 h-5" />
              </button>
              
              <div className="relative group">
                <select
                  value={id}
                  onChange={(e) => navigate(`/employees/${e.target.value}`, { state: location.state })}
                  className="appearance-none bg-gray-50 border border-gray-200 text-gray-700 sm:text-sm rounded-md focus:ring-blue-500 focus:border-blue-500 block w-56 md:w-64 p-1.5 pr-8 hover:bg-white transition-colors truncate font-medium cursor-pointer"
                  title="Pesquisar/Pular para Colaborador"
                >
                  {allEmployees.length > 0 ? (
                    allEmployees.filter(e => listIds.includes(e.id)).map(e => (
                      <option key={e.id} value={e.id}>{e.full_name}</option>
                    ))
                  ) : (
                    <option value={id}>{employee.full_name}</option>
                  )}
                  {/* Fallback no caso de ID ativo não estar carregado ainda no list */}
                  {allEmployees.length > 0 && !allEmployees.find(e => String(e.id) === String(id)) && (
                    <option value={id}>{employee.full_name}</option>
                  )}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400 group-hover:text-blue-500">
                  <MagnifyingGlassIcon className="h-4 w-4" />
                </div>
              </div>

              <button 
                onClick={goToNext}
                disabled={!hasNext}
                className={`p-1.5 rounded-md flex items-center transition-colors ${hasNext ? 'text-gray-700 hover:bg-gray-100 hover:text-blue-600' : 'text-gray-300 cursor-not-allowed'}`}
                title="Próximo Colaborador"
              >
                <ChevronRightIcon className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>
        
        <div className="bg-white shadow-sm border border-gray-200 rounded-xl overflow-hidden relative">
          {/* abstract background banner */}
          <div className="h-32 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-800"></div>
          
          <div className="px-6 pb-6 pt-0 sm:flex sm:items-end sm:justify-between -mt-12 relative z-10">
            <div className="sm:flex sm:space-x-5 items-end">
              <div className="relative group">
                <div className="h-28 w-28 rounded-full border-4 border-white bg-white flex items-center justify-center text-4xl font-bold text-blue-600 shadow-md overflow-hidden">
                  {employee.full_name?.charAt(0) || 'C'}
                </div>
                <span className={`absolute bottom-2 right-2 h-5 w-5 rounded-full border-2 border-white ${employee.is_active ? 'bg-green-500' : 'bg-red-500'}`} title={employee.is_active ? 'Ativo' : 'Inativo'}></span>
              </div>
              <div className="mt-4 sm:flex-1 sm:min-w-0 sm:flex sm:items-center sm:justify-end sm:space-x-6 sm:pb-3">
                <div className="mt-6 sm:mt-0 sm:min-w-0 flex-1">
                  <h1 className="text-3xl font-bold text-gray-900 truncate">
                    {employee.full_name}
                  </h1>
                  <div className="flex flex-col sm:flex-row sm:flex-wrap sm:space-x-6 mt-1">
                    <div className="mt-2 flex items-center text-sm text-gray-500 font-medium">
                      <IdentificationIcon className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                      Matrícula: {employee.unique_id}
                    </div>
                    <div className="mt-2 flex items-center text-sm text-gray-500 font-medium">
                      <BriefcaseIcon className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                      {employee.position || 'Nenhum cargo definido'}
                    </div>
                    <div className="mt-2 flex items-center text-sm text-gray-500 font-medium">
                      <BuildingOfficeIcon className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                      {companies.find(c => c.id === employee.company_id)?.name || employee.department || 'Não alocado'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 flex flex-col justify-stretch space-y-3 sm:flex-row sm:space-y-0 sm:space-x-4 pb-2">
              <div className={`inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-semibold rounded-md shadow-sm ${employee.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                 <span className={`h-2 w-2 rounded-full mr-2 ${employee.is_active ? 'bg-green-500' : 'bg-red-500'}`}></span>
                 {employee.is_active ? 'Colaborador Ativo' : 'Desligado'}
              </div>
              
              {!editingInfo ? (
                <button
                  onClick={() => setEditingInfo(true)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                >
                  <PencilIcon className="h-4 w-4 mr-2 text-gray-400" />
                  Editar Perfil
                </button>
              ) : (
                <div className="flex space-x-2">
                  <button
                    onClick={handleInfoUpdate}
                    className="inline-flex justify-center items-center px-5 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 transition"
                  >
                    Salvar Alterações
                  </button>
                  <button
                    onClick={() => { setEditingInfo(false); loadEmployee(); }}
                    className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="border-b border-gray-200 mb-6 overflow-x-auto hide-scrollbar">
        <nav className="-mb-px flex space-x-8 pb-1 min-w-max">
          {[
            { id: 'info', label: 'Informações', icon: UserCircleIcon },
            { id: 'status', label: 'Status', icon: ClockIcon },
            { id: 'movements', label: 'Histórico de Lotações', icon: BriefcaseIcon },
            { id: 'leaves', label: 'Afastamentos', icon: CalendarIcon },
            { id: 'evolution', label: 'Evolução Profissional', icon: ArrowTrendingUpIcon },
            { id: 'payroll', label: 'Folha de Pagto', icon: CurrencyDollarIcon },
            { id: 'benefits', label: 'Benefícios', icon: HeartIcon },
            { id: 'timesheet', label: 'Cartão Ponto', icon: ClipboardDocumentListIcon }
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
        
        {/* Informações Básicas - Layout melhorado em cards */}
        {activeTab === 'info' && !editingInfo && (
          <div className="space-y-6">
            {/* Card de Informações Pessoais */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
              <div className="flex items-center mb-4">
                <UserIcon className="h-6 w-6 text-blue-600 mr-2" />
                <h3 className="text-lg font-semibold text-gray-900">Informações Pessoais</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">CPF</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.cpf || 'Não informado'}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <CakeIcon className="h-4 w-4 mr-1" />
                    Data de Nascimento
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">{formatDate(employee.birth_date)}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">Sexo</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.sex || 'Não informado'}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">Estado Civil</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.marital_status || 'Não informado'}</dd>
                </div>
              </div>
            </div>

            {/* Card de Contato */}
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-6 border border-green-100">
              <div className="flex items-center mb-4">
                <PhoneIcon className="h-6 w-6 text-green-600 mr-2" />
                <h3 className="text-lg font-semibold text-gray-900">Informações de Contato</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <PhoneIcon className="h-4 w-4 mr-1" />
                    Telefone
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">
                    {employee.phone_number || 'Não informado'}
                  </dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <EnvelopeIcon className="h-4 w-4 mr-1" />
                    Email
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">
                    {employee.email || 'Não informado'}
                  </dd>
                </div>
              </div>
            </div>

            {/* Card de Dados Profissionais */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-100">
              <div className="flex items-center mb-4">
                <BriefcaseIcon className="h-6 w-6 text-purple-600 mr-2" />
                <h3 className="text-lg font-semibold text-gray-900">Informações Profissionais</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="bg-white rounded-lg p-4 shadow-sm lg:col-span-2">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <BuildingOfficeIcon className="h-4 w-4 mr-1" />
                    Empresa
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">
                    {companies.find(c => c.id === employee.company_id)?.name || 'Não informada'}
                  </dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <MapPinIcon className="h-4 w-4 mr-1" />
                    Local de Trabalho
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">
                    {workLocations.find(l => l.id === employee.work_location_id)?.name || 'Não informado'}
                  </dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">Departamento</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.department || 'Não informado'}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">Cargo</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.position || 'Não informado'}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1 flex items-center">
                    <CalendarIcon className="h-4 w-4 mr-1" />
                    Data de Admissão
                  </dt>
                  <dd className="text-base font-semibold text-gray-900">{formatDate(employee.admission_date)}</dd>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <dt className="text-xs font-medium text-gray-500 uppercase mb-1">Tipo de Contrato</dt>
                  <dd className="text-base font-semibold text-gray-900">{employee.contract_type || 'Não informado'}</dd>
                </div>
              </div>
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
                <label className="block text-sm font-medium text-gray-700">Empresa Responsável</label>
                <select
                  value={infoForm.company_id || ''}
                  onChange={(e) => {
                    const companyId = e.target.value;
                    const company = companies.find(c => String(c.id) === companyId);
                    
                    // Se houver empresa selecionada, atualiza também a matrícula/ID Único, 
                    // preservando os 5 últimos dígitos numéricos se possível
                    let newUniqueId = infoForm.unique_id;
                    if (company && company.payroll_prefix) {
                       const prefix = company.payroll_prefix.replace(/\D/g, '').padStart(4, '0');
                       const matricula = newUniqueId.slice(-5).padStart(5, '0');
                       newUniqueId = `${prefix}${matricula}`;
                    }

                    setInfoForm({
                      ...infoForm, 
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
                  value={infoForm.work_location_id || ''}
                  onChange={(e) => setInfoForm({
                    ...infoForm, 
                    work_location_id: e.target.value ? parseInt(e.target.value) : ''
                  })}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 px-3 py-2 border"
                >
                  <option value="">Selecione...</option>
                  {workLocations
                    .filter(loc => !infoForm.company_id || loc.company_id === infoForm.company_id)
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

        {/* Tab de Afastamentos - Funcional */}
        {activeTab === 'leaves' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Histórico de Afastamentos</h3>
              {!showLeaveForm && (
                <button
                  onClick={() => {
                    setShowLeaveForm(true);
                    setEditingLeave(null);
                    setLeaveForm({ leave_type: '', start_date: '', end_date: '', days: '', notes: '' });
                  }}
                  className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 shadow-sm"
                >
                  <PlusIcon className="h-5 w-5 mr-2" />
                  Novo Afastamento
                </button>
              )}
            </div>

            {showLeaveForm && (
              <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
                <h4 className="text-md font-semibold mb-4 text-gray-900">
                  {editingLeave ? 'Editar Afastamento' : 'Registrar Novo Afastamento'}
                </h4>
                <form onSubmit={handleLeaveSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Tipo de Afastamento *
                      </label>
                      <select
                        required
                        value={leaveForm.leave_type}
                        onChange={(e) => setLeaveForm({...leaveForm, leave_type: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">Selecione...</option>
                        <option value="Férias">Férias</option>
                        <option value="Licença Médica">Licença Médica</option>
                        <option value="Licença Maternidade">Licença Maternidade</option>
                        <option value="Licença Paternidade">Licença Paternidade</option>
                        <option value="Afastamento INSS">Afastamento INSS</option>
                        <option value="Suspensão">Suspensão</option>
                        <option value="Outro">Outro</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Dias de Afastamento
                      </label>
                      <input
                        type="number"
                        value={leaveForm.days}
                        onChange={(e) => setLeaveForm({...leaveForm, days: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-gray-50"
                        placeholder="Calculado automaticamente"
                        readOnly
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Data de Início *
                      </label>
                      <input
                        type="date"
                        required
                        value={leaveForm.start_date}
                        onChange={(e) => setLeaveForm({...leaveForm, start_date: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Data de Término *
                      </label>
                      <input
                        type="date"
                        required
                        value={leaveForm.end_date}
                        onChange={(e) => setLeaveForm({...leaveForm, end_date: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Observações
                    </label>
                    <textarea
                      value={leaveForm.notes}
                      onChange={(e) => setLeaveForm({...leaveForm, notes: e.target.value})}
                      rows="3"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Adicione detalhes sobre o afastamento..."
                    />
                  </div>

                  <div className="flex justify-end space-x-3 pt-4 border-t">
                    <button
                      type="button"
                      onClick={() => {
                        setShowLeaveForm(false);
                        setEditingLeave(null);
                        setLeaveForm({ leave_type: '', start_date: '', end_date: '', days: '', notes: '' });
                      }}
                      className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 shadow-sm"
                    >
                      {editingLeave ? 'Atualizar' : 'Salvar'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {loadingLeaves ? (
              <div className="flex justify-center items-center py-12">
                <div className="spinner"></div>
              </div>
            ) : leaves.length === 0 ? (
              <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                <CalendarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhum afastamento registrado</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Comece registrando o primeiro afastamento deste colaborador.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {leaves.map((leave) => (
                  <div
                    key={leave.id}
                    className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-3">
                          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                            {leave.leave_type}
                          </span>
                          <span className="text-sm text-gray-500">
                            {leave.days} {leave.days === 1 ? 'dia' : 'dias'}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500">Início:</span>
                            <span className="ml-2 font-medium text-gray-900">{formatDate(leave.start_date)}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Término:</span>
                            <span className="ml-2 font-medium text-gray-900">{formatDate(leave.end_date)}</span>
                          </div>
                        </div>
                        {leave.notes && (
                          <div className="mt-3 text-sm text-gray-600 bg-gray-50 p-3 rounded">
                            <span className="font-medium text-gray-700">Observações: </span>
                            {leave.notes}
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleEditLeave(leave)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-md"
                          title="Editar"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDeleteLeave(leave.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-md"
                          title="Excluir"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Aba de Movimentações */}
        {activeTab === 'movements' && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Histórico de Lotações e Movimentações</h3>
            </div>
            
            {loadingMovements ? (
              <div className="p-8 text-center flex flex-col items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-gray-500">Carregando histórico...</p>
              </div>
            ) : movements.length === 0 ? (
              <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 m-6">
                <BriefcaseIcon className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                <h3 className="text-sm font-medium text-gray-900 mb-1">Nenhuma movimentação</h3>
                <p className="text-sm text-gray-500">O histórico de lotações deste colaborador está vazio.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo/Motivo</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Alteração</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {movements.map((mov) => {
                      const formatDate = (dateString) => {
                        if (!dateString) return '-';
                        const parts = dateString.split('-');
                        return `${parts[2]}/${parts[1]}/${parts[0]}`;
                      };
                      
                      const oldLoc = workLocations.find(w => w.id.toString() === String(mov.previous_work_location_id))?.name || 'Não informada';
                      const newLoc = workLocations.find(w => w.id.toString() === String(mov.new_work_location_id))?.name || 'Não informada';
                      
                      return (
                        <tr key={mov.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {formatDate(mov.date)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <span className="font-semibold text-gray-900">{mov.movement_type}</span>
                            <br/>
                            <span className="text-xs text-gray-400">{mov.reason || 'Atualização'}</span>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {(mov.previous_department !== mov.new_department) && (
                              <div className="mb-1 border-b border-gray-100 pb-1">
                                <span className="font-medium text-gray-700">Depto: </span>
                                <span className="text-gray-400 line-through">{mov.previous_department || '-'}</span>
                                <span className="text-blue-500 mx-1">➜</span>
                                <span className="text-gray-900"> {mov.new_department || '-'}</span>
                              </div>
                            )}
                            {(mov.previous_position !== mov.new_position) && (
                              <div className="mb-1 border-b border-gray-100 pb-1">
                                <span className="font-medium text-gray-700">Cargo: </span>
                                <span className="text-gray-400 line-through">{mov.previous_position || '-'}</span>
                                <span className="text-blue-500 mx-1">➜</span>
                                <span className="text-gray-900"> {mov.new_position || '-'}</span>
                              </div>
                            )}
                            {(mov.previous_work_location_id !== mov.new_work_location_id) && (
                              <div className="mb-1">
                                <span className="font-medium text-gray-700">Local: </span>
                                <span className="text-gray-400 line-through">{oldLoc}</span>
                                <span className="text-blue-500 mx-1">➜</span>
                                <span className="text-gray-900"> {newLoc}</span>
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'evolution' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-200 flex items-center justify-between bg-gray-50">
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <ArrowTrendingUpIcon className="h-5 w-5 text-indigo-600 mr-2" />
                  Evolução Profissional
                </h3>
              </div>

              {loadingEvolution ? (
                <div className="p-8 text-center flex flex-col items-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                  <p className="text-gray-500">Carregando evolução profissional...</p>
                </div>
              ) : (
                <div className="p-6 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Tempo de casa</p>
                      <p className="mt-1 text-2xl font-bold text-gray-900">{evolutionStats.tenureYears.toFixed(1)} anos</p>
                      <p className="text-xs text-gray-600 mt-1">{evolutionStats.tenureDays} dias desde a admissão</p>
                    </div>
                    <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Cargo atual</p>
                      <p className="mt-1 text-base font-bold text-gray-900">{employee.position || 'Não informado'}</p>
                      <p className="text-xs text-gray-600 mt-1">{employee.department || 'Sem departamento'}</p>
                    </div>
                    <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Último salário líquido</p>
                      <p className="mt-1 text-2xl font-bold text-gray-900">
                        {formatCurrency(evolutionStats.latestPayroll?.net_salary || 0)}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">{evolutionStats.latestPayroll?.period ? formatMonthYear(evolutionStats.latestPayroll.period.year, evolutionStats.latestPayroll.period.month) : '-'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-700">Movimentações</p>
                      <p className="mt-1 text-2xl font-bold text-gray-900">{evolutionStats.totalMovements}</p>
                      <p className="text-xs text-gray-600 mt-1">{evolutionStats.distinctPositions} cargos · {evolutionStats.distinctDepartments} lotações</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="rounded-lg border border-gray-200 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Última movimentação</p>
                      <p className="mt-1 text-base font-bold text-gray-900">{evolutionStats.latestMovement?.movement_type || 'Sem histórico'}</p>
                      <p className="text-sm text-gray-600 mt-1">{evolutionStats.latestMovement?.reason || 'Atualização cadastral'}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Últimos benefícios</p>
                      <p className="mt-1 text-base font-bold text-gray-900">
                        {evolutionStats.latestBenefit?.period ? formatMonthYear(evolutionStats.latestBenefit.period.year, evolutionStats.latestBenefit.period.month) : '-'}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">Total: {formatCurrency(evolutionStats.latestBenefit?.total || 0)}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Status atual</p>
                      <p className="mt-1 text-base font-bold text-gray-900">{employee.employment_status || 'Ativo'}</p>
                      <p className="text-sm text-gray-600 mt-1">{employee.status_reason || 'Sem observações'}</p>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-900">Linha do tempo consolidada</h4>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-white">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Data</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Marco</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Detalhes</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-100">
                          {evolutionEvents.slice(0, 18).map((event, index) => (
                            <tr key={`${event.type}-${event.date}-${index}`} className="hover:bg-gray-50 align-top">
                              <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                                {formatDate(event.date)}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-900">
                                <div className="font-semibold">{event.title}</div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">{event.type}</div>
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600">
                                <div className="font-medium text-gray-800">{event.subtitle}</div>
                                <div className="text-gray-500 mt-1 whitespace-pre-wrap">{event.description}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'payroll' && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <CurrencyDollarIcon className="h-5 w-5 text-green-600 mr-2" />
                Folha de Pagamento
              </h3>
            </div>

            {loadingPayroll ? (
              <div className="p-8 text-center flex flex-col items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mb-4"></div>
                <p className="text-gray-500">Carregando dados de folha...</p>
              </div>
            ) : payrollRecords.length === 0 ? (
              <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 m-6">
                <CurrencyDollarIcon className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                <h3 className="text-sm font-medium text-gray-900 mb-1">Nenhum registro de folha</h3>
                <p className="text-sm text-gray-500">Ainda não há registros de folha vinculados a este colaborador.</p>
              </div>
            ) : (
              <div className="p-6 space-y-5">
                {payrollSummary && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-green-50 border border-green-100 rounded-lg p-4">
                      <p className="text-xs text-green-800 font-medium uppercase">Total Bruto</p>
                      <p className="text-lg font-bold text-green-900 mt-1">{formatCurrency(payrollSummary.total_gross_salary)}</p>
                    </div>
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                      <p className="text-xs text-blue-800 font-medium uppercase">Total Líquido</p>
                      <p className="text-lg font-bold text-blue-900 mt-1">{formatCurrency(payrollSummary.total_net_salary)}</p>
                    </div>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <p className="text-xs text-gray-700 font-medium uppercase">Média Líquida</p>
                      <p className="text-lg font-bold text-gray-900 mt-1">{formatCurrency(payrollSummary.avg_net_salary)}</p>
                    </div>
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Período</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Empresa</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Bruto</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Líquido</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Arquivo</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {payrollRecords.map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.period?.name || '-'}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{item.period?.company || '-'}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.gross_salary)}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">{formatCurrency(item.net_salary)}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{item.upload_filename || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'benefits' && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <HeartIcon className="h-5 w-5 text-purple-600 mr-2" />
                Visão individual de benefícios
              </h3>
            </div>

            {loadingBenefits ? (
              <div className="p-8 text-center flex flex-col items-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-4"></div>
                <p className="text-gray-500">Carregando benefícios...</p>
              </div>
            ) : benefitRecords.length === 0 ? (
              <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 m-6">
                <HeartIcon className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                <h3 className="text-sm font-medium text-gray-900 mb-1">Nenhum benefício encontrado</h3>
                <p className="text-sm text-gray-500">Ainda não há valores de benefícios vinculados a este colaborador.</p>
              </div>
            ) : (
              <div className="p-6 space-y-5">
                {benefitsSummary && (
                  <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                    <div className="bg-purple-50 border border-purple-100 rounded-lg p-3">
                      <p className="text-xs text-purple-800 font-medium uppercase">Refeição</p>
                      <p className="text-base font-bold text-purple-900 mt-1">{formatCurrency(benefitsSummary.total_refeicao)}</p>
                    </div>
                    <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3">
                      <p className="text-xs text-indigo-800 font-medium uppercase">Alimentação</p>
                      <p className="text-base font-bold text-indigo-900 mt-1">{formatCurrency(benefitsSummary.total_alimentacao)}</p>
                    </div>
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                      <p className="text-xs text-blue-800 font-medium uppercase">Mobilidade</p>
                      <p className="text-base font-bold text-blue-900 mt-1">{formatCurrency(benefitsSummary.total_mobilidade)}</p>
                    </div>
                    <div className="bg-cyan-50 border border-cyan-100 rounded-lg p-3">
                      <p className="text-xs text-cyan-800 font-medium uppercase">Livre</p>
                      <p className="text-base font-bold text-cyan-900 mt-1">{formatCurrency(benefitsSummary.total_livre)}</p>
                    </div>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <p className="text-xs text-gray-700 font-medium uppercase">Total</p>
                      <p className="text-base font-bold text-gray-900 mt-1">{formatCurrency(benefitsSummary.total_benefits)}</p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div className="rounded-lg border border-purple-100 bg-purple-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-purple-700">Último período</p>
                    <p className="mt-1 text-sm font-bold text-gray-900">
                      {benefitsSnapshot.latest?.period?.name || '-'}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {benefitsSnapshot.latest?.period?.company || '-'}
                    </p>
                  </div>
                  <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Períodos importados</p>
                    <p className="mt-1 text-2xl font-bold text-gray-900">{benefitsSnapshot.totalPeriods}</p>
                  </div>
                  <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Maior total mensal</p>
                    <p className="mt-1 text-sm font-bold text-gray-900">
                      {benefitsSnapshot.highest?.period?.name || '-'}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {formatCurrency(benefitsSnapshot.highest?.total || 0)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-700">Acumulado exibido</p>
                    <p className="mt-1 text-lg font-bold text-gray-900">
                      {formatCurrency(benefitsSnapshot.totalValue)}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-gray-200 overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-900 flex items-center">
                      <ArrowTrendingUpIcon className="h-4 w-4 text-blue-600 mr-2" />
                      Linha do tempo resumida
                    </h4>
                    <span className="text-xs text-gray-500">período / empresa</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-white">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Período</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Empresa</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Refeição</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Mobilidade</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Livre</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-100">
                        {benefitTimeline.map((item, index) => (
                          <tr key={`${item.period?.id || index}`} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.period?.name || '-'}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">{item.period?.company || '-'}</td>
                            <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.refeicao)}</td>
                            <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.mobilidade)}</td>
                            <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.livre)}</td>
                            <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">{formatCurrency(item.total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Período</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Empresa</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Refeição</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Alimentação</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Mobilidade</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Livre</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {benefitRecords.map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.period?.name || '-'}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{item.period?.company || '-'}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.refeicao)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.alimentacao)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.mobilidade)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatCurrency(item.livre)}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">{formatCurrency(item.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'timesheet' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <ClipboardDocumentListIcon className="h-5 w-5 text-blue-600 mr-2" />
                Cartão Ponto do Colaborador
              </h3>
              <p className="text-sm text-gray-500 mt-1">Dados consolidados por período importado no módulo de cartão ponto</p>
            </div>

            {loadingTimecard ? (
              <div className="px-6 py-10 text-center text-sm text-gray-500">Carregando cartão ponto...</div>
            ) : timecardTimeline.length === 0 ? (
              <div className="px-6 py-10 text-center text-sm text-gray-500">Nenhum dado de cartão ponto encontrado para este colaborador.</div>
            ) : (
              <div className="p-6 space-y-6">
                {timecardSummary && (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <p className="text-xs font-semibold uppercase text-amber-700">Horas Extras (50% + 100%)</p>
                      <p className="text-lg font-bold text-amber-900 mt-1">{formatHours(timecardSummary.total_overtime)}</p>
                    </div>
                    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
                      <p className="text-xs font-semibold uppercase text-indigo-700">Horas Noturnas Totais</p>
                      <p className="text-lg font-bold text-indigo-900 mt-1">{formatHours(timecardSummary.total_night)}</p>
                    </div>
                    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                      <p className="text-xs font-semibold uppercase text-blue-700">Média HE por Registro</p>
                      <p className="text-lg font-bold text-blue-900 mt-1">{formatHours(timecardSummary.avg_overtime)}</p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <p className="text-xs font-semibold uppercase text-gray-600">Registros Importados</p>
                      <p className="text-lg font-bold text-gray-900 mt-1">{timecardRecords.length}</p>
                    </div>
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Período</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Matrícula</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Empresa</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Normais</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">HE 50%</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">HE 100%</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Noturnas</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total HE</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total Noturno</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {timecardTimeline.map((item, index) => (
                        <tr key={`${item.period?.id || index}-${item.upload_filename || ''}`} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900 font-medium">{item.period?.name || formatMonthYear(item.period?.year, item.period?.month)}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{item.employee_number || employee?.registration_number || employee?.unique_id || '-'}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{item.company || '-'}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatHours(item.normal_hours)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatHours(item.overtime_50)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatHours(item.overtime_100)}</td>
                          <td className="px-4 py-3 text-sm text-right text-gray-700">{formatHours(item.night_hours)}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-amber-700">{formatHours(item.total_overtime)}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-indigo-700">{formatHours(item.total_night)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default EmployeeDetail;
