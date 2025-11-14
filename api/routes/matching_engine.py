from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..services.matching_service import MatchingService
from ..services.matching_service_optimized import MatchingServiceOptimized
from ..repositories import ProductRepository

router = APIRouter(prefix="/matching", tags=["Matching"])

# Armazenamento temporário de jobs (usar Redis em produção)
matching_jobs: Dict[str, dict] = {}


# ============================================================================
# SCHEMAS
# ============================================================================

class MatchRequest(BaseModel):
    """Request para encontrar matches de um produto"""
    produto_id: int = Field(..., description="ID do produto base")
    threshold: float = Field(0.75, ge=0, le=1, description="Score mínimo (0-1)")
    limit: int = Field(10, ge=1, le=100, description="Máximo de resultados")


class MatchBatchRequest(BaseModel):
    """Request para matching em lote"""
    produto_ids: List[int] = Field(..., description="Lista de IDs de produtos")
    threshold: float = Field(0.75, ge=0, le=1, description="Score mínimo (0-1)")
    criar_grupos: bool = Field(False, description="Criar grupos automaticamente?")


class MatchProcessRequest(BaseModel):
    """Request para processamento otimizado de matching"""
    batch_size: int = Field(100, ge=1, le=500, description="Produtos por lote")
    min_similarity: float = Field(0.75, ge=0, le=1, description="Similaridade mínima")
    auto_approve_threshold: float = Field(0.85, ge=0, le=1, description="Threshold auto-aprovação")


class MatchResult(BaseModel):
    """Resultado de um match encontrado"""
    produto_id: int
    produto_nome: str
    produto_site: str
    produto_preco: float
    score: float
    detalhes: dict


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/encontrar", response_model=dict)
async def encontrar_matches(
    request: MatchRequest,
    db: Session = Depends(get_db)
):
    """
    Encontra produtos similares a um produto específico.
    
    **Algoritmo:**
    - Compara nome (peso 50%)
    - Compara marca (peso 25%)
    - Compara categoria (peso 15%)
    - Compara embalagem (peso 10%)
    
    **Score final:** média ponderada (0-1)
    
    **Exemplo:**
    ```json
    {
        "produto_id": 1,
        "threshold": 0.75,
        "limit": 10
    }
    ```
    """
    matching_service = MatchingService(db)
    produto_repo = ProductRepository(db)
    
    # Verificar se produto existe
    produto_base = produto_repo.get_by_id(request.produto_id)
    if not produto_base:
        raise HTTPException(
            status_code=404,
            detail=f"Produto {request.produto_id} não encontrado"
        )
    
    # Encontrar matches
    matches = matching_service.encontrar_matches_para_produto(
        produto_id=request.produto_id,
        threshold=request.threshold,
        limit=request.limit
    )
    
    return {
        "produto_base": {
            "id": produto_base.id,
            "nome": produto_base.nome,
            "site": produto_base.site,
            "categoria": produto_base.categoria,
            "marca": produto_base.marca
        },
        "threshold": request.threshold,
        "total_matches_encontrados": len(matches),
        "matches": matches
    }


@router.post("/executar-lote", response_model=dict)
async def executar_matching_lote(
    request: MatchBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Executa matching para múltiplos produtos em lote.
    
    **Parâmetros:**
    - `produto_ids`: Lista de IDs para processar
    - `threshold`: Score mínimo para considerar match
    - `criar_grupos`: Se True, cria grupos automaticamente em `produtos_mestre`
    
    **Exemplo:**
    ```json
    {
        "produto_ids": [1, 2, 3, 4, 5],
        "threshold": 0.75,
        "criar_grupos": false
    }
    ```
    
    **Nota:** Para grandes volumes, considere usar processamento em background.
    """
    if len(request.produto_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Máximo de 100 produtos por requisição. Use processamento em lote para volumes maiores."
        )
    
    matching_service = MatchingService(db)
    
    # Executar matching
    resultados = matching_service.executar_matching_lote(
        produto_ids=request.produto_ids,
        threshold=request.threshold,
        criar_grupos=request.criar_grupos
    )
    
    return {
        "status": "concluido",
        "parametros": {
            "total_produtos": len(request.produto_ids),
            "threshold": request.threshold,
            "criar_grupos": request.criar_grupos
        },
        "resultados": resultados
    }


@router.post("/criar-grupo", response_model=dict)
async def criar_grupo_manual(
    produto_base_id: int = Query(..., description="ID do produto base"),
    produtos_similares: List[int] = Query(..., description="IDs dos produtos similares"),
    score: float = Query(1.0, ge=0, le=1, description="Score do grupo"),
    db: Session = Depends(get_db)
):
    """
    Cria um grupo de produtos mestre manualmente.
    
    **Uso:** Para validação manual de matches ou criação customizada de grupos.
    
    **Exemplo:**
    ```
    POST /matching/criar-grupo?produto_base_id=1&produtos_similares=2&produtos_similares=3&score=0.95
    ```
    """
    matching_service = MatchingService(db)
    produto_repo = ProductRepository(db)
    
    # Validar produto base
    produto_base = produto_repo.get_by_id(produto_base_id)
    if not produto_base:
        raise HTTPException(
            status_code=404,
            detail=f"Produto base {produto_base_id} não encontrado"
        )
    
    # Validar produtos similares
    for pid in produtos_similares:
        produto = produto_repo.get_by_id(pid)
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {pid} não encontrado"
            )
    
    # Criar grupo
    grupo = matching_service.criar_grupo_automatico(
        produto_base_id=produto_base_id,
        produtos_similares_ids=produtos_similares,
        score_medio=score
    )
    
    if not grupo:
        raise HTTPException(
            status_code=500,
            detail="Erro ao criar grupo"
        )
    
    return {
        "status": "criado",
        "grupo": {
            "id": grupo.id,
            "id_match": grupo.id_match,
            "nome_produto": grupo.nome_produto,
            "total_produtos": grupo.total_produtos,
            "total_sites": grupo.total_sites,
            "score_match": grupo.score_match
        }
    }


@router.get("/estatisticas", response_model=dict)
async def obter_estatisticas_matching(db: Session = Depends(get_db)):
    """
    Retorna estatísticas do sistema de matching.
    
    **Métricas:**
    - Total de produtos no sistema
    - Total de grupos criados
    - Taxa de cobertura (% de produtos com match)
    - Distribuição de scores
    """
    matching_service = MatchingService(db)
    
    total_produtos = matching_service.produto_repo.count()
    total_grupos = matching_service.grupo_repo.count()
    
    # Calcular produtos únicos em grupos (aproximado)
    # Nota: Isso seria mais preciso com query específica
    estatisticas_grupos = matching_service.grupo_repo.get_statistics()
    
    return {
        "produtos": {
            "total": total_produtos,
            "em_grupos": total_grupos * 2,  # Aproximado: média de 2 produtos por grupo
            "taxa_cobertura": (total_grupos * 2 / total_produtos * 100) if total_produtos > 0 else 0
        },
        "grupos": {
            "total": total_grupos,
            "media_produtos_por_grupo": estatisticas_grupos['media_sites'],
            "score_medio": estatisticas_grupos['media_score']
        },
        "sistema": {
            "metodo": "similaridade_ponderada",
            "threshold_padrao": 0.75,
            "algoritmo": "SequenceMatcher + Pesos"
        }
    }


@router.get("/sugestoes/{produto_id}", response_model=dict)
async def obter_sugestoes_matching(
    produto_id: int,
    limit: int = Query(5, ge=1, le=20, description="Número de sugestões"),
    db: Session = Depends(get_db)
):
    """
    Retorna sugestões de produtos similares para validação manual.
    
    **Uso:** Interface de validação pode usar este endpoint para mostrar
    sugestões ao usuário antes de criar o grupo.
    
    **Diferença de /encontrar:**
    - Threshold mais baixo (0.60) para mais sugestões
    - Formato otimizado para UI
    - Inclui informações extras (preço, site, etc.)
    """
    matching_service = MatchingService(db)
    produto_repo = ProductRepository(db)
    
    produto_base = produto_repo.get_by_id(produto_id)
    if not produto_base:
        raise HTTPException(
            status_code=404,
            detail=f"Produto {produto_id} não encontrado"
        )
    
    # Buscar com threshold mais baixo para sugestões
    matches = matching_service.encontrar_matches_para_produto(
        produto_id=produto_id,
        threshold=0.60,  # Mais permissivo
        limit=limit
    )
    
    return {
        "produto_base": {
            "id": produto_base.id,
            "nome": produto_base.nome,
            "site": produto_base.site,
            "preco": produto_base.preco,
            "categoria": produto_base.categoria,
            "marca": produto_base.marca,
            "url": produto_base.url
        },
        "sugestoes": [
            {
                "id": m['produto_id'],
                "nome": m['produto_nome'],
                "site": m['produto_site'],
                "preco": m['produto_preco'],
                "score": m['score'],
                "confianca": "alta" if m['score'] >= 0.85 else "media" if m['score'] >= 0.75 else "baixa",
                "recomendacao": "Provável match" if m['score'] >= 0.80 else "Revisar manualmente"
            }
            for m in matches
        ],
        "total_sugestoes": len(matches)
    }


# ============================================================================
# ENDPOINTS OTIMIZADOS - Processam apenas produtos SEM matching
# ============================================================================

async def executar_matching_otimizado(job_id: str, request: MatchProcessRequest, db: Session):
    """Executa matching otimizado em background"""
    try:
        matching_jobs[job_id]["status"] = "running"
        matching_jobs[job_id]["message"] = "Processando produtos sem matching..."
        
        # Usar serviço otimizado
        service = MatchingServiceOptimized(db)
        resultado = await service.processar_produtos_sem_matching(
            batch_size=request.batch_size,
            min_similarity=request.min_similarity,
            auto_approve_threshold=request.auto_approve_threshold
        )
        
        # Atualizar job com resultado
        matching_jobs[job_id].update({
            "status": "completed" if resultado["status"] == "success" else "failed",
            "message": resultado["message"],
            "progress": 100.0,
            "completed_at": datetime.now().isoformat(),
            "resultado": resultado
        })
        
    except Exception as e:
        matching_jobs[job_id].update({
            "status": "failed",
            "message": f"Erro: {str(e)}",
            "progress": 0.0,
            "completed_at": datetime.now().isoformat()
        })


@router.post("/process", response_model=dict)
async def processar_matching_otimizado(
    request: MatchProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🚀 **ENDPOINT OTIMIZADO** - Processa apenas produtos SEM matching
    
    **Estratégia inteligente:**
    1. Busca apenas produtos com `tem_matching = False`
    2. Tenta adicionar a grupos existentes primeiro
    3. Cria novos grupos apenas se necessário
    4. Atualiza produtos e grupos automaticamente
    
    **Economiza recursos:**
    - ✅ Não reprocessa produtos que já têm matching
    - ✅ Reutiliza grupos existentes
    - ✅ Processamento incremental
    
    **Parâmetros:**
    - `batch_size`: Quantos produtos processar (padrão: 100)
    - `min_similarity`: Similaridade mínima para match (0.75)
    - `auto_approve_threshold`: Threshold para aprovação automática (0.85)
    
    **Exemplo:**
    ```json
    {
        "batch_size": 100,
        "min_similarity": 0.75,
        "auto_approve_threshold": 0.85
    }
    ```
    
    **Retorna:** Job ID para acompanhamento via `/matching/status/{job_id}`
    """
    job_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Criar job
    matching_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "message": "Matching iniciado",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "config": request.dict()
    }
    
    # Adicionar task em background
    background_tasks.add_task(executar_matching_otimizado, job_id, request, db)
    
    return {
        "message": "Matching iniciado - apenas produtos sem matching serão processados",
        "job_id": job_id,
        "status": "pending",
        "info": "Processamento incremental: adiciona a grupos existentes ou cria novos"
    }


@router.get("/status/{job_id}", response_model=dict)
async def obter_status_matching(job_id: str):
    """
    Consulta o status de um job de matching
    
    **Estados possíveis:**
    - `pending`: Aguardando início
    - `running`: Processando
    - `completed`: Concluído com sucesso
    - `failed`: Erro no processamento
    """
    if job_id not in matching_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    return matching_jobs[job_id]


@router.get("/estatisticas-otimizadas", response_model=dict)
async def obter_estatisticas_otimizadas(db: Session = Depends(get_db)):
    """
    Estatísticas detalhadas do sistema de matching otimizado
    
    **Informações:**
    - Total de produtos tratados
    - Produtos com e sem matching
    - Total de grupos mestres
    - Taxa de cobertura
    - Distribuição de produtos por grupo
    """
    service = MatchingServiceOptimized(db)
    stats = service.obter_estatisticas()
    
    return {
        "estatisticas": stats,
        "gerado_em": datetime.now().isoformat()
    }
