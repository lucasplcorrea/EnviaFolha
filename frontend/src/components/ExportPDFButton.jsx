import React from 'react';
import { PrinterIcon } from '@heroicons/react/24/outline';

const ExportPDFButton = ({ className = '' }) => {
  const handleExportPDF = () => {
    window.print();
  };

  return (
    <button
      onClick={handleExportPDF}
      className={`inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md ${className}`}
      title="Exportar esta página como PDF (Ctrl+P)"
    >
      <PrinterIcon className="h-5 w-5 mr-2" />
      Exportar PDF
    </button>
  );
};

export default ExportPDFButton;
