const fs = require('fs');
const path = 'frontend/src/pages/Employees.jsx';
let content = fs.readFileSync(path, 'utf8');

const regexModal = /\{\/\* Formulário Modal \*\/\}.*?Salvar Alterações.*?<\/form>\s*<\/div>\s*<\/div>\s*\)\}/s;

const match = content.match(regexModal);
if (match) {
    const modalBlock = match[0];
    content = content.replace(modalBlock, '');
    
    // Insere no fim antes da div final do return global
    const targetEnd = '      {/* Modal de Importação */}';
    if(content.includes(targetEnd)) {
         content = content.replace(targetEnd, modalBlock + '\\n\\n      {/* Modal de Importação */}');
         fs.writeFileSync(path, content);
         console.log('Movido com sucesso!');
    } else {
        const lastDivUnix = '    </div>\\n  );\\n};';
        const lastDivWin = '    </div>\\r\\n  );\\r\\n};';
        if(content.includes(lastDivUnix)) {
           content = content.replace(lastDivUnix, modalBlock + '\\n    </div>\\n  );\\n};'); 
           fs.writeFileSync(path, content);
           console.log('Movido para o fim do form (Unix)!');
        } else if (content.includes(lastDivWin)) {
            content = content.replace(lastDivWin, modalBlock + '\\r\\n    </div>\\r\\n  );\\r\\n};');
            fs.writeFileSync(path, content);
            console.log('Movido para o fim do form (Win)!');
        } else {
            console.log('Não achei targetEnd ou lastDivs');
        }
    }
} else {
    console.log('Nao achei regexModal!');
}
