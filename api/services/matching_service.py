from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from difflib import SequenceMatcher
import re
import json

from ..models import Produto, ProdutosMestre, ProdutosMestreCreate
from ..repositories import ProductRepository, ProdutosMestreRepository


class MatchingService:
    """Serviço para matching de produtos similares"""
    
    def __init__(self, db: Session):
        self.db = db
        self.produto_repo = ProductRepository(db)
        self.grupo_repo = ProdutosMestreRepository(db)
    
    def normalizar_texto(self, texto: str) -> str:
        """Normaliza texto para comparação"""
        if not texto:
            return ""
        
        # Lowercase
        texto = texto.lower()
        
        # Remover caracteres especiais
        texto = re.sub(r'[^\w\s]', ' ', texto)
        
        # Remover espaços extras
        texto = ' '.join(texto.split())
        
        return texto
    
    def calcular_similaridade(self, texto1: str, texto2: str) -> float:
        """Calcula similaridade entre dois textos (0-1)"""
        texto1_norm = self.normalizar_texto(texto1)
        texto2_norm = self.normalizar_texto(texto2)
        
        if not texto1_norm or not texto2_norm:
            return 0.0
        
        return SequenceMatcher(None, texto1_norm, texto2_norm).ratio()
    
    def produtos_sao_similares(
        self,
        produto1: Produto,
        produto2: Produto,
        threshold: float = 0.75
    ) -> Tuple[bool, float, Dict]:
        """
        Verifica se dois produtos são similares.
        
        Retorna:
            - bool: São similares?
            - float: Score de similaridade
            - dict: Detalhes da comparação
        """
        scores = {}
        
        # 1. Comparar nome (peso 50%)
        scores['nome'] = self.calcular_similaridade(produto1.nome, produto2.nome)
        
        # 2. Comparar marca (peso 25%)
        if produto1.marca and produto2.marca:
            scores['marca'] = 1.0 if produto1.marca.lower() == produto2.marca.lower() else 0.0
        else:
            scores['marca'] = 0.0
        
        # 3. Comparar categoria (peso 15%)
        if produto1.categoria and produto2.categoria:
            scores['categoria'] = 1.0 if produto1.categoria.lower() == produto2.categoria.lower() else 0.0
        else:
            scores['categoria'] = 0.0
        
        # 4. Comparar embalagem (peso 10%)
        if produto1.embalagem and produto2.embalagem:
            scores['embalagem'] = self.calcular_similaridade(produto1.embalagem, produto2.embalagem)
        else:
            scores['embalagem'] = 0.0
        
        # Calcular score final ponderado
        score_final = (
            scores['nome'] * 0.5 +
            scores['marca'] * 0.25 +
            scores['categoria'] * 0.15 +
            scores['embalagem'] * 0.1
        )
        
        detalhes = {
            'scores_individuais': scores,
            'score_final': score_final,
            'threshold': threshold,
            'metodo': 'similaridade_ponderada'
        }
        
        return (score_final >= threshold, score_final, detalhes)
    
    def encontrar_matches_para_produto(
        self,
        produto_id: int,
        threshold: float = 0.75,
        limit: int = 10
    ) -> List[Dict]:
        """
        Encontra produtos similares a um produto específico.
        
        Args:
            produto_id: ID do produto base
            threshold: Score mínimo para considerar match (0-1)
            limit: Número máximo de matches
        
        Returns:
            Lista de dicionários com matches encontrados
        """
        produto_base = self.produto_repo.get_by_id(produto_id)
        
        if not produto_base:
            return []
        
        # Buscar produtos candidatos (mesma categoria, exceto mesmo site)
        candidatos = self.db.query(Produto).filter(
            Produto.id != produto_id,
            Produto.site != produto_base.site,  # Produtos de outros sites
            Produto.categoria == produto_base.categoria if produto_base.categoria else True
        ).limit(1000).all()  # Limitar busca
        
        matches = []
        
        for candidato in candidatos:
            is_similar, score, detalhes = self.produtos_sao_similares(
                produto_base,
                candidato,
                threshold
            )
            
            if is_similar:
                matches.append({
                    'produto_id': candidato.id,
                    'produto_nome': candidato.nome,
                    'produto_site': candidato.site,
                    'produto_preco': candidato.preco,
                    'score': score,
                    'detalhes': detalhes
                })
        
        # Ordenar por score (maior primeiro)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:limit]
    
    def criar_grupo_automatico(
        self,
        produto_base_id: int,
        produtos_similares_ids: List[int],
        score_medio: float
    ) -> Optional[ProdutosMestre]:
        """
        Cria um novo grupo de produtos mestre automaticamente.
        
        Args:
            produto_base_id: ID do produto principal
            produtos_similares_ids: IDs dos produtos similares
            score_medio: Score médio de matching
        
        Returns:
            Grupo criado ou None
        """
        produto_base = self.produto_repo.get_by_id(produto_base_id)
        
        if not produto_base:
            return None
        
        # Contar próximo ID de match
        total_grupos = self.grupo_repo.count()
        proximo_id = total_grupos + 1
        id_match = f"MSO{proximo_id:05d}"
        
        # Todos os IDs do grupo (base + similares)
        todos_ids = [produto_base_id] + produtos_similares_ids
        
        # Contar sites únicos
        sites_unicos = set()
        for pid in todos_ids:
            p = self.produto_repo.get_by_id(pid)
            if p:
                sites_unicos.add(p.site)
        
        # Criar grupo
        grupo_data = ProdutosMestreCreate(
            id_match=id_match,
            id_bids=json.dumps(todos_ids),
            nome_produto=produto_base.nome,
            categoria=produto_base.categoria,
            subcategoria=produto_base.subcategoria,
            marca=produto_base.marca,
            embalagem=produto_base.embalagem,
            total_sites=len(sites_unicos),
            total_produtos=len(todos_ids),
            score_match=score_medio,
            metodo_matching="automatico_api",
            estrategia_base="similaridade_ponderada"
        )
        
        return self.grupo_repo.create(grupo_data)
    
    def executar_matching_lote(
        self,
        produto_ids: List[int],
        threshold: float = 0.75,
        criar_grupos: bool = False
    ) -> Dict:
        """
        Executa matching para múltiplos produtos.
        
        Args:
            produto_ids: Lista de IDs de produtos
            threshold: Score mínimo
            criar_grupos: Se True, cria grupos automaticamente
        
        Returns:
            Estatísticas do processamento
        """
        resultados = {
            'total_processados': 0,
            'total_matches_encontrados': 0,
            'grupos_criados': 0,
            'detalhes': []
        }
        
        for produto_id in produto_ids:
            matches = self.encontrar_matches_para_produto(
                produto_id,
                threshold=threshold
            )
            
            resultados['total_processados'] += 1
            resultados['total_matches_encontrados'] += len(matches)
            
            if criar_grupos and matches:
                # Criar grupo com os matches encontrados
                ids_similares = [m['produto_id'] for m in matches]
                score_medio = sum(m['score'] for m in matches) / len(matches)
                
                grupo = self.criar_grupo_automatico(
                    produto_id,
                    ids_similares,
                    score_medio
                )
                
                if grupo:
                    resultados['grupos_criados'] += 1
                    resultados['detalhes'].append({
                        'produto_id': produto_id,
                        'grupo_id': grupo.id,
                        'grupo_codigo': grupo.id_match,
                        'total_matches': len(matches)
                    })
        
        return resultados
