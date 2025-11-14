from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import time
import logging

from .database import init_db
from .routes import data_processing, matching, products, health, feedbacks, matching_engine, categorias

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Match Crew API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - Configuração para produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React/Next.js dev
        "http://localhost:8501",  # Streamlit
        "http://localhost:8000",  # FastAPI dev
        "*"  # TODO: Remover em produção e especificar domínios
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page-Count"]
)

# Middleware de logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log todas as requisições com tempo de resposta"""
    start_time = time.time()
    
    # Log da requisição
    logger.info(f"📥 {request.method} {request.url.path}")
    
    # Processar requisição
    response = await call_next(request)
    
    # Calcular tempo de processamento
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log da resposta
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Tempo: {process_time:.3f}s"
    )
    
    return response

# Error Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validação do Pydantic"""
    logger.error(f"Erro de validação: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "erro": "Erro de validação",
            "detalhes": exc.errors(),
            "mensagem": "Os dados enviados não são válidos. Verifique os campos e tente novamente."
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler para erros do banco de dados"""
    logger.error(f"Erro de banco de dados: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro no banco de dados",
            "mensagem": "Ocorreu um erro ao acessar o banco de dados. Tente novamente mais tarde.",
            "detalhes": str(exc) if app.debug else None
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler genérico para exceções não tratadas"""
    logger.error(f"Erro não tratado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro interno do servidor",
            "mensagem": "Ocorreu um erro inesperado. Tente novamente mais tarde.",
            "detalhes": str(exc) if app.debug else None
        }
    )

# Incluir rotas
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(products.router, prefix="/api/v1")  # Já tem prefix="/produtos" no router
app.include_router(matching.router, prefix="/api/v1")  # Já tem prefix="/produtos-mestre" no router
app.include_router(matching_engine.router, prefix="/api/v1")  # Já tem prefix="/matching" no router
app.include_router(feedbacks.router, prefix="/api/v1")  # Já tem prefix="/feedbacks" no router
app.include_router(data_processing.router, prefix="/api/v1/data", tags=["data-processing"])
app.include_router(categorias.router, prefix="/api/v1/categorias", tags=["categorias"])

# Importar e incluir rota de scraping
from .routes import scraping
app.include_router(scraping.router, prefix="/api/v1", tags=["scraping"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("🚀 Iniciando Match Crew API...")
    init_db()
    logger.info("✅ Banco de dados inicializado com sucesso!")
    logger.info("📚 Documentação disponível em: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 Encerrando Match Crew API...")

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz da API com informações básicas."""
    return {
        "nome": "Match Crew API",
        "versao": "1.0.0",
        "status": "online",
        "documentacao": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/api/v1/health",
            "produtos": "/api/v1/produtos",
            "produtos_mestre": "/api/v1/produtos-mestre",
            "matching": "/api/v1/matching",
            "feedbacks": "/api/v1/feedbacks",
            "data_processing": "/api/v1/data",
            "scraping": "/api/v1/scraping",
            "categorias": "/api/v1/categorias"
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🔧 Iniciando servidor em modo desenvolvimento...")
    uvicorn.run(
        "api.app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )