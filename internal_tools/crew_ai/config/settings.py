import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

class CrewAIConfig:
    """Configurações centralizadas do CrewAI"""
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL = os.getenv('MODEL', 'gpt-4o-mini')
    
    # Database
    DB_PATH = Path("match_crew.db")
    LEGACY_DB_PATH = Path("data/produtos.db")
    
    # Limites de processamento
    MAX_TOKENS_PER_QUERY = 10000  # Proteção contra token overload
    BATCH_SIZE = 10  # Processar de 10 em 10
    MAX_RETRY = 3  # Tentativas em caso de erro
    
    # Logs
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = Path("logs/crewai.log")
    
    @classmethod
    def validate(cls):
        """Valida configurações obrigatórias"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY nao configurada no .env")
        
        if not cls.DB_PATH.exists() and not cls.LEGACY_DB_PATH.exists():
            raise ValueError(f"Banco de dados nao encontrado: {cls.DB_PATH}")
        
        return True
