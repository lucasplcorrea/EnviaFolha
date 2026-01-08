# Correção da Tabela hr_indicator_snapshots no PostgreSQL

## Problema

Quando você fez export/import da tabela `hr_indicator_snapshots` sem dados, o PostgreSQL criou a coluna `created_at` como `VARCHAR` em vez de `TIMESTAMP`, causando o erro:

```
operator does not exist: character varying >= timestamp without time zone
```

## Solução

Existem 3 formas de corrigir:

### Opção 1: Script Automático (RECOMENDADO)

**No servidor, execute:**

```bash
# 1. Entrar no diretório do projeto
cd /path/to/EnviaFolha

# 2. Executar script de correção
chmod +x backend/fix-hr-indicators.sh
./backend/fix-hr-indicators.sh
```

Isso vai:
- Dropar a tabela `hr_indicator_snapshots` (está vazia, sem problema)
- Recriar com os tipos corretos
- Configurar índices e triggers
- Reiniciar o backend automaticamente

### Opção 2: Script Python Direto

**Dentro do container backend:**

```bash
# Executar Python dentro do container
docker exec -it nexo-rh-backend python fix_hr_indicators_table.py

# Reiniciar backend
docker restart nexo-rh-backend
```

### Opção 3: SQL Manual

**Se preferir executar SQL diretamente:**

```bash
# Conectar ao PostgreSQL
docker exec -it nexo-rh-postgres psql -U nexo_rh -d nexo_rh_db

# Copiar e colar o conteúdo de fix_hr_indicators_columns.sql
# Ou executar o arquivo:
docker cp backend/fix_hr_indicators_columns.sql nexo-rh-postgres:/tmp/
docker exec -it nexo-rh-postgres psql -U nexo_rh -d nexo_rh_db -f /tmp/fix_hr_indicators_columns.sql
```

## Verificação

Após executar a correção, verifique se funcionou:

```bash
# Ver estrutura da tabela
docker exec nexo-rh-postgres psql -U nexo_rh -d nexo_rh_db -c "\d hr_indicator_snapshots"
```

Você deve ver:
```
 created_at | timestamp without time zone | default CURRENT_TIMESTAMP
 updated_at | timestamp without time zone | default CURRENT_TIMESTAMP
```

## Teste

Acesse o dashboard de HR Indicators no frontend:
- Navegue para "Indicadores de RH"
- Se não houver erros no log, está funcionando!
- Os dados serão calculados e cacheados automaticamente

## Notas Importantes

⚠️ **A tabela será dropada e recriada!** 
- Como está vazia, não há perda de dados
- Os snapshots serão recalculados automaticamente quando acessar o dashboard

✅ **Após a correção:**
- O cache de indicadores funcionará corretamente
- Consultas serão mais rápidas
- Não haverá mais erros de tipo

## Prevenção Futura

**Para evitar esse problema em migrações futuras:**

1. Use sempre o SQLAlchemy para criar tabelas:
   ```python
   from app.models.base import Base
   Base.metadata.create_all(engine)
   ```

2. Ou use o script `create_hr_indicators_table.py` incluído

3. Nunca faça export/import manual de estrutura sem verificar tipos

## Troubleshooting

**Se ainda houver erros após a correção:**

1. Verifique os logs do backend:
   ```bash
   docker logs nexo-rh-backend --tail 50
   ```

2. Confirme a estrutura da tabela:
   ```bash
   docker exec nexo-rh-postgres psql -U nexo_rh -d nexo_rh_db -c "\d hr_indicator_snapshots"
   ```

3. Limpe o cache e reinicie tudo:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Arquivos Criados

- `fix_hr_indicators_table.py` - Script Python automático
- `fix_hr_indicators_columns.sql` - SQL para executar manualmente
- `fix-hr-indicators.sh` - Script bash que automatiza tudo
