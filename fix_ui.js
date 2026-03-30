const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/Employees.jsx', 'utf8');

content = content.replace(
  /const \[showEditModal, setShowEditModal\] = useState\(false\);\r?\n/,
  ''
);

content = content.replace(
  /setShowEditModal\(false\);\r?\n/g,
  ''
);

content = content.replace(
  /setShowEditModal\(true\);\r?\n/g,
  'setShowForm(true);\r\n'
);

content = content.replace(
  /window.scrollTo\({ top: 0, behavior: 'smooth' }\);\r?\n/g,
  ''
);

const lockedOptions = "disabled={!companyFilter}\\s*>";
const lockedSelectStr = new RegExp("className=\\"w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500\\"\\s*" + lockedOptions + "\\s*<option value=\\"\\">\\{companyFilter \\? 'Todos locais' : 'Selecione empresa...'\\}</option>", "m");

const unlockedSelectStr = \`className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos locais</option>\`;

content = content.replace(lockedSelectStr, unlockedSelectStr);

const modalRegex = /\{\/\* Modal de Edição Rápida \*\/\}.*?<\/div>[\r\n\s]*\)}/s;
content = content.replace(modalRegex, '');

const formHeaderRegex = /\{\/\* Formulário \*\/\}.*?className="grid grid-cols-1 gap-4 sm:grid-cols-2">/s;
const formHeaderReplacement = \`{/* Formulário Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4">
          <div className={\`relative mx-auto p-6 border w-full max-w-4xl shadow-xl rounded-lg \${config.classes.card} \${config.classes.border}\`}>
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-gray-100">
              <h2 className={\`text-xl font-semibold \${config.classes.text}\`}>
                {editingEmployee ? '✏️ Editar Colaborador' : '➕ Novo Colaborador'}
              </h2>
              <button
                onClick={handleCancel}
                type="button"
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 rounded p-1"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2 max-h-[75vh] overflow-y-auto pr-2 pb-2 custom-scrollbar">\`;
            
content = content.replace(formHeaderRegex, formHeaderReplacement);

const formFooterRegex = /<div className="sm:col-span-2 flex justify-end space-x-3">.*?Atualizar' : 'Salvar'\}[\r\n\s]*<\/button>[\r\n\s]*<\/div>[\r\n\s]*<\/form>[\r\n\s]*<\/div>[\r\n\s]*\)}/s;
const formFooterReplacement = \`<div className="sm:col-span-2 flex justify-end space-x-3 pt-4 border-t border-gray-100 mt-2">
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {editingEmployee ? '💾 Salvar Alterações' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
        </div>
      )}\`;
      
content = content.replace(formFooterRegex, formFooterReplacement);

fs.writeFileSync('frontend/src/pages/Employees.jsx', content);
console.log('Script finalizado');
