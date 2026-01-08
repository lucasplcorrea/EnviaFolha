# CORREÇÃO PARA EXTRAÇÃO DO NÚMERO DA EMPRESA

## Problema Identificado

Os PDFs analisados têm o seguinte layout:
```
Cadastro Nome do Funcionário CBO Empresa Local Departamento FL
189 CRISTINA APARECIDA STOROZ WIL 421310 60 1 000101
```

O código atual usa este regex (linha 3659 de main_legacy.py):
```python
empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
empresa_num = empresa_field_match.group(3) if empresa_field_match else 'UNKNOWN_EMP'
```

**PROBLEMA:** O regex falha porque:
1. O nome tem abreviações/números misturados (ex: "WIL")
2. Não está considerando corretamente a estrutura de campos

## Solução

Usar um regex mais específico que busca diretamente após a linha de cabeçalho:

```python
# REGEX MELHORADO - Captura os campos na ordem correta
# Cadastro = group(1), Nome = ignorado, CBO = group(2), Empresa = group(3)
empresa_field_match = re.search(
    r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*'
    r'(\d+)\s+([A-ZÀ-Ú\s\d]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
    text
)

if empresa_field_match:
    cadastro_num = empresa_field_match.group(1)  # 189
    # group(2) é o nome (ignoramos)
    # group(3) é o CBO
    empresa_num = empresa_field_match.group(4)  # 60 (EMPRESA)
else:
    # Fallback: tentar padrão alternativo mais genérico
    # Linha com: NUMERO NOME_QUALQUER NUMERO NUMERO NUMERO NUMERO NUMERO
    alt_match = re.search(r'(\d+)\s+[\w\s]+?\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text)
    if alt_match:
        empresa_num = alt_match.group(3)  # Terceiro número = empresa
    else:
        empresa_num = 'UNKNOWN_EMP'
```

## Aplicação

Substituir as linhas 3655-3660 em `backend/main_legacy.py`
