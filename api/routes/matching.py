from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from ..database import get_db
from ..repositories import ProdutosMestreRepository, ProductRepository
from ..models import (
    ProdutosMestreResponse,
    ProdutosMestreCreate,
    ProdutosMestreUpdate,
    ProdutosMestreResumo,
    ProdutosMestreComProdutos,
    ProdutoResumo
)

router = APIRouter(prefix="/produtos-mestre", tags=["Produtos Mestre"])


@router.get("/", response_model=dict)
async def listar_grupos(
    pagina: int = Query(1, ge=1, description="Número da página"),
    tamanho: int = Query(100, ge=1, le=500, description="Itens por página"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    total_sites_min: Optional[int] = Query(None, ge=1, le=8, description="Mínimo de sites"),
    score_min: Optional[float] = Query(None, ge=0, le=1, description="Score mínimo"),
    busca: Optional[str] = Query(None, description="Busca textual"),
    db: Session = Depends(get_db)
):
    """
    Listar grupos de produtos mestre com paginação e filtros.
    
    **Filtros disponíveis:**
    - categoria: Categoria do grupo
    - marca: Marca do grupo
    - total_sites_min: Mínimo de sites (1-8)
    - score_min: Score mínimo de matching (0-1)
    - busca: Busca textual em nome_produto
    
    **Paginação:**
    - pagina: Número da página (inicia em 1)
    - tamanho: Quantidade de itens (1-500, padrão 100)
    """
    repo = ProdutosMestreRepository(db)
    skip = (pagina - 1) * tamanho
    
    # Preparar filtros
    filtros = {}
    if categoria:
        filtros['categoria'] = categoria
    if marca:
        filtros['marca'] = marca
    if total_sites_min:
        filtros['total_sites_min'] = total_sites_min
    if score_min:
        filtros['score_min'] = score_min
    
    # Buscar grupos
    if busca:
        grupos = repo.search(busca, skip=skip, limit=tamanho)
        total = repo.count(**filtros)  # Aproximado
    else:
        grupos = repo.get_all(skip=skip, limit=tamanho, **filtros)
        total = repo.count(**filtros)
    
    # Calcular metadados de paginação
    total_paginas = (total + tamanho - 1) // tamanho
    
    return {
        "dados": [ProdutosMestreResumo.from_orm(g) for g in grupos],
        "paginacao": {
            "pagina_atual": pagina,
            "tamanho_pagina": tamanho,
            "total_itens": total,
            "total_paginas": total_paginas,
            "tem_proxima": pagina < total_paginas,
            "tem_anterior": pagina > 1
        },
        "filtros_aplicados": filtros
    }


@router.get("/estatisticas", response_model=dict)
async def obter_estatisticas(db: Session = Depends(get_db)):
    """
    Retorna estatísticas gerais dos produtos mestre.
    
    **Métricas:**
    - total_grupos: Total de grupos no sistema
    - media_sites: Média de sites por grupo
    - media_score: Score médio de matching
    """
    repo = ProdutosMestreRepository(db)
    stats = repo.get_statistics()
    
    return {
        "estatisticas": stats,
        "gerado_em": "2025-10-21T00:00:00"
    }


@router.get("/{grupo_id}", response_model=ProdutosMestreResponse)
async def obter_grupo(grupo_id: int, db: Session = Depends(get_db)):
    """
    Obter detalhes completos de um grupo específico.
    """
    repo = ProdutosMestreRepository(db)
    grupo = repo.get_by_id(grupo_id)
    
    if not grupo:
        raise HTTPException(status_code=404, detail=f"Grupo com ID {grupo_id} não encontrado")
    
    return grupo


@router.get("/codigo/{id_match}", response_model=ProdutosMestreResponse)
async def obter_grupo_por_codigo(id_match: str, db: Session = Depends(get_db)):
    """
    Obter grupo por código MSO (ex: MSO00001).
    """
    repo = ProdutosMestreRepository(db)
    grupo = repo.get_by_id_match(id_match)
    
    if not grupo:
        raise HTTPException(status_code=404, detail=f"Grupo com código {id_match} não encontrado")
    
    return grupo


@router.get("/{grupo_id}/produtos", response_model=dict)
async def obter_produtos_do_grupo(grupo_id: int, db: Session = Depends(get_db)):
    """
    Obter todos os produtos que fazem parte de um grupo.
    Expande o campo id_bids (JSON) e retorna os produtos completos.
    """
    repo_mestre = ProdutosMestreRepository(db)
    repo_produtos = ProductRepository(db)
    
    grupo = repo_mestre.get_by_id(grupo_id)
    
    if not grupo:
        raise HTTPException(status_code=404, detail=f"Grupo com ID {grupo_id} não encontrado")
    
    # Parsear id_bids (JSON array de IDs)
    try:
        if isinstance(grupo.id_bids, str):
            ids_produtos = json.loads(grupo.id_bids)
        else:
            ids_produtos = grupo.id_bids
    except:
        ids_produtos = []
    
    # Buscar produtos
    produtos = []
    for pid in ids_produtos:
        produto = repo_produtos.get_by_id(int(pid))
        if produto:
            produtos.append(ProdutoResumo.from_orm(produto))
    
    return {
        "grupo": ProdutosMestreResumo.from_orm(grupo),
        "total_produtos": len(produtos),
        "produtos": produtos
    }


@router.post("/", response_model=ProdutosMestreResponse, status_code=201)
async def criar_grupo(grupo: ProdutosMestreCreate, db: Session = Depends(get_db)):
    """
    Criar novo grupo de produtos mestre.
    
    **Campos obrigatórios:**
    - nome_produto: Nome do produto
    - id_bids: Array JSON de IDs dos produtos
    """
    repo = ProdutosMestreRepository(db)
    novo_grupo = repo.create(grupo)
    
    return novo_grupo


@router.put("/{grupo_id}", response_model=ProdutosMestreResponse)
async def atualizar_grupo(
    grupo_id: int, 
    grupo_update: ProdutosMestreUpdate, 
    db: Session = Depends(get_db)
):
    """
    Atualizar grupo de produtos mestre.
    
    Apenas os campos enviados serão atualizados.
    """
    repo = ProdutosMestreRepository(db)
    grupo_atualizado = repo.update(grupo_id, grupo_update)
    
    if not grupo_atualizado:
        raise HTTPException(status_code=404, detail=f"Grupo com ID {grupo_id} não encontrado")
    
    return grupo_atualizado