import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import DatabaseStatusIndicator from './DatabaseStatusIndicator';
import {
  HomeIcon,
  UsersIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  DocumentArrowUpIcon,
  PaperAirplaneIcon,
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Colaboradores', href: '/employees', icon: UsersIcon },
  { 
    name: 'Processar Holerites', 
    href: '/payroll-processor', 
    icon: DocumentArrowUpIcon,
    description: 'Upload e segmentação de PDFs'
  },
  { 
    name: 'Enviar Holerites', 
    href: '/payroll-sender', 
    icon: PaperAirplaneIcon,
    description: 'Envio via WhatsApp'
  },
  { 
    name: 'Dados de Folha', 
    href: '/payroll-data', 
    icon: ChartBarIcon,
    description: 'Processamento de planilhas'
  },
  { name: 'Comunicados', href: '/communications', icon: ChatBubbleLeftRightIcon },
  { name: 'Relatórios', href: '/reports', icon: ChartBarIcon },
  { name: 'Configurações', href: '/settings', icon: CogIcon },
  { name: 'Usuários', href: '/users', icon: UsersIcon, adminOnly: true },
];

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuth();
  const { config } = useTheme();
  const location = useLocation();

  const SidebarContent = () => (
    <div className={`flex flex-col h-0 flex-1 ${config.classes.sidebar} ${config.classes.border}`}>
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        <div className="flex items-center flex-shrink-0 px-4">
          <h2 className="text-xl font-bold text-brand-500 nexo-theme:text-brand-400">Nexo RH</h2>
        </div>
        
        <nav className="mt-5 flex-1 px-2 space-y-1">
          {navigation
            .filter(item => !item.adminOnly || user?.is_admin)
            .map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`${
                  isActive
                    ? 'bg-brand-100 dark:bg-brand-800 nexo-theme:bg-brand-700 border-brand-500 text-brand-700 dark:text-brand-300 nexo-theme:text-brand-200'
                    : 'border-transparent text-gray-600 dark:text-gray-300 nexo-theme:text-slate-300 hover:bg-gray-50 dark:hover:bg-gray-700 nexo-theme:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-white nexo-theme:hover:text-white'
                } group flex items-center px-2 py-2 text-sm font-medium border-l-4 transition-colors duration-200`}
              >
                <item.icon
                  className={`${
                    isActive 
                      ? 'text-brand-500 dark:text-brand-400 nexo-theme:text-brand-400' 
                      : 'text-gray-400 dark:text-gray-500 nexo-theme:text-slate-500 group-hover:text-gray-500 dark:group-hover:text-gray-400 nexo-theme:group-hover:text-slate-400'
                  } mr-3 h-6 w-6`}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );

  return (
    <div className={`h-screen flex overflow-hidden ${config.classes.body}`}>
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 flex z-40 md:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className={`relative flex-1 flex flex-col max-w-xs w-full ${config.classes.sidebar}`}>
          <div className="absolute top-0 right-0 -mr-12 pt-2">
            <button
              className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-6 w-6 text-white" />
            </button>
          </div>
          <SidebarContent />
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64">
          <SidebarContent />
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        {/* Top bar */}
        <div className={`relative z-10 flex-shrink-0 flex h-16 ${config.classes.card} shadow`}>
          <button
            className={`px-4 ${config.classes.border} ${config.classes.textSecondary} focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-500 md:hidden`}
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          
          <div className="flex-1 px-4 flex justify-between items-center">
            <div className="flex-1 flex">
              <h1 className={`text-2xl font-semibold ${config.classes.text}`}>
                {navigation.find(item => item.href === location.pathname)?.name || 'Dashboard'}
              </h1>
            </div>
            
            <div className="ml-4 flex items-center md:ml-6">
              <div className="flex items-center space-x-4">
                <DatabaseStatusIndicator />
                <span className={`text-sm ${config.classes.textSecondary}`}>Olá, {user?.full_name}</span>
                <button
                  onClick={logout}
                  className={`${config.classes.card} p-1 rounded-full ${config.classes.textSecondary} hover:${config.classes.text} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500`}
                >
                  <ArrowRightOnRectangleIcon className="h-6 w-6" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className={`flex-1 relative overflow-y-auto focus:outline-none ${config.classes.body}`}>
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
