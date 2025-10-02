import React from 'react';

const CommunicationSender = () => {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Envio de Comunicados</h1>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          🚧 Em Desenvolvimento
        </h2>
        <p className="text-gray-600">
          Esta funcionalidade está sendo implementada. Em breve você poderá:
        </p>
        <ul className="mt-4 list-disc list-inside text-gray-600 space-y-2">
          <li>Enviar comunicados para grupos selecionados</li>
          <li>Suporte a múltiplos formatos (PDF, imagens)</li>
          <li>Seleção flexível de destinatários</li>
          <li>Templates de mensagem personalizáveis</li>
          <li>Agendamento de envios</li>
        </ul>
      </div>
    </div>
  );
};

export default CommunicationSender;
