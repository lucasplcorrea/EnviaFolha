import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  UserIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  KeyIcon
} from '@heroicons/react/24/outline';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [permissions, setPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPermissionsModal, setShowPermissionsModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role_name: 'viewer',
    is_admin: false
  });

  const roles = [
    { value: 'admin', label: 'Administrador', description: 'Acesso total ao sistema' },
    { value: 'manager', label: 'Gerente de RH', description: 'Acesso a operações principais' },
    { value: 'operator', label: 'Operador', description: 'Acesso a funções básicas' },
    { value: 'viewer', label: 'Visualizador', description: 'Acesso somente leitura' }
  ];

  // Carregar dados apenas uma vez
  const loadData = useCallback(async () => {
    if (dataLoaded) return;
    
    setLoading(true);
    try {
      // Fazer as requisições em sequência para evitar sobrecarga
      console.log('🔄 Carregando usuários...');
      const usersResponse = await api.get('/users');
      setUsers(usersResponse.data.users || []);
      
      console.log('🔄 Carregando permissões...');
      const permissionsResponse = await api.get('/users/permissions');
      setPermissions(permissionsResponse.data.permissions || {});
      
      setDataLoaded(true);
      console.log('✅ Dados carregados com sucesso');
    } catch (error) {
      toast.error('Erro ao carregar dados do sistema');
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }, [dataLoaded]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadUsers = async () => {
    try {
      console.log('🔄 Recarregando usuários...');
      const response = await api.get('/users');
      setUsers(response.data.users || []);
    } catch (error) {
      toast.error('Erro ao carregar usuários');
      console.error('Erro ao carregar usuários:', error);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    
    try {
      const response = await api.post('/users', newUser);
      
      if (response.data.success) {
        toast.success('Usuário criado com sucesso!');
        setShowCreateModal(false);
        setNewUser({
          username: '',
          email: '',
          full_name: '',
          password: '',
          role_name: 'viewer',
          is_admin: false
        });
        loadUsers();
      } else {
        toast.error(response.data.message || 'Erro ao criar usuário');
      }
    } catch (error) {
      toast.error(error.response?.data?.message || 'Erro ao criar usuário');
    }
  };

  const handleUpdatePermissions = async (userId, newPermissions) => {
    try {
      const response = await api.post('/users/permissions', {
        user_id: userId,
        permissions: newPermissions
      });
      
      if (response.data.success) {
        toast.success('Permissões atualizadas com sucesso!');
        setShowPermissionsModal(false);
        setSelectedUser(null);
        loadUsers();
      } else {
        toast.error(response.data.message || 'Erro ao atualizar permissões');
      }
    } catch (error) {
      toast.error(error.response?.data?.message || 'Erro ao atualizar permissões');
    }
  };

  const getRoleLabel = (roleName) => {
    const role = roles.find(r => r.value === roleName);
    return role ? role.label : roleName || 'Sem papel';
  };

  const getRoleBadgeColor = (roleName) => {
    switch (roleName) {
      case 'admin':
        return 'bg-red-100 text-red-800';
      case 'manager':
        return 'bg-blue-100 text-blue-800';
      case 'operator':
        return 'bg-green-100 text-green-800';
      case 'viewer':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <UserGroupIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Gerenciamento de Usuários</h1>
            <p className="text-gray-600">Gerencie usuários e suas permissões no sistema</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Novo Usuário</span>
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">
            Usuários do Sistema ({users.length})
          </h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usuário
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Papel
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Permissões
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Último Acesso
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <UserIcon className="h-6 w-6 text-blue-600" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{user.full_name}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                        <div className="text-xs text-gray-400">@{user.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleBadgeColor(user.role)}`}>
                      {getRoleLabel(user.role)}
                    </span>
                    {user.is_admin && (
                      <div className="mt-1">
                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 rounded">
                          <ShieldCheckIcon className="h-3 w-3 mr-1" />
                          Admin
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {user.permissions.length} permissões
                    </div>
                    <div className="text-xs text-gray-500">
                      {user.permissions.slice(0, 3).join(', ')}
                      {user.permissions.length > 3 && '...'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.last_login 
                      ? new Date(user.last_login).toLocaleDateString() 
                      : 'Nunca'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => {
                          setSelectedUser(user);
                          setShowPermissionsModal(true);
                        }}
                        className="text-blue-600 hover:text-blue-900"
                        title="Gerenciar Permissões"
                      >
                        <KeyIcon className="h-5 w-5" />
                      </button>
                      <button
                        className="text-gray-600 hover:text-gray-900"
                        title="Editar Usuário"
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button
                        className="text-red-600 hover:text-red-900"
                        title="Excluir Usuário"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Criar Novo Usuário</h3>
              
              <form onSubmit={handleCreateUser} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nome Completo</label>
                  <input
                    type="text"
                    value={newUser.full_name}
                    onChange={(e) => setNewUser({...newUser, full_name: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nome de Usuário</label>
                  <input
                    type="text"
                    value={newUser.username}
                    onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Senha</label>
                  <input
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Papel</label>
                  <select
                    value={newUser.role_name}
                    onChange={(e) => setNewUser({...newUser, role_name: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {roles.map(role => (
                      <option key={role.value} value={role.value}>
                        {role.label} - {role.description}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_admin"
                    checked={newUser.is_admin}
                    onChange={(e) => setNewUser({...newUser, is_admin: e.target.checked})}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_admin" className="ml-2 block text-sm text-gray-900">
                    Administrador (acesso total)
                  </label>
                </div>
                
                <div className="flex justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Criar Usuário
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Permissions Modal */}
      {showPermissionsModal && selectedUser && (
        <PermissionsModal
          user={selectedUser}
          permissions={permissions}
          onSave={handleUpdatePermissions}
          onClose={() => {
            setShowPermissionsModal(false);
            setSelectedUser(null);
          }}
        />
      )}
    </div>
  );
};

// Component for managing user permissions
const PermissionsModal = ({ user, permissions, onSave, onClose }) => {
  const [selectedPermissions, setSelectedPermissions] = useState(user.permissions || []);

  const handlePermissionToggle = (permissionName) => {
    setSelectedPermissions(prev => {
      if (prev.includes(permissionName)) {
        return prev.filter(p => p !== permissionName);
      } else {
        return [...prev, permissionName];
      }
    });
  };

  const handleSave = () => {
    onSave(user.id, selectedPermissions);
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-3/4 max-w-4xl shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Gerenciar Permissões - {user.full_name}
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(permissions).map(([module, modulePermissions]) => (
              <div key={module} className="border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2 capitalize">{module}</h4>
                <div className="space-y-2">
                  {modulePermissions.map((permission) => (
                    <label key={permission.name} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedPermissions.includes(permission.name)}
                        onChange={() => handlePermissionToggle(permission.name)}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">
                        {permission.description}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
          
          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              Salvar Permissões
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserManagement;