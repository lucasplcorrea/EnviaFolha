import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  UserCircleIcon,
  KeyIcon,
  EnvelopeIcon,
  BuildingOfficeIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';

const Profile = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  
  // Estados do perfil
  const [profileData, setProfileData] = useState({
    username: '',
    email: '',
    full_name: ''
  });
  
  // Estados de senha
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  useEffect(() => {
    if (user) {
      setProfileData({
        username: user.username || '',
        email: user.email || '',
        full_name: user.full_name || ''
      });
    }
  }, [user]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await api.put('/users/profile', profileData);
      
      if (response.data.success) {
        toast.success('Perfil atualizado com sucesso!');
      }
    } catch (error) {
      console.error('Erro ao atualizar perfil:', error);
      toast.error(error.response?.data?.error || 'Erro ao atualizar perfil');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async (e) => {
    e.preventDefault();

    // Validar senhas
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('As senhas não coincidem');
      return;
    }

    if (passwordData.new_password.length < 6) {
      toast.error('A senha deve ter pelo menos 6 caracteres');
      return;
    }

    setChangingPassword(true);

    try {
      const response = await api.put('/users/change-password', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      
      if (response.data.success) {
        toast.success('Senha alterada com sucesso!');
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      }
    } catch (error) {
      console.error('Erro ao alterar senha:', error);
      toast.error(error.response?.data?.error || 'Erro ao alterar senha');
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center">
          <UserCircleIcon className="h-8 w-8 mr-3 text-blue-600" />
          Meu Perfil
        </h1>
        <p className="text-gray-600 mt-1">
          Gerencie suas informações pessoais e configurações de segurança
        </p>
      </div>

      {/* User Info Card */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center space-x-4 pb-4 border-b">
          <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
            <UserCircleIcon className="h-10 w-10 text-blue-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{user?.full_name || user?.username}</h2>
            <p className="text-sm text-gray-500">@{user?.username}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`inline-flex px-2 py-0.5 text-xs font-semibold rounded-full ${
                user?.is_admin 
                  ? 'bg-purple-100 text-purple-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {user?.is_admin ? '👑 Administrador' : '👤 Usuário'}
              </span>
              <span className="inline-flex px-2 py-0.5 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                <CheckCircleIcon className="h-3 w-3 mr-1 inline" />
                Ativo
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Profile Update Form */}
      <form onSubmit={handleProfileUpdate} className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
          <UserCircleIcon className="h-6 w-6 mr-2 text-gray-600" />
          Informações Pessoais
        </h3>
        
        <div className="space-y-4">
          {/* Username (read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Usuário
            </label>
            <input
              type="text"
              value={profileData.username}
              disabled
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 bg-gray-100 cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">O nome de usuário não pode ser alterado</p>
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome Completo
            </label>
            <input
              type="text"
              name="full_name"
              value={profileData.full_name}
              onChange={handleProfileChange}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Seu nome completo"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <EnvelopeIcon className="inline h-4 w-4 mr-1" />
              E-mail
            </label>
            <input
              type="email"
              name="email"
              value={profileData.email}
              onChange={handleProfileChange}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="seu@email.com"
            />
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Salvando...
                </>
              ) : (
                <>
                  <CheckCircleIcon className="h-5 w-5 mr-2" />
                  Salvar Alterações
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Password Change Form */}
      <form onSubmit={handlePasswordUpdate} className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
          <KeyIcon className="h-6 w-6 mr-2 text-gray-600" />
          Alterar Senha
        </h3>
        
        <div className="space-y-4">
          {/* Current Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Senha Atual
            </label>
            <input
              type="password"
              name="current_password"
              value={passwordData.current_password}
              onChange={handlePasswordChange}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Digite sua senha atual"
            />
          </div>

          {/* New Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nova Senha
            </label>
            <input
              type="password"
              name="new_password"
              value={passwordData.new_password}
              onChange={handlePasswordChange}
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Digite sua nova senha"
            />
            <p className="text-xs text-gray-500 mt-1">Mínimo de 6 caracteres</p>
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confirmar Nova Senha
            </label>
            <input
              type="password"
              name="confirm_password"
              value={passwordData.confirm_password}
              onChange={handlePasswordChange}
              className={`w-full border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 ${
                passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password
                  ? 'border-red-300 focus:ring-red-500'
                  : 'border-gray-300 focus:ring-blue-500'
              }`}
              placeholder="Confirme sua nova senha"
            />
            {passwordData.confirm_password && passwordData.new_password !== passwordData.confirm_password && (
              <p className="text-xs text-red-600 mt-1 flex items-center">
                <XCircleIcon className="h-3 w-3 mr-1" />
                As senhas não coincidem
              </p>
            )}
            {passwordData.confirm_password && passwordData.new_password === passwordData.confirm_password && (
              <p className="text-xs text-green-600 mt-1 flex items-center">
                <CheckCircleIcon className="h-3 w-3 mr-1" />
                As senhas coincidem
              </p>
            )}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={changingPassword || !passwordData.current_password || !passwordData.new_password || passwordData.new_password !== passwordData.confirm_password}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center"
            >
              {changingPassword ? (
                <>
                  <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Alterando...
                </>
              ) : (
                <>
                  <KeyIcon className="h-5 w-5 mr-2" />
                  Alterar Senha
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Info Card */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <BuildingOfficeIcon className="h-5 w-5 text-blue-600 mr-2 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-blue-900">Informações Importantes</h4>
            <p className="text-xs text-blue-700 mt-1">
              • Mantenha suas informações sempre atualizadas<br />
              • Use uma senha forte com letras, números e caracteres especiais<br />
              • Nunca compartilhe sua senha com outras pessoas<br />
              • Em caso de problemas, contate o administrador do sistema
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
