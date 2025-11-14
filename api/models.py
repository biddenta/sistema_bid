from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()

# SQLAlchemy Models (Database)
class ProdutosBruto(Base):
    """
    Modelo de Produtos Brutos - dados diretos do web scraping (não tratados)
    """
    __tablename__ = "produtos_bruto"
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True)
    
    # Informações básicas (dados brutos do scraping)
    nome = Column(String(500), nullable=False, index=True)
    descricao = Column(Text)
    marca = Column(String(100), index=True)
    categoria = Column(String(100), index=True)
    subcategoria = Column(String(100), index=True)
    embalagem = Column(String(200))
    
    # Preços
    preco = Column(Float)
    preco_promocional = Column(Float)
    
    # Origem
    site = Column(String(50), nullable=False, index=True)
    url = Column(Text)
    
    # Imagens
    imagem_url = Column(Text)
    imagens_extras = Column(Text)  # JSON
    
    # Status
    status = Column(String(50), default="ativo", index=True)
    
    # Datas
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ultima_coleta = Column(DateTime)
    
    # Índices para performance
    __table_args__ = (
        Index('idx_bruto_site_categoria', 'site', 'categoria'),
    )

class Produto(Base):
    """
    Modelo de Produto - produtos tratados pela IA (dados limpos e enriquecidos)
    """
    __tablename__ = "produtos"
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), index=True)  # SKU_site do legado
    
    # Informações básicas
    nome = Column(String(500), nullable=False, index=True)
    descricao = Column(Text)
    marca = Column(String(100), index=True)
    categoria = Column(String(100), index=True)
    subcategoria = Column(String(100), index=True)
    embalagem = Column(String(200))  # info_embalagem do legado
    
    # Preços
    preco = Column(Float)  # preco_normal do legado
    preco_promocional = Column(Float)  # preco_desconto do legado
    
    # Origem
    site = Column(String(50), nullable=False, index=True)
    url = Column(Text)
    
    # Imagens
    imagem_url = Column(Text)  # imagem_principal do legado
    imagens_extras = Column(Text)  # JSON: ["url1", "url2"] - imagem_extra do legado
    
    # Status
    status = Column(String(50), default="ativo", index=True)
    
    # Controle de processamento
    tratado = Column(Boolean, default=False, index=True)  # Se foi processado pela IA
    data_tratamento = Column(DateTime)  # Quando foi tratado
    tem_matching = Column(Boolean, default=False, index=True)  # Se já tem matching
    id_match = Column(String(50), index=True)  # ID do grupo mestre (MSO00001, etc)
    
    # Datas
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ultima_coleta = Column(DateTime)  # Última vez que foi scrapado
    
    # Índices compostos para performance
    __table_args__ = (
        Index('idx_site_categoria', 'site', 'categoria'),
        Index('idx_marca_categoria', 'marca', 'categoria'),
        Index('idx_tratado_matching', 'tratado', 'tem_matching'),  # Para queries otimizadas
    )

class ProdutosMestre(Base):
    """
    Modelo de Produtos Mestre - grupos de produtos similares
    Estrutura EXATA da tabela produtos_mestre do produtos_mestre_unificado.db
    """
    __tablename__ = "produtos_mestre"
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    id_match = Column(String(50), nullable=False, index=True)  # MSO00001, MSO00002...
    id_bids = Column(Text, nullable=False)  # JSON: ["19692", "26896", "5575"]
    
    # Informações do produto mestre
    nome_produto = Column(Text, nullable=False)
    categoria = Column(String(100), index=True)
    subcategoria = Column(String(100))
    marca = Column(String(100), index=True)
    embalagem = Column(String(200))
    
    # URLs dos sites (8 sites)
    url_cremer = Column(Text)
    url_speed = Column(Text)
    url_medsul = Column(Text)
    url_proclin = Column(Text)
    url_dentalshop = Column(Text)
    url_apoiodental = Column(Text)
    url_interdental = Column(Text)
    url_surya = Column(Text)
    
    # Estatísticas
    total_sites = Column(Integer, index=True)
    total_produtos = Column(Integer)
    score_match = Column(Float, index=True)
    
    # Metadata do matching
    metodo_matching = Column(String(50), index=True)  # super_otimizado, hibrido, etc
    estrategia_base = Column(String(50))  # essencial, completo, etc
    
    # Datas
    data_criacao = Column(String(50))  # Mantém formato ISO string do original
    data_atualizacao = Column(String(50))  # Mantém formato ISO string do original

class Feedback(Base):
    """
    Modelo de Feedback - aprendizado do sistema
    Agora referencia produtos_mestre ao invés de matches
    """
    __tablename__ = "feedbacks"
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamento com produtos_mestre
    match_id = Column(Integer, nullable=False, index=True)  # ID do grupo produtos_mestre
    
    # Tipo de feedback
    tipo_feedback = Column(String(50), nullable=False)  # validacao, automatico, manual, parcial
    is_correto = Column(Boolean, nullable=False)  # True=SIM, False=NÃO/PARCIAL
    
    # Detalhes da validação
    observacoes = Column(Text)  # Observações do usuário, sinônimos, exclusões
    padroes_detectados = Column(Text)  # JSON com padrões e falsos positivos
    confianca = Column(Float)  # Score de confiança (0.0 a 1.0)
    
    # Campos específicos para validação PARCIAL
    total_produtos = Column(Integer)  # Total de produtos no grupo
    produtos_corretos = Column(Integer)  # Quantidade de produtos corretos
    falsos_positivos = Column(Text)  # JSON com IDs dos produtos falsos positivos
    
    # Informações adicionais
    usuario = Column(String(100))  # Nome/ID do usuário que fez o feedback
    origem = Column(String(50), default='interface_validacao')  # Origem do feedback
    
    # Datas
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship removido temporariamente até ajustar lógica

# Pydantic Models (API) - Schemas para validação de requisições/respostas

class ProdutoBase(BaseModel):
    """Schema base para Produto"""
    nome: str = Field(..., description="Nome do produto", min_length=1, max_length=500)
    descricao: Optional[str] = Field(None, description="Descrição detalhada")
    marca: Optional[str] = Field(None, description="Marca do produto", max_length=100)
    categoria: Optional[str] = Field(None, description="Categoria", max_length=100)
    subcategoria: Optional[str] = Field(None, description="Subcategoria", max_length=100)
    embalagem: Optional[str] = Field(None, description="Informações da embalagem", max_length=200)
    preco: Optional[float] = Field(None, description="Preço normal", ge=0)
    preco_promocional: Optional[float] = Field(None, description="Preço promocional", ge=0)
    site: str = Field(..., description="Site de origem")
    url: Optional[str] = Field(None, description="URL do produto")
    imagem_url: Optional[str] = Field(None, description="URL da imagem principal")
    imagens_extras: Optional[str] = Field(None, description="JSON com URLs extras")
    sku: Optional[str] = Field(None, description="SKU do site", max_length=100)

class ProdutoCreate(ProdutoBase):
    """Schema para criar produto"""
    pass

class ProdutoUpdate(BaseModel):
    """Schema para atualizar produto (todos os campos opcionais)"""
    nome: Optional[str] = Field(None, min_length=1, max_length=500)
    descricao: Optional[str] = None
    marca: Optional[str] = Field(None, max_length=100)
    categoria: Optional[str] = Field(None, max_length=100)
    subcategoria: Optional[str] = Field(None, max_length=100)
    embalagem: Optional[str] = Field(None, max_length=200)
    preco: Optional[float] = Field(None, ge=0)
    preco_promocional: Optional[float] = Field(None, ge=0)
    site: Optional[str] = None
    url: Optional[str] = None
    imagem_url: Optional[str] = None
    imagens_extras: Optional[str] = None
    sku: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, description="ativo, inativo, rascunho")

class ProdutoResponse(ProdutoBase):
    """Schema de resposta com produto completo"""
    id: int
    status: str
    criado_em: datetime
    atualizado_em: datetime
    ultima_coleta: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ProdutoResumo(BaseModel):
    """Schema resumido para listagens (performance)"""
    id: int
    nome: str
    marca: Optional[str]
    categoria: Optional[str]
    embalagem: Optional[str]
    preco: Optional[float]
    preco_promocional: Optional[float]
    site: str
    url: Optional[str]
    status: str
    
    class Config:
        from_attributes = True

class ProdutosMestreBase(BaseModel):
    """Schema base para Produtos Mestre"""
    id_match: str = Field(..., description="Código único do grupo (ex: MSO00001)")
    id_bids: str = Field(..., description="JSON array com IDs dos produtos do grupo")
    nome_produto: str = Field(..., description="Nome representativo do produto mestre")
    categoria: Optional[str] = Field(None, description="Categoria principal")
    subcategoria: Optional[str] = Field(None, description="Subcategoria")
    marca: Optional[str] = Field(None, description="Marca")
    embalagem: Optional[str] = Field(None, description="Informações de embalagem")
    
    # URLs dos 8 sites
    url_cremer: Optional[str] = None
    url_speed: Optional[str] = None
    url_medsul: Optional[str] = None
    url_proclin: Optional[str] = None
    url_dentalshop: Optional[str] = None
    url_apoiodental: Optional[str] = None
    url_interdental: Optional[str] = None
    url_surya: Optional[str] = None
    
    # Estatísticas
    total_sites: Optional[int] = Field(None, description="Quantidade de sites com este produto")
    total_produtos: Optional[int] = Field(None, description="Total de produtos neste grupo")
    score_match: Optional[float] = Field(None, description="Score de similaridade do grupo")
    metodo_matching: Optional[str] = Field(None, description="Método usado no matching")
    estrategia_base: Optional[str] = Field(None, description="Estratégia aplicada")

class ProdutosMestreCreate(ProdutosMestreBase):
    """Schema para criar produto mestre (raramente usado - gerados automaticamente)"""
    pass

class ProdutosMestreUpdate(BaseModel):
    """Schema para atualizar produto mestre"""
    nome_produto: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    marca: Optional[str] = None
    embalagem: Optional[str] = None
    url_cremer: Optional[str] = None
    url_speed: Optional[str] = None
    url_medsul: Optional[str] = None
    url_proclin: Optional[str] = None
    url_dentalshop: Optional[str] = None
    url_apoiodental: Optional[str] = None
    url_interdental: Optional[str] = None
    url_surya: Optional[str] = None

class ProdutosMestreResponse(ProdutosMestreBase):
    """Schema de resposta com produto mestre completo"""
    id: int
    data_criacao: Optional[str]
    data_atualizacao: Optional[str]
    
    class Config:
        from_attributes = True

class ProdutosMestreResumo(BaseModel):
    """Schema resumido para listagens"""
    id: int
    id_match: str
    nome_produto: str
    marca: Optional[str]
    total_sites: Optional[int]
    score_match: Optional[float]
    
    class Config:
        from_attributes = True

class ProdutosMestreComProdutos(ProdutosMestreResponse):
    """Schema com produtos expandidos do grupo"""
    produtos: List[ProdutoResumo] = Field(default_factory=list, description="Lista de produtos do grupo")

# Schema obsoleto - mantido para compatibilidade temporária
class MatchComProdutos(BaseModel):
    """Schema de match com dados completos dos produtos"""
    match_id: int
    similarity_score: float
    metodo: Optional[str]
    is_validated: bool
    tipo_validacao: Optional[str]
    criado_em: datetime
    produto_1: ProdutoResumo
    produto_2: ProdutoResumo
    
    class Config:
        from_attributes = True

class FeedbackBase(BaseModel):
    """Schema base para Feedback"""
    match_id: int = Field(..., description="ID do grupo produtos_mestre")
    tipo_feedback: str = Field(..., description="validacao, automatico, manual, parcial")
    is_correto: bool = Field(..., description="True=SIM/válido, False=NÃO/PARCIAL")
    observacoes: Optional[str] = Field(None, description="Observações, sinônimos, exclusões")
    padroes_detectados: Optional[str] = Field(None, description="JSON com padrões detectados")
    confianca: Optional[float] = Field(None, description="Score de confiança", ge=0, le=1)

class FeedbackCreate(FeedbackBase):
    """Schema para criar feedback"""
    # Campos adicionais opcionais para validação PARCIAL
    total_produtos: Optional[int] = Field(None, description="Total de produtos no grupo")
    produtos_corretos: Optional[int] = Field(None, description="Quantidade de produtos corretos")
    falsos_positivos: Optional[str] = Field(None, description="JSON com IDs dos falsos positivos")
    usuario: Optional[str] = Field(None, description="Nome/ID do usuário")
    origem: Optional[str] = Field('api', description="Origem do feedback")

class FeedbackUpdate(BaseModel):
    """Schema para atualizar feedback"""
    tipo_feedback: Optional[str] = None
    is_correto: Optional[bool] = None
    observacoes: Optional[str] = None
    padroes_detectados: Optional[str] = None
    confianca: Optional[float] = Field(None, ge=0, le=1)
    total_produtos: Optional[int] = None
    produtos_corretos: Optional[int] = None
    falsos_positivos: Optional[str] = None

class FeedbackResponse(FeedbackBase):
    """Schema de resposta com feedback completo"""
    id: int
    total_produtos: Optional[int]
    produtos_corretos: Optional[int]
    falsos_positivos: Optional[str]
    usuario: Optional[str]
    origem: Optional[str]
    criado_em: datetime
    atualizado_em: Optional[datetime]
    
    class Config:
        from_attributes = True

class FeedbackDeterministico(BaseModel):
    """Schema para resposta de feedback determinístico"""
    match_id: int
    padroes_detectados: int
    detalhes: List[dict]  # Lista de padrões encontrados
    recomendacao: str  # aceitar, rejeitar
    feedback_salvo_em: datetime

# Schemas auxiliares

class PaginacaoMetadata(BaseModel):
    """Metadados de paginação"""
    pagina_atual: int
    limite: int
    total_itens: int
    total_paginas: int
    tem_proxima: bool
    tem_anterior: bool

class ProdutosPaginados(BaseModel):
    """Resposta paginada de produtos"""
    produtos: List[ProdutoResumo]
    paginacao: PaginacaoMetadata

class MatchesPaginados(BaseModel):
    """Resposta paginada de matches"""
    matches: List[MatchComProdutos]
    paginacao: PaginacaoMetadata

class StatusProcesso(BaseModel):
    """Status de um processo (tratamento, matching, scraping)"""
    job_id: str
    tipo: str
    status: str  # pendente, processando, concluido, erro
    progresso: Optional[dict] = None  # percentual, itens_processados, etc
    estatisticas: Optional[dict] = None
    iniciado_em: datetime
    finalizado_em: Optional[datetime] = None
    mensagem: Optional[str] = None

class ExecucaoMatchingRequest(BaseModel):
    """Schema para requisição de execução de matching"""
    algoritmo: str = Field("hibrido", description="hibrido, similaridade, exato")
    threshold: float = Field(0.7, description="Score mínimo", ge=0, le=1)
    max_matches_por_produto: int = Field(10, description="Máximo de matches por produto", ge=1)
    filtros: Optional[dict] = Field(None, description="Filtros adicionais")

class ScrapingRequest(BaseModel):
    """Schema para requisição de scraping"""
    site: str = Field(..., description="Site a ser scrapado")
    tipo: str = Field("completo", description="completo ou diario")
    categorias: Optional[List[str]] = Field(None, description="Categorias específicas")
    forcar_atualizacao: bool = Field(False, description="Forçar atualização de produtos existentes")

class TratamentoRequest(BaseModel):
    """Schema para requisição de tratamento"""
    fonte: str = Field("produtos_existentes", description="base_externa ou produtos_existentes")
    caminho_db: Optional[str] = Field(None, description="Caminho do banco externo")
    opcoes: Optional[dict] = Field(None, description="Opções de tratamento")

class TratamentoItemRequest(BaseModel):
    """Schema para tratamento de item específico"""
    acoes: List[str] = Field(..., description="Lista de ações: limpar, normalizar, categorizar")
    prioridade: str = Field("normal", description="baixa, normal, alta")