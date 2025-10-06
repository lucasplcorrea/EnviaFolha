#!/bin/bash

# Script para build e deploy da aplicação EnviaFolha
# Uso: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
IMAGE_NAME="enviafolha-backend"
IMAGE_TAG="latest"

echo "🚀 Iniciando deploy do EnviaFolha - Ambiente: $ENVIRONMENT"
echo "=================================================="

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Inicie o Docker e tente novamente."
    exit 1
fi

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
    echo "⚠️  Arquivo .env não encontrado. Copiando do exemplo..."
    cp .env.example .env
    echo "📝 Edite o arquivo .env com suas configurações antes de continuar"
    echo "   Principais configurações:"
    echo "   - EVOLUTION_SERVER_URL"
    echo "   - EVOLUTION_API_KEY" 
    echo "   - EVOLUTION_INSTANCE_NAME"
    exit 1
fi

# Criar diretórios de dados se não existirem
echo "📁 Criando diretórios de dados..."
mkdir -p data/uploads
mkdir -p data/enviados
mkdir -p data/holerites_formatados_final

# Verificar se employees.json existe
if [ ! -f backend/employees.json ]; then
    echo "⚠️  Arquivo employees.json não encontrado. Criando arquivo básico..."
    cat > backend/employees.json << 'EOF'
{
  "employees": [
    {
      "id": 1,
      "unique_id": "001",
      "full_name": "Administrador",
      "phone_number": "11999999999",
      "email": "admin@empresa.com",
      "department": "TI",
      "position": "Administrador",
      "is_active": true
    }
  ],
  "users": [
    {
      "id": 1,
      "username": "admin",
      "password": "admin123",
      "full_name": "Administrador",
      "email": "admin@empresa.com",
      "is_admin": true
    }
  ]
}
EOF
fi

# Build da imagem Docker
echo "🔨 Fazendo build da imagem Docker..."
docker build -t $IMAGE_NAME:$IMAGE_TAG ./backend

# Parar containers antigos se existirem
echo "🛑 Parando containers antigos..."
docker-compose down || true

# Subir a aplicação
echo "🚀 Iniciando aplicação..."
if [ "$ENVIRONMENT" = "production" ]; then
    # Produção - apenas backend
    docker-compose up -d backend
else
    # Desenvolvimento - backend + frontend (se disponível)
    docker-compose --profile with-frontend up -d || docker-compose up -d backend
fi

# Aguardar aplicação ficar pronta
echo "⏳ Aguardando aplicação ficar pronta..."
sleep 10

# Verificar health check
echo "🔍 Verificando status da aplicação..."
if curl -f http://localhost:8002/ > /dev/null 2>&1; then
    echo "✅ Aplicação está rodando!"
    echo ""
    echo "🌐 URLs disponíveis:"
    echo "   - Backend: http://localhost:8002"
    echo "   - API Health: http://localhost:8002/"
    echo "   - Dashboard: http://localhost:8002/ (aguarde o frontend carregar)"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Acesse http://localhost:8002 para verificar se está funcionando"
    echo "   2. Configure suas credenciais da Evolution API no arquivo .env"
    echo "   3. Faça login com: admin / admin123"
    echo "   4. Cadastre seus funcionários"
    echo "   5. Comece a enviar holerites!"
    echo ""
    echo "📊 Para monitorar logs:"
    echo "   docker-compose logs -f backend"
else
    echo "❌ Aplicação não está respondendo. Verificando logs..."
    docker-compose logs backend
    exit 1
fi

echo "🎉 Deploy concluído com sucesso!"