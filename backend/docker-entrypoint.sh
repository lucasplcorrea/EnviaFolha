#!/bin/sh
set -e

echo "Iniciando Nexo RH Backend..."
echo "Executando migrações do banco de dados..."
python run_migrations.py

echo "Iniciando servidor..."
exec python main.py
