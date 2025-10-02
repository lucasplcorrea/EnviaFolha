import React from 'react';
import { 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon, 
  UsersIcon,
  ChartBarIcon 
} from '@heroicons/react/24/outline';

const Dashboard = () => {
  const stats = [
    {
      name: 'Colaboradores Cadastrados',
      value: '0',
      icon: UsersIcon,
      color: 'bg-blue-500'
    },
    {
      name: 'Holerites Enviados',
      value: '0',
      icon: DocumentTextIcon,
      color: 'bg-green-500'
    },
    {
      name: 'Comunicados Enviados',
      value: '0',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-purple-500'
    },
    {
      name: 'Taxa de Sucesso',
      value: '0%',
      icon: ChartBarIcon,
      color: 'bg-orange-500'
    }
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h1>
      
      {/* Cards de estatísticas */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`${stat.color} p-3 rounded-md`}>
                    <stat.icon className="h-6 w-6 text-white" />
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.name}
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {stat.value}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Seção de boas-vindas */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Bem-vindo ao Sistema de Envio RH v2.0
        </h2>
        <div className="space-y-4">
          <p className="text-gray-600">
            Sistema completo para envio automatizado de holerites e comunicados via WhatsApp.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-2">📋 Colaboradores</h3>
              <p className="text-sm text-gray-600">
                Gerencie o cadastro de colaboradores e suas informações de contato.
              </p>
            </div>
            
            <div className="border rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-2">📄 Holerites</h3>
              <p className="text-sm text-gray-600">
                Envie holerites protegidos por senha de forma automatizada.
              </p>
            </div>
            
            <div className="border rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-2">📢 Comunicados</h3>
              <p className="text-sm text-gray-600">
                Envie comunicados e documentos para grupos selecionados.
              </p>
            </div>
          </div>
          
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">🚀 Primeiros Passos:</h4>
            <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
              <li>Configure suas credenciais da Evolution API em Configurações</li>
              <li>Cadastre seus colaboradores na seção Colaboradores</li>
              <li>Comece enviando comunicados ou holerites</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
