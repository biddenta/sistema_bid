from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import FeedbackRepository
from ..models import FeedbackCreate, FeedbackUpdate, FeedbackResponse

router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])


@router.get("/", response_model=dict)
async def listar_feedbacks(
    pagina: int = Query(1, ge=1, description="Número da página"),
    tamanho: int = Query(100, ge=1, le=500, description="Itens por página"),
    tipo_feedback: Optional[str] = Query(None, description="Filtrar por tipo"),
    db: Session = Depends(get_db)
):
    """
    Listar feedbacks com paginação.
    
    **Filtros disponíveis:**
    - tipo_feedback: Tipo do feedback
    
    **Paginação:**
    - pagina: Número da página (inicia em 1)
    - tamanho: Quantidade de itens (1-500, padrão 100)
    """
    repo = FeedbackRepository(db)
    skip = (pagina - 1) * tamanho
    
    if tipo_feedback:
        feedbacks = repo.get_by_type(tipo_feedback, skip=skip, limit=tamanho)
        total = repo.count(tipo_feedback=tipo_feedback)
    else:
        feedbacks = repo.get_all(skip=skip, limit=tamanho)
        total = repo.count()
    
    total_paginas = (total + tamanho - 1) // tamanho
    
    return {
        "dados": [FeedbackResponse.from_orm(f) for f in feedbacks],
        "paginacao": {
            "pagina_atual": pagina,
            "tamanho_pagina": tamanho,
            "total_itens": total,
            "total_paginas": total_paginas,
            "tem_proxima": pagina < total_paginas,
            "tem_anterior": pagina > 1
        }
    }


@router.get("/match/{match_id}", response_model=List[FeedbackResponse])
async def obter_feedbacks_por_match(match_id: int, db: Session = Depends(get_db)):
    """
    Obter todos os feedbacks de um match específico.
    """
    repo = FeedbackRepository(db)
    feedbacks = repo.get_by_match(match_id)
    
    return [FeedbackResponse.from_orm(f) for f in feedbacks]


@router.get("/estatisticas", response_model=dict)
async def obter_estatisticas_feedbacks(db: Session = Depends(get_db)):
    """
    Retorna estatísticas gerais dos feedbacks.
    
    **Métricas:**
    - total: Total de feedbacks
    - corretos: Feedbacks marcados como corretos
    - incorretos: Feedbacks marcados como incorretos
    - taxa_acerto: Percentual de acerto
    - por_tipo: Distribuição por tipo de feedback
    """
    repo = FeedbackRepository(db)
    stats = repo.get_statistics()
    
    return {
        "estatisticas": stats,
        "gerado_em": "2025-10-21T00:00:00"
    }


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def obter_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """
    Obter detalhes de um feedback específico.
    """
    repo = FeedbackRepository(db)
    feedback = repo.get_by_id(feedback_id)
    
    if not feedback:
        raise HTTPException(status_code=404, detail=f"Feedback com ID {feedback_id} não encontrado")
    
    return feedback


@router.post("/", response_model=FeedbackResponse, status_code=201)
async def criar_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """
    Criar novo feedback.
    
    **Campos obrigatórios:**
    - match_id: ID do grupo produtos_mestre
    - tipo_feedback: validacao, automatico, manual, parcial
    - is_correto: True=SIM/válido, False=NÃO/PARCIAL
    
    **Campos opcionais para validação PARCIAL:**
    - total_produtos: Total de produtos no grupo
    - produtos_corretos: Quantidade de produtos corretos
    - falsos_positivos: JSON com IDs dos produtos falsos positivos
    - observacoes: Sinônimos, exclusões, comentários
    - usuario: Nome/ID do usuário
    """
    repo = FeedbackRepository(db)
    novo_feedback = repo.create(feedback)
    
    return novo_feedback


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def atualizar_feedback(
    feedback_id: int,
    feedback_update: FeedbackUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualizar feedback existente.
    
    Apenas os campos enviados serão atualizados.
    """
    repo = FeedbackRepository(db)
    feedback_atualizado = repo.update(feedback_id, feedback_update)
    
    if not feedback_atualizado:
        raise HTTPException(status_code=404, detail=f"Feedback com ID {feedback_id} não encontrado")
    
    return feedback_atualizado


@router.delete("/{feedback_id}", status_code=204)
async def deletar_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """
    Deletar feedback.
    
    **Atenção:** Esta ação é irreversível.
    """
    repo = FeedbackRepository(db)
    sucesso = repo.delete(feedback_id)
    
    if not sucesso:
        raise HTTPException(status_code=404, detail=f"Feedback com ID {feedback_id} não encontrado")
    
    return None  # 204 No Content
