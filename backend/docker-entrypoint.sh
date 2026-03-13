#!/bin/bash
set -e

echo "🚀 Iniciando Nexo RH Backend..."

# Executar migrations
echo "🔄 Executando migrations do banco de dados..."
python run_migrations.py

# Iniciar o servidor principal (adapter modular + legado)
echo "✅ Iniciando servidor..."
exec python main.py
