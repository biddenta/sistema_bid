from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.data_processor_optimized import DataProcessorOptimized
from ..services.data_processor_crewai import DataProcessorCrewAI

router = APIRouter()

# Armazenamento temporário de jobs (usar Redis em produção)
processing_jobs: Dict[str, dict] = {}

class ProcessingRequest(BaseModel):
    source: str = "scraped_data"
    batch_size: Optional[int] = 100  # Reduzido de 1000 para 100
    site_filtro: Optional[str] = None  # Filtrar por site específico
    clean_data: bool = True
    normalize_prices: bool = True
    categorize: bool = True

class ProcessingStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None

class ProcessingResult(BaseModel):
    job_id: str
    status: str
    total_processados: int
    sucessos: int
    erros: int
    duracao_segundos: float
    detalhes: dict

# Função para executar processamento em background
async def executar_processamento(job_id: str, request: ProcessingRequest, db: Session):
    """Executa processamento de dados em background"""
    try:
        processing_jobs[job_id]["status"] = "running"
        processing_jobs[job_id]["message"] = "Processando produtos novos..."
        
        # Usar serviço otimizado
        processor = DataProcessorOptimized(db)
        resultado = await processor.processar_produtos_novos(
            batch_size=request.batch_size,
            site_filtro=request.site_filtro
        )
        
        # Atualizar job com resultado
        processing_jobs[job_id].update({
            "status": "completed" if resultado["status"] == "success" else "failed",
            "message": resultado["message"],
            "progress": 100.0,
            "completed_at": datetime.now().isoformat(),
            "resultado": resultado
        })
        
    except Exception as e:
        processing_jobs[job_id].update({
            "status": "failed",
            "message": f"Erro: {str(e)}",
            "progress": 0.0,
            "completed_at": datetime.now().isoformat()
        })

@router.post("/process", response_model=dict)
async def process_data(
    request: ProcessingRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Executar processamento de dados NOVOS (apenas produtos não tratados)
    Economiza tokens processando apenas o necessário
    """
    job_id = f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Criar job
    processing_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Processamento iniciado",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "config": request.dict()
    }
    
    # Adicionar task em background
    background_tasks.add_task(executar_processamento, job_id, request, db)
    
    return {
        "message": "Processamento iniciado - apenas produtos novos serão tratados",
        "job_id": job_id,
        "status": "pending",
        "info": "Processando apenas produtos que ainda não foram tratados pela IA"
    }

@router.get("/process/status/{job_id}", response_model=ProcessingStatus)
async def get_processing_status(job_id: str):
    """
    Obter status de um job de processamento
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = processing_jobs[job_id]
    
    return ProcessingStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        started_at=datetime.fromisoformat(job["started_at"]),
        completed_at=datetime.fromisoformat(job["completed_at"]) if job.get("completed_at") else None
    )

@router.post("/clean")
async def clean_data():
    """
    Executar apenas limpeza de dados
    """
    # TODO: Implementar lógica de limpeza específica
    return {"message": "Limpeza de dados executada"}

@router.post("/normalize") 
async def normalize_data():
    """
    Executar apenas normalização de dados
    """
    # TODO: Implementar normalização específica
    return {"message": "Normalização executada"}

@router.post("/categorize")
async def categorize_data():
    """
    Executar apenas categorização automática
    """
    # TODO: Implementar categorização
    return {"message": "Categorização executada"}

@router.get("/stats")
async def get_processing_stats(db: Session = Depends(get_db)):
    """
    Estatísticas de processamento de dados
    """
    try:
        processor = DataProcessorOptimized(db)
        stats = processor.obter_estatisticas()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


# ============================================================================
# NOVO: ENDPOINT COM CREWAI
# ============================================================================

class CrewAIProcessingRequest(BaseModel):
    """Request para processamento com CrewAI"""
    limite: int = 10  # Processar poucos produtos por vez (CrewAI é lento)
    usar_crewai: bool = True  # Se False, usa processamento simples

async def executar_processamento_crewai(job_id: str, request: CrewAIProcessingRequest, db: Session):
    """Executa processamento com CrewAI em background"""
    try:
        processing_jobs[job_id]["status"] = "running"
        processing_jobs[job_id]["message"] = "Processando com CrewAI (agentes inteligentes)..."
        
        # Usar serviço CrewAI
        processor = DataProcessorCrewAI(db)
        resultado = await processor.processar_produtos_nao_tratados(
            limite=request.limite,
            usar_crewai=request.usar_crewai
        )
        
        # Atualizar job com resultado
        processing_jobs[job_id].update({
            "status": "completed" if resultado["status"] == "success" else "failed",
            "message": resultado["message"],
            "progress": 100.0,
            "completed_at": datetime.now().isoformat(),
            "resultado": resultado
        })
        
    except Exception as e:
        processing_jobs[job_id].update({
            "status": "failed",
            "message": f"Erro: {str(e)}",
            "progress": 0.0,
            "completed_at": datetime.now().isoformat()
        })

@router.post("/process-with-crewai", response_model=dict)
async def process_with_crewai(
    request: CrewAIProcessingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🤖 **NOVO**: Processar produtos usando CrewAI (agentes inteligentes)
    
    **IMPORTANTE:** Este endpoint usa os agentes do CrewAI para tratamento
    inteligente de dados, incluindo:
    - analista_nomes: Normalização de nomes
    - analista_marcas: Correção de marcas
    - analista_categorias: ✅ **Corrige categorias automaticamente**
    - analista_precos: Validação de preços
    - analista_embalagens: Padronização de embalagens
    
    **Vantagens:**
    - ✅ Corrige categorias misturadas com marcas
    - ✅ Identifica e categoriza automaticamente
    - ✅ Melhor qualidade de dados
    
    **Desvantagens:**
    - ⏱️ Mais lento (agentes LLM)
    - 💰 Custo de API OpenAI
    
    **Recomendação:** Processar em lotes pequenos (10-50 produtos)
    """
    job_id = f"crew_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Criar job
    processing_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Processamento CrewAI iniciado",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "config": request.dict(),
        "tipo": "CrewAI"
    }
    
    # Adicionar task em background
    background_tasks.add_task(executar_processamento_crewai, job_id, request, db)
    
    return {
        "message": "Processamento CrewAI iniciado - agentes inteligentes processando",
        "job_id": job_id,
        "status": "pending",
        "info": f"Processando {request.limite} produtos com CrewAI",
        "aviso": "CrewAI é mais lento mas muito mais inteligente. Aguarde conclusão.",
        "monitorar": f"GET /api/v1/data/process/status/{job_id}"
    }