import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  CurrencyDollarIcon,
  UsersIcon,
  CalendarDaysIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline';

const IndicatorsLayout = () => {
  const { config } = useTheme();

  const menuItems = [
    { path: '/indicators', name: 'Visão Geral', icon: ChartBarIcon, end: true },
    { path: '/indicators/headcount', name: 'Efetivo', icon: UserGroupIcon },
    { path: '/indicators/turnover', name: 'Rotatividade', icon: ArrowPathIcon },
    { path: '/indicators/demographics', name: 'Demografia', icon: UsersIcon },
    { path: '/indicators/tenure', name: 'Tempo de Casa', icon: ClockIcon },
    { path: '/indicators/leaves', name: 'Afastamentos', icon: ExclamationTriangleIcon },
    { path: '/indicators/payroll', name: 'Folha de Pagamento', icon: CurrencyDollarIcon },
    { path: '/indicators/period-comparison', name: 'Comparativo Períodos', icon: CalendarDaysIcon },
    { path: '/indicators/reports', name: 'Relatórios', icon: DocumentArrowDownIcon },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className={`${config.classes.card} border-b ${config.classes.border} px-6 py-4`}>
        <h1 className={`text-2xl font-bold ${config.classes.text}`}>
          📊 Indicadores de RH
        </h1>
        <p className={`text-sm ${config.classes.textSecondary} mt-1`}>
          Análise e métricas de recursos humanos
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className={`${config.classes.card} border-b ${config.classes.border} px-6`}>
        <nav className="flex flex-wrap gap-1 -mb-px">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : `border-transparent ${config.classes.textSecondary} hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300`
                }`
              }
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="p-6">
        <Outlet />
      </div>
    </div>
  );
};

export default IndicatorsLayout;
