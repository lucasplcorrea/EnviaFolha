FROM python:3.11-slim

WORKDIR /app

# Copia apenas arquivos necessários
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements_evolution.txt

EXPOSE 8502

CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.enableCORS=false"]
