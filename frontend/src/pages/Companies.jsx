import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  BuildingOfficeIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const EMPTY_FORM = {
  name: '',
  trade_name: '',
  cnpj: '',
  payroll_prefix: '',
  address: '',
  phone: '',
  email: '',
  is_active: true,
  notes: '',
};

export default function Companies() {
  const { config } = useTheme();
  const { user } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const isAdmin = user?.is_admin;

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      setLoading(true);
      const res = await api.get('/companies');
      setCompanies(res.data);
    } catch (e) {
      toast.error('Erro ao carregar empresas');
    } finally {
      setLoading(false);
    }
  }

  function openNew() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(company) {
    setEditing(company);
    setForm({
      name: company.name || '',
      trade_name: company.trade_name || '',
      cnpj: company.cnpj || '',
      payroll_prefix: company.payroll_prefix || '',
      address: company.address || '',
      phone: company.phone || '',
      email: company.email || '',
      is_active: company.is_active ?? true,
      notes: company.notes || '',
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.payroll_prefix.trim()) {
      toast.error('Nome e Prefixo de Matrícula são obrigatórios');
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await api.put(`/companies/${editing.id}`, form);
        toast.success('Empresa atualizada com sucesso!');
      } else {
        await api.post('/companies', form);
        toast.success('Empresa criada com sucesso!');
      }
      closeForm();
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erro ao salvar empresa');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(company) {
    if (!window.confirm(`Desativar a empresa "${company.name}"?`)) return;
    try {
      await api.delete(`/companies/${company.id}`);
      toast.success('Empresa desativada');
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erro ao desativar empresa');
    }
  }

  const field = (label, key, type = 'text', placeholder = '') => (
    <div>
      <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} ${config.classes.input || 'bg-white'} ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`}
      />
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-xl">
            <BuildingOfficeIcon className="h-7 w-7 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className={`text-2xl font-bold ${config.classes.text}`}>Empresas</h1>
            <p className={`text-sm ${config.classes.textSecondary}`}>
              Cadastro das empresas do grupo e seus prefixos de matrícula
            </p>
          </div>
        </div>
        {isAdmin && (
          <button
            onClick={openNew}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            Nova Empresa
          </button>
        )}
      </div>

      {/* Modal de Formulário */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className={`w-full max-w-2xl rounded-2xl shadow-2xl ${config.classes.card} ${config.classes.border} border`}>
            <div className={`flex items-center justify-between p-6 border-b ${config.classes.border}`}>
              <h2 className={`text-lg font-bold ${config.classes.text}`}>
                {editing ? 'Editar Empresa' : 'Nova Empresa'}
              </h2>
              <button onClick={closeForm} className="text-gray-400 hover:text-gray-600 transition-colors">
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {field('Razão Social *', 'name', 'text', 'Ex: Infraestrutura Ltda')}
                {field('Nome Fantasia', 'trade_name', 'text', 'Ex: Construtora ABC')}
                {field('CNPJ', 'cnpj', 'text', '00.000.000/0000-00')}
                <div>
                  <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>
                    Prefixo de Matrícula *
                    <span className="ml-1 text-xs text-gray-400 font-normal">(usado no absolute_id)</span>
                  </label>
                  <input
                    type="text"
                    value={form.payroll_prefix}
                    onChange={e => setForm({ ...form, payroll_prefix: e.target.value })}
                    placeholder="Ex: 0059"
                    maxLength={10}
                    className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono`}
                  />
                </div>
                {field('Telefone', 'phone', 'tel', '(47) 3333-4444')}
                {field('E-mail', 'email', 'email', 'contato@empresa.com')}
              </div>

              {field('Endereço', 'address', 'text', 'Rua, número, cidade - UF')}

              <div>
                <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Observações</label>
                <textarea
                  value={form.notes}
                  onChange={e => setForm({ ...form, notes: e.target.value })}
                  rows={3}
                  placeholder="Notas internas sobre esta empresa..."
                  className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`}
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={e => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label htmlFor="is_active" className={`text-sm ${config.classes.text}`}>
                  Empresa ativa
                </label>
              </div>

              <div className={`flex justify-end gap-3 pt-4 border-t ${config.classes.border}`}>
                <button type="button" onClick={closeForm}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                  Cancelar
                </button>
                <button type="submit" disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors">
                  {saving ? 'Salvando...' : editing ? 'Atualizar' : 'Criar Empresa'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div className={`${config.classes.card} rounded-2xl shadow border ${config.classes.border} overflow-hidden`}>
        {loading ? (
          <div className="flex items-center justify-center p-16">
            <div className="spinner" />
          </div>
        ) : companies.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-center">
            <BuildingOfficeIcon className="h-12 w-12 text-gray-300 mb-4" />
            <p className={`text-lg font-medium ${config.classes.text}`}>Nenhuma empresa cadastrada</p>
            <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
              Clique em "Nova Empresa" para começar
            </p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className={config.classes.tableHeader || 'bg-gray-50 dark:bg-gray-800'}>
              <tr>
                {['Empresa', 'Prefixo', 'CNPJ', 'Contato', 'Colaboradores', 'Obras', 'Status', ''].map(h => (
                  <th key={h} className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${config.classes.textSecondary}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className={`divide-y ${config.classes.border}`}>
              {companies.map(c => (
                <tr key={c.id} className={`hover:${config.classes.rowHover || 'bg-gray-50 dark:bg-gray-750'} transition-colors`}>
                  <td className="px-4 py-3">
                    <div className={`font-medium text-sm ${config.classes.text}`}>{c.name}</div>
                    {c.trade_name && (
                      <div className={`text-xs ${config.classes.textSecondary}`}>{c.trade_name}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300">
                      {c.payroll_prefix}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-sm font-mono ${config.classes.textSecondary}`}>
                    {c.cnpj || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className={`text-xs ${config.classes.textSecondary}`}>{c.phone || '—'}</div>
                    <div className={`text-xs ${config.classes.textSecondary}`}>{c.email || ''}</div>
                  </td>
                  <td className={`px-4 py-3 text-sm text-center ${config.classes.text}`}>
                    {c.employees_count ?? 0}
                  </td>
                  <td className={`px-4 py-3 text-sm text-center ${config.classes.text}`}>
                    {c.work_locations_count ?? 0}
                  </td>
                  <td className="px-4 py-3">
                    {c.is_active ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                        <CheckCircleIcon className="h-3 w-3" /> Ativa
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400">
                        <ExclamationCircleIcon className="h-3 w-3" /> Inativa
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {isAdmin && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(c)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                          title="Editar"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(c)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                          title="Desativar"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
