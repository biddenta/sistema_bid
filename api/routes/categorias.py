from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Produto
from sqlalchemy import func
import os

router = APIRouter()

# Armazenamento de jobs de validação
validation_jobs: Dict[str, dict] = {}


class CategoriaValidacao(BaseModel):
    """Resultado de validação de uma categoria"""
    categoria: str
    total_produtos: int
    eh_marca_probabilidade: float
    eh_subcategoria_probabilidade: float
    categoria_principal_sugerida: str
    confianca_media: float
    status: str  # "valida", "marca", "subcategoria"


class ValidacaoRequest(BaseModel):
    """Requisição de validação"""
    categorias: Optional[List[str]] = None  # None = todas
    usar_llm: bool = False  # Usar LLM para validação inteligente
    limite_amostras: int = 3  # Produtos por categoria para analisar
    threshold_confianca: float = 0.7


class ValidacaoResponse(BaseModel):
    """Resposta de validação"""
    job_id: str
    status: str
    total_categorias: int
    categorias_validas: int
    marcas_detectadas: int
    subcategorias_detectadas: int
    timestamp: datetime


class HierarquiaCategoria(BaseModel):
    """Estrutura hierárquica de categoria"""
    categoria_principal: str
    subcategorias: List[str]
    total_produtos: int


# ============================================================================
# ANÁLISE DE HIERARQUIA
# ============================================================================

@router.get("/hierarquia/analise", response_model=Dict)
async def analisar_hierarquia(
    db: Session = Depends(get_db)
):
    """
    Analisa estrutura atual de categorias e identifica hierarquia
    
    Returns:
        Análise completa com padrões identificados
    """
    try:
        # Buscar categorias com contagem
        categorias_count = db.query(
            Produto.categoria,
            func.count(Produto.id).label('total')
        ).filter(
            Produto.categoria.isnot(None)
        ).group_by(
            Produto.categoria
        ).order_by(
            func.count(Produto.id).desc()
        ).all()
        
        # Analisar padrões
        categorias_com_separador = []
        categorias_longas = []
        categorias_curtas = []
        
        for cat, total in categorias_count:
            if any(sep in cat for sep in ['>', '|', '-', '/', ':']):
                categorias_com_separador.append({
                    "categoria": cat,
                    "total": total
                })
            
            if len(cat) > 30:
                categorias_longas.append({
                    "categoria": cat,
                    "total": total
                })
            elif len(cat) < 15:
                categorias_curtas.append({
                    "categoria": cat,
                    "total": total
                })
        
        # Agrupar por keywords principais
        keywords_principais = [
            'Ortodontia', 'Endodontia', 'Prótese', 'Implante', 'Cirurgia',
            'Periodontia', 'Dentística', 'Estética', 'Biossegurança',
            'Equipamento', 'Instrumental', 'Radiologia', 'Moldagem',
            'Anestésico', 'Descartável', 'Laboratorial'
        ]
        
        categorias_agrupadas = {}
        for keyword in keywords_principais:
            grupo = []
            for cat, total in categorias_count:
                if keyword.lower() in cat.lower():
                    grupo.append({
                        "categoria": cat,
                        "total": total
                    })
            
            if grupo:
                categorias_agrupadas[keyword] = {
                    "subcategorias": grupo,
                    "total_produtos": sum(x['total'] for x in grupo),
                    "total_subcategorias": len(grupo)
                }
        
        return {
            "total_categorias_distintas": len(categorias_count),
            "com_hierarquia_explicita": len(categorias_com_separador),
            "categorias_longas": categorias_longas[:10],
            "categorias_curtas": categorias_curtas[:20],
            "agrupamento_sugerido": categorias_agrupadas,
            "padroes": {
                "com_separador": len(categorias_com_separador),
                "longas": len(categorias_longas),
                "curtas": len(categorias_curtas)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hierarquia/categorias-principais", response_model=List[HierarquiaCategoria])
async def listar_categorias_principais(
    db: Session = Depends(get_db)
):
    """
    Lista categorias principais com suas subcategorias
    
    Returns:
        Lista de categorias hierárquicas
    """
    try:
        keywords_principais = [
            'Ortodontia', 'Endodontia', 'Prótese', 'Implante', 'Cirurgia',
            'Periodontia', 'Dentística', 'Estética', 'Biossegurança',
            'Equipamento', 'Instrumental', 'Radiologia', 'Moldagem',
            'Anestésico', 'Descartável', 'Laboratorial'
        ]
        
        resultado = []
        
        for keyword in keywords_principais:
            # Buscar categorias que contêm a keyword
            categorias = db.query(
                Produto.categoria,
                func.count(Produto.id).label('total')
            ).filter(
                Produto.categoria.ilike(f"%{keyword}%")
            ).group_by(
                Produto.categoria
            ).all()
            
            if categorias:
                resultado.append(HierarquiaCategoria(
                    categoria_principal=keyword,
                    subcategorias=[cat for cat, _ in categorias],
                    total_produtos=sum(total for _, total in categorias)
                ))
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VALIDAÇÃO COM LLM
# ============================================================================

@router.post("/validar/llm", response_model=ValidacaoResponse)
async def validar_categorias_llm(
    request: ValidacaoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Valida categorias usando LLM (GPT-4)
    
    - Identifica se valor é marca, categoria ou subcategoria
    - Sugere correções
    - Executa em background
    
    **REQUER**: OPENAI_API_KEY configurada
    """
    
    # Verificar API key
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY não configurada. Configure a variável de ambiente."
        )
    
    # Gerar job_id
    job_id = f"validation_{datetime.now():%Y%m%d_%H%M%S}"
    
    # Buscar categorias a validar
    if request.categorias:
        categorias_validar = request.categorias
    else:
        # Todas as categorias
        cats = db.query(Produto.categoria).filter(
            Produto.categoria.isnot(None)
        ).distinct().all()
        categorias_validar = [c[0] for c in cats]
    
    # Criar job
    validation_jobs[job_id] = {
        "status": "pending",
        "categorias_validar": categorias_validar,
        "total": len(categorias_validar),
        "processadas": 0,
        "resultados": {},
        "started_at": datetime.now()
    }
    
    # Executar em background
    background_tasks.add_task(
        executar_validacao_llm,
        job_id=job_id,
        categorias=categorias_validar,
        limite_amostras=request.limite_amostras,
        threshold=request.threshold_confianca,
        db=db
    )
    
    return ValidacaoResponse(
        job_id=job_id,
        status="pending",
        total_categorias=len(categorias_validar),
        categorias_validas=0,
        marcas_detectadas=0,
        subcategorias_detectadas=0,
        timestamp=datetime.now()
    )


@router.get("/validar/status/{job_id}")
async def status_validacao(job_id: str):
    """Verifica status de validação em andamento"""
    
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = validation_jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "total": job["total"],
        "processadas": job["processadas"],
        "progresso": job["processadas"] / job["total"] if job["total"] > 0 else 0,
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at")
    }


@router.get("/validar/resultado/{job_id}")
async def resultado_validacao(job_id: str):
    """Retorna resultado completo de validação"""
    
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    
    job = validation_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Validação ainda não completada. Status: {job['status']}"
        )
    
    # Processar resultados
    resultados = job["resultados"]
    
    categorias_validas = 0
    marcas_detectadas = 0
    subcategorias_detectadas = 0
    
    validacoes = []
    
    for cat, res in resultados.items():
        if res['eh_marca_probabilidade'] > 0.5:
            status = "marca"
            marcas_detectadas += 1
        elif res['eh_subcategoria_probabilidade'] > 0.5:
            status = "subcategoria"
            subcategorias_detectadas += 1
        else:
            status = "valida"
            categorias_validas += 1
        
        validacoes.append(CategoriaValidacao(
            categoria=cat,
            total_produtos=res['total_produtos_analisados'],
            eh_marca_probabilidade=res['eh_marca_probabilidade'],
            eh_subcategoria_probabilidade=res['eh_subcategoria_probabilidade'],
            categoria_principal_sugerida=res['categoria_principal_sugerida'],
            confianca_media=res['confianca_media'],
            status=status
        ))
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "total_categorias": len(validacoes),
        "categorias_validas": categorias_validas,
        "marcas_detectadas": marcas_detectadas,
        "subcategorias_detectadas": subcategorias_detectadas,
        "validacoes": validacoes,
        "timestamp": job["completed_at"]
    }


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

async def executar_validacao_llm(
    job_id: str,
    categorias: List[str],
    limite_amostras: int,
    threshold: float,
    db: Session
):
    """Executa validação com LLM em background"""
    
    try:
        validation_jobs[job_id]["status"] = "running"
        
        # Importar agente (evita import circular)
        import sys
        from pathlib import Path
        ROOT = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(ROOT))
        
        from scripts.agente_validacao_categorias import AgenteValidacaoCategorias
        
        # Criar agente
        agente = AgenteValidacaoCategorias()
        
        # Validar categorias
        resultados = agente.validar_batch_categorias(
            categorias=categorias,
            limite_amostras=limite_amostras
        )
        
        # Atualizar job
        validation_jobs[job_id]["resultados"] = resultados
        validation_jobs[job_id]["processadas"] = len(categorias)
        validation_jobs[job_id]["status"] = "completed"
        validation_jobs[job_id]["completed_at"] = datetime.now()
        
    except Exception as e:
        validation_jobs[job_id]["status"] = "failed"
        validation_jobs[job_id]["error"] = str(e)
        validation_jobs[job_id]["completed_at"] = datetime.now()
