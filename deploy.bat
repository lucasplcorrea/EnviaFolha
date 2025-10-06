@echo off
REM Script para build e deploy da aplicação EnviaFolha no Windows
REM Uso: deploy.bat [environment]

setlocal enabledelayedexpansion

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=production

set IMAGE_NAME=enviafolha-backend
set IMAGE_TAG=latest

echo 🚀 Iniciando deploy do EnviaFolha - Ambiente: %ENVIRONMENT%
echo ==================================================

REM Verificar se o Docker está rodando
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker não está rodando. Inicie o Docker e tente novamente.
    exit /b 1
)

REM Verificar se o arquivo .env existe
if not exist .env (
    echo ⚠️  Arquivo .env não encontrado. Copiando do exemplo...
    copy .env.example .env
    echo 📝 Edite o arquivo .env com suas configurações antes de continuar
    echo    Principais configurações:
    echo    - EVOLUTION_SERVER_URL
    echo    - EVOLUTION_API_KEY
    echo    - EVOLUTION_INSTANCE_NAME
    exit /b 1
)

REM Criar diretórios de dados se não existirem
echo 📁 Criando diretórios de dados...
if not exist data\uploads mkdir data\uploads
if not exist data\enviados mkdir data\enviados
if not exist data\holerites_formatados_final mkdir data\holerites_formatados_final

REM Verificar se employees.json existe
if not exist backend\employees.json (
    echo ⚠️  Arquivo employees.json não encontrado. Criando arquivo básico...
    echo { > backend\employees.json
    echo   "employees": [ >> backend\employees.json
    echo     { >> backend\employees.json
    echo       "id": 1, >> backend\employees.json
    echo       "unique_id": "001", >> backend\employees.json
    echo       "full_name": "Administrador", >> backend\employees.json
    echo       "phone_number": "11999999999", >> backend\employees.json
    echo       "email": "admin@empresa.com", >> backend\employees.json
    echo       "department": "TI", >> backend\employees.json
    echo       "position": "Administrador", >> backend\employees.json
    echo       "is_active": true >> backend\employees.json
    echo     } >> backend\employees.json
    echo   ], >> backend\employees.json
    echo   "users": [ >> backend\employees.json
    echo     { >> backend\employees.json
    echo       "id": 1, >> backend\employees.json
    echo       "username": "admin", >> backend\employees.json
    echo       "password": "admin123", >> backend\employees.json
    echo       "full_name": "Administrador", >> backend\employees.json
    echo       "email": "admin@empresa.com", >> backend\employees.json
    echo       "is_admin": true >> backend\employees.json
    echo     } >> backend\employees.json
    echo   ] >> backend\employees.json
    echo } >> backend\employees.json
)

REM Build da imagem Docker
echo 🔨 Fazendo build da imagem Docker...
docker build -t %IMAGE_NAME%:%IMAGE_TAG% ./backend

REM Parar containers antigos se existirem
echo 🛑 Parando containers antigos...
docker-compose down 2>nul

REM Subir a aplicação
echo 🚀 Iniciando aplicação...
if "%ENVIRONMENT%"=="production" (
    REM Produção - apenas backend
    docker-compose up -d backend
) else (
    REM Desenvolvimento - backend + frontend (se disponível)
    docker-compose --profile with-frontend up -d 2>nul || docker-compose up -d backend
)

REM Aguardar aplicação ficar pronta
echo ⏳ Aguardando aplicação ficar pronta...
timeout /t 10 /nobreak >nul

REM Verificar health check
echo 🔍 Verificando status da aplicação...
curl -f http://localhost:8002/ >nul 2>&1
if errorlevel 1 (
    echo ❌ Aplicação não está respondendo. Verificando logs...
    docker-compose logs backend
    exit /b 1
) else (
    echo ✅ Aplicação está rodando!
    echo.
    echo 🌐 URLs disponíveis:
    echo    - Backend: http://localhost:8002
    echo    - API Health: http://localhost:8002/
    echo    - Dashboard: http://localhost:8002/ (aguarde o frontend carregar)
    echo.
    echo 📋 Próximos passos:
    echo    1. Acesse http://localhost:8002 para verificar se está funcionando
    echo    2. Configure suas credenciais da Evolution API no arquivo .env
    echo    3. Faça login com: admin / admin123
    echo    4. Cadastre seus funcionários
    echo    5. Comece a enviar holerites!
    echo.
    echo 📊 Para monitorar logs:
    echo    docker-compose logs -f backend
    echo.
    echo 🎉 Deploy concluído com sucesso!
)