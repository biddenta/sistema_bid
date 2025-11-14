from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from .models import Produto, ProdutosMestre, Feedback
from .models import ProdutoCreate, ProdutoUpdate
from .models import ProdutosMestreCreate, ProdutosMestreUpdate
from .models import FeedbackCreate, FeedbackUpdate

class ProductRepository:
    """Repository para operações com Produtos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, product: ProdutoCreate) -> Produto:
        db_product = Produto(**product.dict())
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product
    
    def get_by_id(self, product_id: int) -> Optional[Produto]:
        return self.db.query(Produto).filter(Produto.id == product_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, **filtros) -> List[Produto]:
        """
        Busca produtos com filtros dinâmicos.
        Filtros suportados: site, categoria, subcategoria, marca, status
        """
        query = self.db.query(Produto)
        
        # Aplicar filtros
        if 'site' in filtros and filtros['site']:
            query = query.filter(Produto.site == filtros['site'])
        
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(Produto.categoria == filtros['categoria'])
        
        if 'subcategoria' in filtros and filtros['subcategoria']:
            query = query.filter(Produto.subcategoria == filtros['subcategoria'])
        
        if 'marca' in filtros and filtros['marca']:
            query = query.filter(Produto.marca == filtros['marca'])
        
        if 'status' in filtros and filtros['status']:
            query = query.filter(Produto.status == filtros['status'])
        
        # Paginação
        return query.offset(skip).limit(limit).all()
    
    def count(self, **filtros) -> int:
        """Conta total de produtos com filtros"""
        query = self.db.query(func.count(Produto.id))
        
        if 'site' in filtros and filtros['site']:
            query = query.filter(Produto.site == filtros['site'])
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(Produto.categoria == filtros['categoria'])
        if 'subcategoria' in filtros and filtros['subcategoria']:
            query = query.filter(Produto.subcategoria == filtros['subcategoria'])
        if 'marca' in filtros and filtros['marca']:
            query = query.filter(Produto.marca == filtros['marca'])
        if 'status' in filtros and filtros['status']:
            query = query.filter(Produto.status == filtros['status'])
        
        return query.scalar()
    
    def search(self, busca: str, skip: int = 0, limit: int = 100, **filtros) -> List[Produto]:
        """Busca textual + filtros"""
        query = self.db.query(Produto).filter(
            or_(
                Produto.nome.ilike(f"%{busca}%"),
                Produto.descricao.ilike(f"%{busca}%"),
                Produto.marca.ilike(f"%{busca}%")
            )
        )
        
        # Aplicar filtros adicionais
        if 'site' in filtros and filtros['site']:
            query = query.filter(Produto.site == filtros['site'])
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(Produto.categoria == filtros['categoria'])
        if 'status' in filtros and filtros['status']:
            query = query.filter(Produto.status == filtros['status'])
        
        return query.offset(skip).limit(limit).all()
    
    def count_search(self, busca: str, **filtros) -> int:
        """Conta resultados de busca"""
        query = self.db.query(func.count(Produto.id)).filter(
            or_(
                Produto.nome.ilike(f"%{busca}%"),
                Produto.descricao.ilike(f"%{busca}%"),
                Produto.marca.ilike(f"%{busca}%")
            )
        )
        
        if 'site' in filtros and filtros['site']:
            query = query.filter(Produto.site == filtros['site'])
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(Produto.categoria == filtros['categoria'])
        if 'status' in filtros and filtros['status']:
            query = query.filter(Produto.status == filtros['status'])
        
        return query.scalar()
    
    def update(self, product_id: int, product: ProdutoUpdate) -> Optional[Produto]:
        db_product = self.get_by_id(product_id)
        if db_product:
            update_data = product.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_product, field, value)
            self.db.commit()
            self.db.refresh(db_product)
        return db_product
    
    def delete(self, product_id: int) -> bool:
        db_product = self.get_by_id(product_id)
        if db_product:
            self.db.delete(db_product)
            self.db.commit()
            return True
        return False
    
    def get_distinct_values(self, campo: str, **filtros) -> List[str]:
        """Retorna valores únicos de um campo"""
        query = self.db.query(getattr(Produto, campo)).distinct()
        
        # Aplicar filtros
        if 'site' in filtros and filtros['site']:
            query = query.filter(Produto.site == filtros['site'])
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(Produto.categoria == filtros['categoria'])
        
        result = query.all()
        return [r[0] for r in result if r[0]]


class ProdutosMestreRepository:
    """Repository para operações com Produtos Mestre (grupos)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, grupo: ProdutosMestreCreate) -> ProdutosMestre:
        db_grupo = ProdutosMestre(**grupo.dict())
        self.db.add(db_grupo)
        self.db.commit()
        self.db.refresh(db_grupo)
        return db_grupo
    
    def get_by_id(self, grupo_id: int) -> Optional[ProdutosMestre]:
        return self.db.query(ProdutosMestre).filter(ProdutosMestre.id == grupo_id).first()
    
    def get_by_id_match(self, id_match: str) -> Optional[ProdutosMestre]:
        """Busca por código único (MSO00001, etc)"""
        return self.db.query(ProdutosMestre).filter(ProdutosMestre.id_match == id_match).first()
    
    def get_all(self, skip: int = 0, limit: int = 100, **filtros) -> List[ProdutosMestre]:
        """
        Busca grupos mestre com filtros.
        Filtros: categoria, marca, total_sites_min, score_min
        """
        query = self.db.query(ProdutosMestre)
        
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(ProdutosMestre.categoria == filtros['categoria'])
        
        if 'marca' in filtros and filtros['marca']:
            query = query.filter(ProdutosMestre.marca == filtros['marca'])
        
        if 'total_sites_min' in filtros:
            query = query.filter(ProdutosMestre.total_sites >= filtros['total_sites_min'])
        
        if 'score_min' in filtros:
            query = query.filter(ProdutosMestre.score_match >= filtros['score_min'])
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, **filtros) -> int:
        """Conta total de grupos"""
        query = self.db.query(func.count(ProdutosMestre.id))
        
        if 'categoria' in filtros and filtros['categoria']:
            query = query.filter(ProdutosMestre.categoria == filtros['categoria'])
        if 'marca' in filtros and filtros['marca']:
            query = query.filter(ProdutosMestre.marca == filtros['marca'])
        
        return query.scalar()
    
    def search(self, busca: str, skip: int = 0, limit: int = 100) -> List[ProdutosMestre]:
        """Busca textual em nome_produto e marca"""
        return (
            self.db.query(ProdutosMestre)
            .filter(
                or_(
                    ProdutosMestre.nome_produto.ilike(f"%{busca}%"),
                    ProdutosMestre.marca.ilike(f"%{busca}%")
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(self, grupo_id: int, grupo: ProdutosMestreUpdate) -> Optional[ProdutosMestre]:
        db_grupo = self.get_by_id(grupo_id)
        if db_grupo:
            update_data = grupo.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_grupo, field, value)
            self.db.commit()
            self.db.refresh(db_grupo)
        return db_grupo
    
    def get_statistics(self) -> dict:
        """Estatísticas gerais"""
        total = self.db.query(func.count(ProdutosMestre.id)).scalar()
        media_sites = self.db.query(func.avg(ProdutosMestre.total_sites)).scalar()
        media_score = self.db.query(func.avg(ProdutosMestre.score_match)).scalar()
        
        return {
            "total_grupos": total,
            "media_sites": round(media_sites, 2) if media_sites else 0,
            "media_score": round(media_score, 3) if media_score else 0
        }


class FeedbackRepository:
    """Repository para operações com Feedbacks"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, feedback: FeedbackCreate) -> Feedback:
        """Cria novo feedback no banco"""
        db_feedback = Feedback(**feedback.dict(exclude_none=True))
        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)
        return db_feedback
    
    def get_by_id(self, feedback_id: int) -> Optional[Feedback]:
        """Busca feedback por ID"""
        return self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    def get_by_match(self, match_id: int) -> List[Feedback]:
        """Busca todos os feedbacks de um grupo específico"""
        return (
            self.db.query(Feedback)
            .filter(Feedback.match_id == match_id)
            .order_by(Feedback.criado_em.desc())
            .all()
        )
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Feedback]:
        """Lista todos os feedbacks com paginação"""
        return (
            self.db.query(Feedback)
            .order_by(Feedback.criado_em.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_type(self, tipo_feedback: str, skip: int = 0, limit: int = 100) -> List[Feedback]:
        """Busca feedbacks por tipo"""
        return (
            self.db.query(Feedback)
            .filter(Feedback.tipo_feedback == tipo_feedback)
            .order_by(Feedback.criado_em.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count(self, **filtros) -> int:
        """Conta total de feedbacks com filtros opcionais"""
        query = self.db.query(Feedback)
        
        if 'tipo_feedback' in filtros:
            query = query.filter(Feedback.tipo_feedback == filtros['tipo_feedback'])
        if 'is_correto' in filtros:
            query = query.filter(Feedback.is_correto == filtros['is_correto'])
        if 'match_id' in filtros:
            query = query.filter(Feedback.match_id == filtros['match_id'])
            
        return query.count()
    
    def get_statistics(self) -> dict:
        """Retorna estatísticas gerais dos feedbacks"""
        total = self.db.query(Feedback).count()
        corretos = self.db.query(Feedback).filter(Feedback.is_correto == True).count()
        incorretos = self.db.query(Feedback).filter(Feedback.is_correto == False).count()
        
        # Contar por tipo
        validacao = self.db.query(Feedback).filter(Feedback.tipo_feedback == 'validacao').count()
        parcial = self.db.query(Feedback).filter(Feedback.tipo_feedback == 'parcial').count()
        
        return {
            'total': total,
            'corretos': corretos,
            'incorretos': incorretos,
            'taxa_acerto': round((corretos / total * 100), 2) if total > 0 else 0,
            'por_tipo': {
                'validacao': validacao,
                'parcial': parcial
            }
        }
    
    def update(self, feedback_id: int, feedback_update: FeedbackUpdate) -> Optional[Feedback]:
        """Atualiza feedback existente"""
        db_feedback = self.get_by_id(feedback_id)
        if not db_feedback:
            return None
        
        update_data = feedback_update.dict(exclude_none=True)
        for field, value in update_data.items():
            setattr(db_feedback, field, value)
        
        self.db.commit()
        self.db.refresh(db_feedback)
        return db_feedback
    
    def delete(self, feedback_id: int) -> bool:
        """Deleta feedback"""
        db_feedback = self.get_by_id(feedback_id)
        if not db_feedback:
            return False
        
        self.db.delete(db_feedback)
        self.db.commit()
        return True