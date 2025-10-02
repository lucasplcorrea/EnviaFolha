import React from 'react';

const Reports = () => {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Relatórios</h1>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          📊 Dashboard de Analytics
        </h2>
        <p className="text-gray-600">
          Funcionalidade em desenvolvimento. Aqui você encontrará:
        </p>
        <ul className="mt-4 list-disc list-inside text-gray-600 space-y-2">
          <li>Gráficos de performance em tempo real</li>
          <li>Relatórios de sucesso/falha</li>
          <li>Histórico completo de envios</li>
          <li>Estatísticas por departamento</li>
          <li>Exportação de dados</li>
        </ul>
      </div>
    </div>
  );
};

export default Reports;
