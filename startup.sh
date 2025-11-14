# Definir variáveis de ambiente
export PYTHONUNBUFFERED=1
export PORT=${PORT:-8000}

# Definir diretório de trabalho
WORKDIR="/home/site/wwwroot"
cd "$WORKDIR" || exit 1
echo "Diretório de trabalho: $(pwd)"

# Adicionar ao PYTHONPATH
export PYTHONPATH="$WORKDIR:$PYTHONPATH"
echo "PYTHONPATH: $PYTHONPATH"

# Verificar Python e pacotes
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Verificar se api/__init__.py existe
if [ ! -f "api/__init__.py" ]; then
    echo "ERRO: api/__init__.py não encontrado!"
    echo "Criando api/__init__.py..."
    touch api/__init__.py
fi

# Listar estrutura para debug
echo "Estrutura de diretórios:"
ls -la
echo "Conteúdo da pasta api:"
ls -la api/

# Verificar se o banco de dados existe
if [ ! -f "match_crew.db" ]; then
    echo "Banco de dados não encontrado. Aplicação pode falhar."
fi

# Testar importação do módulo
echo "Testando importação do módulo api..."
python -c "import api.app; print('Módulo api.app importado com sucesso')" || {
    echo "❌ ERRO ao importar api.app"
    echo "Tentando corrigir..."
    pip install -r requirements.txt --no-cache-dir
}

# Calcular workers baseado em CPUs (recomendação: 2*CPU + 1)
WORKERS=${WEB_CONCURRENCY:-2}
echo "Usando $WORKERS workers"

# Iniciar a aplicação
echo "=== Iniciando servidor Gunicorn na porta $PORT ==="
exec gunicorn -w "$WORKERS" \
    -k uvicorn.workers.UvicornWorker \
    api.app:app \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload
