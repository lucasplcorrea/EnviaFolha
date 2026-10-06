import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  MapPinIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  BuildingOfficeIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';

const EMPTY_FORM = {
  name: '',
  code: '',
  company_id: '',
  address_street: '',
  address_number: '',
  address_complement: '',
  address_neighborhood: '',
  address_city: '',
  address_state: '',
  address_zip: '',
  latitude: '',
  longitude: '',
  is_active: true,
  notes: '',
};

export default function WorkLocations() {
  const { config } = useTheme();
  const { user } = useAuth();
  const [locations, setLocations] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [companyFilter, setCompanyFilter] = useState('');

  const isAdmin = user?.is_admin;

  useEffect(() => { load(); loadCompanies(); }, []);

  async function load() {
    try {
      setLoading(true);
      const res = await api.get('/work-locations?active=false');
      setLocations(res.data);
    } catch (e) {
      toast.error('Erro ao carregar locais');
    } finally {
      setLoading(false);
    }
  }

  async function loadCompanies() {
    try {
      const res = await api.get('/companies');
      setCompanies(res.data);
    } catch {}
  }

  function openNew() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(loc) {
    setEditing(loc);
    setForm({
      name: loc.name || '',
      code: loc.code || '',
      company_id: loc.company_id || '',
      address_street: loc.address_street || '',
      address_number: loc.address_number || '',
      address_complement: loc.address_complement || '',
      address_neighborhood: loc.address_neighborhood || '',
      address_city: loc.address_city || '',
      address_state: loc.address_state || '',
      address_zip: loc.address_zip || '',
      latitude: loc.latitude || '',
      longitude: loc.longitude || '',
      is_active: loc.is_active ?? true,
      notes: loc.notes || '',
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
    if (!form.name.trim()) {
      toast.error('Nome da obra/local é obrigatório');
      return;
    }
    const payload = {
      ...form,
      company_id: form.company_id ? parseInt(form.company_id) : null,
      latitude: form.latitude !== '' ? parseFloat(form.latitude) : null,
      longitude: form.longitude !== '' ? parseFloat(form.longitude) : null,
    };
    setSaving(true);
    try {
      if (editing) {
        await api.put(`/work-locations/${editing.id}`, payload);
        toast.success('Local atualizado com sucesso!');
      } else {
        await api.post('/work-locations', payload);
        toast.success('Local criado com sucesso!');
      }
      closeForm();
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erro ao salvar local');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(loc) {
    if (!window.confirm(`Desativar o local "${loc.name}"?`)) return;
    try {
      await api.delete(`/work-locations/${loc.id}`);
      toast.success('Local desativado');
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Erro ao desativar local');
    }
  }

  const tf = (label, key, type = 'text', placeholder = '', extra = {}) => (
    <div>
      <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`}
        {...extra}
      />
    </div>
  );

  const filteredLocations = companyFilter
    ? locations.filter(l => String(l.company_id) === companyFilter)
    : locations;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl">
            <MapPinIcon className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className={`text-2xl font-bold ${config.classes.text}`}>Locais de Trabalho</h1>
            <p className={`text-sm ${config.classes.textSecondary}`}>
              Obras, canteiros e unidades de alocação de colaboradores
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Filtro por empresa */}
          {companies.length > 0 && (
            <select
              value={companyFilter}
              onChange={e => setCompanyFilter(e.target.value)}
              className={`px-3 py-2 text-sm rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} focus:outline-none focus:ring-2 focus:ring-blue-500`}
            >
              <option value="">Todas as empresas</option>
              {companies.map(c => (
                <option key={c.id} value={String(c.id)}>{c.name} ({c.payroll_prefix})</option>
              ))}
            </select>
          )}
          {isAdmin && (
            <button
              onClick={openNew}
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Novo Local
            </button>
          )}
        </div>
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className={`w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl ${config.classes.card} ${config.classes.border} border`}>
            <div className={`flex items-center justify-between p-6 border-b ${config.classes.border} sticky top-0 ${config.classes.card} z-10`}>
              <h2 className={`text-lg font-bold ${config.classes.text}`}>
                {editing ? 'Editar Local de Trabalho' : 'Novo Local de Trabalho'}
              </h2>
              <button onClick={closeForm} className="text-gray-400 hover:text-gray-600 transition-colors">
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              {/* Identificação */}
              <div>
                <h3 className={`text-sm font-semibold ${config.classes.textSecondary} uppercase tracking-wider mb-3`}>
                  Identificação
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="sm:col-span-2">{tf('Nome da Obra / Local *', 'name', 'text', 'Ex: Residencial Primavera')}</div>
                  {tf('Código Interno', 'code', 'text', 'Ex: OB-2025-001')}
                </div>
                <div className="mt-4">
                  <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Empresa Responsável</label>
                  <select
                    value={form.company_id}
                    onChange={e => setForm({ ...form, company_id: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`}
                  >
                    <option value="">Selecione uma empresa...</option>
                    {companies.map(c => (
                      <option key={c.id} value={c.id}>{c.name} — Prefixo {c.payroll_prefix}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Endereço */}
              <div>
                <h3 className={`text-sm font-semibold ${config.classes.textSecondary} uppercase tracking-wider mb-3`}>
                  Endereço
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="sm:col-span-3">{tf('Logradouro', 'address_street', 'text', 'Rua, Avenida...')}</div>
                  {tf('Número', 'address_number', 'text', 'S/N')}
                  {tf('Complemento', 'address_complement', 'text', 'Bloco, Sala...')}
                  {tf('Bairro', 'address_neighborhood')}
                  <div className="sm:col-span-2">{tf('Cidade', 'address_city')}</div>
                  {tf('UF', 'address_state', 'text', 'PR', { maxLength: 2 })}
                  {tf('CEP', 'address_zip', 'text', '85500-000')}
                </div>
              </div>

              {/* Geolocalização */}
              <div>
                <h3 className={`text-sm font-semibold ${config.classes.textSecondary} uppercase tracking-wider mb-3`}>
                  Geolocalização <span className="text-xs normal-case font-normal">(para mapa interativo)</span>
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {tf('Latitude', 'latitude', 'number', '-25.4284')}
                  {tf('Longitude', 'longitude', 'number', '-49.2733')}
                </div>
                <p className={`text-xs ${config.classes.textSecondary} mt-1.5`}>
                  💡 Você pode obter as coordenadas clicando com o botão direito em qualquer ponto no Google Maps.
                </p>
              </div>

              {/* Observações e status */}
              <div>
                <label className={`block text-sm font-medium ${config.classes.text} mb-1`}>Observações</label>
                <textarea
                  value={form.notes}
                  onChange={e => setForm({ ...form, notes: e.target.value })}
                  rows={3}
                  placeholder="Notas sobre esta obra ou local..."
                  className={`w-full px-3 py-2 rounded-lg border ${config.classes.border} bg-white dark:bg-gray-800 ${config.classes.text} text-sm focus:outline-none focus:ring-2 focus:ring-blue-500`}
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="loc_active"
                  checked={form.is_active}
                  onChange={e => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label htmlFor="loc_active" className={`text-sm ${config.classes.text}`}>Local ativo</label>
              </div>

              <div className={`flex justify-end gap-3 pt-4 border-t ${config.classes.border}`}>
                <button type="button" onClick={closeForm}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                  Cancelar
                </button>
                <button type="submit" disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors">
                  {saving ? 'Salvando...' : editing ? 'Atualizar' : 'Criar Local'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grid de cards */}
      {loading ? (
        <div className="flex items-center justify-center p-16"><div className="spinner" /></div>
      ) : filteredLocations.length === 0 ? (
        <div className={`${config.classes.card} rounded-2xl border ${config.classes.border} p-16 text-center`}>
          <MapPinIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className={`text-lg font-medium ${config.classes.text}`}>Nenhum local cadastrado</p>
          <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
            {companyFilter ? 'Nenhum local para esta empresa.' : 'Clique em "Novo Local" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredLocations.map(loc => (
            <div key={loc.id}
              className={`${config.classes.card} rounded-2xl border ${config.classes.border} p-5 flex flex-col gap-3 hover:shadow-md transition-shadow`}>
              {/* Card header */}
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    {loc.is_active ? (
                      <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
                    ) : (
                      <ExclamationCircleIcon className="h-4 w-4 text-red-400 flex-shrink-0" />
                    )}
                    <h3 className={`font-semibold text-sm ${config.classes.text} truncate`}>{loc.name}</h3>
                  </div>
                  {loc.code && (
                    <span className="text-xs font-mono text-gray-400 dark:text-gray-500">{loc.code}</span>
                  )}
                </div>
                {isAdmin && (
                  <div className="flex gap-1 ml-2 flex-shrink-0">
                    <button onClick={() => openEdit(loc)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors">
                      <PencilIcon className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={() => handleDelete(loc)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors">
                      <TrashIcon className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Empresa e colaboradores */}
              <div className="flex items-center gap-3">
                {loc.company_name && (
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                    <BuildingOfficeIcon className="h-3 w-3" />
                    {loc.company_name}
                  </span>
                )}
                <span className={`inline-flex items-center gap-1 text-xs ${config.classes.textSecondary}`}>
                  <UsersIcon className="h-3 w-3" />
                  {loc.employees_count ?? 0} colaboradores
                </span>
              </div>

              {/* Endereço */}
              {(loc.address_street || loc.address_city) && (
                <div className={`text-xs ${config.classes.textSecondary} leading-relaxed`}>
                  <MapPinIcon className="h-3 w-3 inline mr-1 text-gray-400" />
                  {[loc.address_street, loc.address_number, loc.address_city, loc.address_state]
                    .filter(Boolean).join(', ')}
                </div>
              )}

              {/* Coords */}
              {loc.latitude && loc.longitude && (
                <a
                  href={`https://www.google.com/maps?q=${loc.latitude},${loc.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-500 hover:text-blue-700 hover:underline"
                >
                  {loc.latitude.toFixed(5)}, {loc.longitude.toFixed(5)} → ver no mapa
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
