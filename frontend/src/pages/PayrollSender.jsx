import React from 'react';

const PayrollSender = () => {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Envio de Holerites</h1>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          🚧 Em Desenvolvimento
        </h2>
        <p className="text-gray-600">
          Esta funcionalidade está sendo implementada. Em breve você poderá:
        </p>
        <ul className="mt-4 list-disc list-inside text-gray-600 space-y-2">
          <li>Fazer upload de arquivos PDF de holerites</li>
          <li>Segmentar automaticamente por colaborador</li>
          <li>Proteger com senha (4 primeiros dígitos do CPF)</li>
          <li>Enviar via WhatsApp com mensagem única otimizada</li>
          <li>Acompanhar o progresso em tempo real</li>
        </ul>
      </div>
    </div>
  );
};

export default PayrollSender;
