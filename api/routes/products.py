from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories import ProductRepository
from ..models import (
    ProdutoResponse, 
    ProdutoCreate, 
    ProdutoUpdate,
    ProdutoResumo
)

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("/", response_model=dict)
async def listar_produtos(
    pagina: int = Query(1, ge=1, description="Número da página"),
    tamanho: int = Query(100, ge=1, le=500, description="Itens por página"),
    site: Optional[str] = Query(None, description="Filtrar por site"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    subcategoria: Optional[str] = Query(None, description="Filtrar por subcategoria"),
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    busca: Optional[str] = Query(None, description="Busca textual"),
    db: Session = Depends(get_db)
):
    """
    Listar produtos com paginação e filtros.
    
    **Filtros disponíveis:**
    - site: Nome do site (ex: "Dental Cremer")
    - categoria: Categoria do produto
    - subcategoria: Subcategoria do produto
    - marca: Marca do produto
    - status: Status (ativo/inativo)
    - busca: Busca textual em nome/descrição/marca
    
    **Paginação:**
    - pagina: Número da página (inicia em 1)
    - tamanho: Quantidade de itens (1-500, padrão 100)
    """
    repo = ProductRepository(db)
    skip = (pagina - 1) * tamanho
    
    # Preparar filtros
    filtros = {}
    if site:
        filtros['site'] = site
    if categoria:
        filtros['categoria'] = categoria
    if subcategoria:
        filtros['subcategoria'] = subcategoria
    if marca:
        filtros['marca'] = marca
    if status:
        filtros['status'] = status
    
    # Buscar produtos
    if busca:
        produtos = repo.search(busca, skip=skip, limit=tamanho, **filtros)
        total = repo.count_search(busca, **filtros)
    else:
        produtos = repo.get_all(skip=skip, limit=tamanho, **filtros)
        total = repo.count(**filtros)
    
    # Calcular metadados de paginação
    total_paginas = (total + tamanho - 1) // tamanho
    
    return {
        "dados": [ProdutoResumo.from_orm(p) for p in produtos],
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


@router.get("/sites/disponiveis", response_model=dict)
async def listar_sites_disponiveis(db: Session = Depends(get_db)):
    """
    Retorna lista de sites disponíveis no sistema.
    """
    repo = ProductRepository(db)
    sites = repo.get_distinct_values('site')
    
    return {
        "total": len(sites),
        "sites": sorted(sites)
    }


@router.get("/categorias/disponiveis", response_model=dict)
async def listar_categorias_disponiveis(
    site: Optional[str] = Query(None, description="Filtrar categorias por site"),
    db: Session = Depends(get_db)
):
    """
    Retorna lista de categorias disponíveis.
    Opcionalmente filtradas por site.
    """
    repo = ProductRepository(db)
    filtros = {}
    if site:
        filtros['site'] = site
    
    categorias = repo.get_distinct_values('categoria', **filtros)
    
    return {
        "total": len(categorias),
        "categorias": sorted(categorias),
        "filtros": filtros
    }


@router.get("/marcas/disponiveis", response_model=dict)
async def listar_marcas_disponiveis(
    site: Optional[str] = Query(None, description="Filtrar marcas por site"),
    categoria: Optional[str] = Query(None, description="Filtrar marcas por categoria"),
    db: Session = Depends(get_db)
):
    """
    Retorna lista de marcas disponíveis.
    Opcionalmente filtradas por site e/ou categoria.
    """
    repo = ProductRepository(db)
    filtros = {}
    if site:
        filtros['site'] = site
    if categoria:
        filtros['categoria'] = categoria
    
    marcas = repo.get_distinct_values('marca', **filtros)
    
    return {
        "total": len(marcas),
        "marcas": sorted(marcas),
        "filtros": filtros
    }


@router.get("/{product_id}", response_model=ProdutoResponse)
async def obter_produto(product_id: int, db: Session = Depends(get_db)):
    """
    Obter detalhes completos de um produto específico.
    """
    repo = ProductRepository(db)
    produto = repo.get_by_id(product_id)
    
    if not produto:
        raise HTTPException(status_code=404, detail=f"Produto com ID {product_id} não encontrado")
    
    return produto


@router.post("/", response_model=ProdutoResponse, status_code=201)
async def criar_produto(produto: ProdutoCreate, db: Session = Depends(get_db)):
    """
    Criar novo produto.
    
    **Campos obrigatórios:**
    - nome: Nome do produto
    - site: Site de origem
    - url: URL do produto
    - preco: Preço do produto
    """
    repo = ProductRepository(db)
    novo_produto = repo.create(produto)
    
    return novo_produto


@router.put("/{product_id}", response_model=ProdutoResponse)
async def atualizar_produto(
    product_id: int, 
    produto_update: ProdutoUpdate, 
    db: Session = Depends(get_db)
):
    """
    Atualizar produto existente.
    
    Apenas os campos enviados serão atualizados.
    """
    repo = ProductRepository(db)
    produto_atualizado = repo.update(product_id, produto_update)
    
    if not produto_atualizado:
        raise HTTPException(status_code=404, detail=f"Produto com ID {product_id} não encontrado")
    
    return produto_atualizado


@router.delete("/{product_id}", status_code=204)
async def deletar_produto(product_id: int, db: Session = Depends(get_db)):
    """
    Deletar produto.
    
    **Atenção:** Esta ação é irreversível.
    """
    repo = ProductRepository(db)
    sucesso = repo.delete(product_id)
    
    if not sucesso:
        raise HTTPException(status_code=404, detail=f"Produto com ID {product_id} não encontrado")
    
    return None  # 204 No Content
