# Definir variáveis de ambiente
export PYTHONUNBUFFERED=1
export PORT=${PORT:-8000}

# Verificar se o banco de dados existe
if [ ! -f "match_crew.db" ]; then
    echo "Banco de dados não encontrado. Criando novo..."
fi

# Instalar dependências se necessário
if [ ! -d ".venv" ]; then
    echo "Instalando dependências..."
    pip install -r requirements.txt
fi

# Iniciar a aplicação
echo "Iniciando servidor na porta $PORT..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.app:app --bind 0.0.0.0:$PORT --timeout 120 --access-logfile - --error-logfile -
