Scripts de manutenção e operações manuais do backend.

Uso esperado:
- execute a partir da raiz do repositório ou informe as variáveis de ambiente necessárias
- para scripts que autenticam na API, defina `SCRIPT_API_PASSWORD`
- para sobrescrever a URL da API, use `SCRIPT_API_URL`
- para sobrescrever a pasta dos CSVs analíticos, use `SCRIPT_ANALYTICS_DIR`

Observações:
- os scripts desta pasta não fazem parte do runtime principal da aplicação
- o wrapper legado `backend/fix_employee_phones_br.py` foi mantido temporariamente para compatibilidade