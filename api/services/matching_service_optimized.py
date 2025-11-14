import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from ..models import Produto, ProdutosMestre


class MatchingServiceOptimized:
    """
    Serviço de matching otimizado que:
    1. Busca apenas produtos SEM matching (tem_matching = False)
    2. Tenta primeiro encaixar em grupos mestres existentes
    3. Cria novos grupos apenas se não houver match com existentes
    4. Atualiza grupos mestres com novos produtos
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.threshold_match = 0.85  # 85% de similaridade para match automático
        self.threshold_group = 0.75  # 75% para adicionar a grupo existente
    
    async def processar_produtos_sem_matching(
        self,
        batch_size: int = 100,
        min_similarity: float = 0.75,
        auto_approve_threshold: float = 0.85
    ) -> Dict:
        """
        Processa apenas produtos que ainda não têm matching
        
        Args:
            batch_size: Quantos produtos processar por vez
            min_similarity: Similaridade mínima para considerar match
            auto_approve_threshold: Acima deste valor, aprova automaticamente
        
        Returns:
            Dict com estatísticas do matching
        """
        start_time = datetime.now()
        
        self.threshold_match = auto_approve_threshold
        self.threshold_group = min_similarity
        
        try:
            # 1. Buscar produtos sem matching
            produtos_sem_matching = self._buscar_produtos_sem_matching(batch_size)
            
            if not produtos_sem_matching:
                return {
                    "status": "success",
                    "message": "Nenhum produto sem matching para processar",
                    "produtos_processados": 0,
                    "grupos_novos": 0,
                    "grupos_atualizados": 0,
                    "tempo_processamento": 0.0
                }
            
            print(f"🔍 {len(produtos_sem_matching)} produtos sem matching encontrados")
            
            # 2. Buscar todos os grupos mestres existentes
            grupos_existentes = self._buscar_grupos_mestres()
            print(f"📦 {len(grupos_existentes)} grupos mestres existentes")
            
            # 3. Processar cada produto
            stats = {
                "produtos_processados": 0,
                "adicionados_a_grupos": 0,
                "grupos_novos_criados": 0,
                "grupos_atualizados": 0,
                "produtos_sem_match": 0
            }
            
            for produto in produtos_sem_matching:
                resultado = await self._processar_produto_individual(
                    produto, 
                    grupos_existentes
                )
                
                if resultado["acao"] == "adicionado_grupo":
                    stats["adicionados_a_grupos"] += 1
                    stats["grupos_atualizados"] += 1
                elif resultado["acao"] == "novo_grupo":
                    stats["grupos_novos_criados"] += 1
                else:
                    stats["produtos_sem_match"] += 1
                
                stats["produtos_processados"] += 1
            
            self.db.commit()
            
            # 4. Calcular estatísticas finais
            end_time = datetime.now()
            tempo_total = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "message": f"{stats['produtos_processados']} produtos processados",
                "produtos_processados": stats["produtos_processados"],
                "grupos_novos": stats["grupos_novos_criados"],
                "grupos_atualizados": stats["grupos_atualizados"],
                "produtos_adicionados": stats["adicionados_a_grupos"],
                "produtos_sem_match": stats["produtos_sem_match"],
                "tempo_processamento": tempo_total,
                "detalhes": stats
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Erro no matching: {str(e)}",
                "produtos_processados": 0,
                "grupos_novos": 0,
                "grupos_atualizados": 0,
                "tempo_processamento": 0.0
            }
    
    def _buscar_produtos_sem_matching(self, batch_size: int) -> List[Produto]:
        """
        Busca produtos que ainda não têm matching
        Prioriza produtos tratados e ativos
        """
        produtos = self.db.query(Produto).filter(
            and_(
                Produto.tratado == True,  # Apenas produtos já tratados
                Produto.status == "ativo",
                or_(
                    Produto.tem_matching == False,
                    Produto.tem_matching.is_(None)
                )
            )
        ).limit(batch_size).all()
        
        return produtos
    
    def _buscar_grupos_mestres(self) -> List[ProdutosMestre]:
        """
        Busca todos os grupos mestres existentes
        """
        grupos = self.db.query(ProdutosMestre).all()
        return grupos
    
    async def _processar_produto_individual(
        self,
        produto: Produto,
        grupos_existentes: List[ProdutosMestre]
    ) -> Dict:
        """
        Processa um produto individual:
        1. Tenta encontrar grupo compatível
        2. Se encontrar, adiciona ao grupo
        3. Se não encontrar, cria novo grupo (se tiver pares)
        """
        melhor_grupo = None
        melhor_score = 0.0
        
        # 1. Procurar grupo mais compatível
        for grupo in grupos_existentes:
            score = self._calcular_similaridade_grupo(produto, grupo)
            
            if score > melhor_score:
                melhor_score = score
                melhor_grupo = grupo
        
        # 2. Decidir ação baseado no score
        if melhor_score >= self.threshold_group:
            # Adicionar ao grupo existente
            self._adicionar_produto_ao_grupo(produto, melhor_grupo)
            return {
                "acao": "adicionado_grupo",
                "id_match": melhor_grupo.id_match,
                "score": melhor_score
            }
        else:
            # Verificar se há outros produtos similares sem matching para criar novo grupo
            produtos_similares = self._buscar_produtos_similares(produto)
            
            if len(produtos_similares) >= 1:  # Mínimo 2 produtos (o produto + 1 similar)
                novo_grupo = self._criar_novo_grupo([produto] + produtos_similares)
                return {
                    "acao": "novo_grupo",
                    "id_match": novo_grupo.id_match,
                    "total_produtos": len(produtos_similares) + 1
                }
            else:
                # Produto não tem match suficiente ainda
                return {
                    "acao": "sem_match",
                    "score": melhor_score
                }
    
    def _calcular_similaridade_grupo(
        self,
        produto: Produto,
        grupo: ProdutosMestre
    ) -> float:
        """
        Calcula similaridade entre produto e grupo mestre
        Baseado em: categoria, marca, nome, embalagem
        """
        score = 0.0
        peso_total = 0.0
        
        # Categoria (peso 30%)
        if produto.categoria and grupo.categoria:
            if produto.categoria.lower() == grupo.categoria.lower():
                score += 0.3
            peso_total += 0.3
        
        # Marca (peso 25%)
        if produto.marca and grupo.marca:
            if produto.marca.lower() == grupo.marca.lower():
                score += 0.25
            peso_total += 0.25
        
        # Embalagem (peso 20%)
        if produto.embalagem and grupo.embalagem:
            sim_embalagem = self._similaridade_texto(produto.embalagem, grupo.embalagem)
            score += sim_embalagem * 0.2
            peso_total += 0.2
        
        # Nome do produto (peso 25%)
        if produto.nome and grupo.nome_produto:
            sim_nome = self._similaridade_texto(produto.nome, grupo.nome_produto)
            score += sim_nome * 0.25
            peso_total += 0.25
        
        return (score / peso_total) if peso_total > 0 else 0.0
    
    def _similaridade_texto(self, texto1: str, texto2: str) -> float:
        """
        Calcula similaridade entre dois textos usando Jaccard
        """
        tokens1 = set(texto1.lower().split())
        tokens2 = set(texto2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        interseccao = tokens1.intersection(tokens2)
        uniao = tokens1.union(tokens2)
        
        return len(interseccao) / len(uniao)
    
    def _adicionar_produto_ao_grupo(self, produto: Produto, grupo: ProdutosMestre):
        """
        Adiciona produto a um grupo mestre existente
        """
        # Atualizar id_bids (lista de IDs dos produtos)
        try:
            id_bids = json.loads(grupo.id_bids) if grupo.id_bids else []
        except:
            id_bids = []
        
        if str(produto.id) not in id_bids:
            id_bids.append(str(produto.id))
            grupo.id_bids = json.dumps(id_bids)
        
        # Atualizar URL do site correspondente
        url_field = f"url_{self._normalizar_nome_site(produto.site)}"
        if hasattr(grupo, url_field) and produto.url:
            setattr(grupo, url_field, produto.url)
        
        # Atualizar estatísticas
        grupo.total_produtos = len(id_bids)
        grupo.total_sites = self._contar_sites_ativos(grupo)
        grupo.data_atualizacao = datetime.now().isoformat()
        
        # Marcar produto como tendo matching
        produto.tem_matching = True
        produto.id_match = grupo.id_match
        produto.atualizado_em = datetime.now()
    
    def _buscar_produtos_similares(self, produto: Produto) -> List[Produto]:
        """
        Busca produtos similares que também não têm matching
        """
        # Query otimizada: mesma categoria e marca
        produtos = self.db.query(Produto).filter(
            and_(
                Produto.id != produto.id,
                Produto.categoria == produto.categoria,
                Produto.marca == produto.marca,
                Produto.tratado == True,
                Produto.status == "ativo",
                or_(
                    Produto.tem_matching == False,
                    Produto.tem_matching.is_(None)
                )
            )
        ).limit(10).all()
        
        # Filtrar por similaridade de nome
        similares = []
        for p in produtos:
            if self._similaridade_texto(produto.nome, p.nome) >= 0.6:
                similares.append(p)
        
        return similares
    
    def _criar_novo_grupo(self, produtos: List[Produto]) -> ProdutosMestre:
        """
        Cria um novo grupo mestre com os produtos fornecidos
        """
        # Gerar novo ID de match
        ultimo_grupo = self.db.query(ProdutosMestre).order_by(
            ProdutosMestre.id.desc()
        ).first()
        
        if ultimo_grupo and ultimo_grupo.id_match:
            # Extrair número do último ID (ex: MSO00123 -> 123)
            try:
                ultimo_num = int(ultimo_grupo.id_match.replace("MSO", ""))
                novo_num = ultimo_num + 1
            except:
                novo_num = 1
        else:
            novo_num = 1
        
        novo_id_match = f"MSO{novo_num:05d}"
        
        # Produto base (primeiro da lista)
        produto_base = produtos[0]
        
        # Lista de IDs
        id_bids = [str(p.id) for p in produtos]
        
        # Criar novo grupo
        novo_grupo = ProdutosMestre(
            id_match=novo_id_match,
            id_bids=json.dumps(id_bids),
            nome_produto=produto_base.nome,
            categoria=produto_base.categoria,
            subcategoria=produto_base.subcategoria,
            marca=produto_base.marca,
            embalagem=produto_base.embalagem,
            total_sites=len(set(p.site for p in produtos)),
            total_produtos=len(produtos),
            score_match=self.threshold_match,
            metodo_matching="otimizado_v2",
            estrategia_base="incremental",
            data_criacao=datetime.now().isoformat(),
            data_atualizacao=datetime.now().isoformat()
        )
        
        # Adicionar URLs por site
        for produto in produtos:
            url_field = f"url_{self._normalizar_nome_site(produto.site)}"
            if hasattr(novo_grupo, url_field) and produto.url:
                setattr(novo_grupo, url_field, produto.url)
        
        self.db.add(novo_grupo)
        self.db.flush()  # Para obter o ID
        
        # Marcar todos os produtos como tendo matching
        for produto in produtos:
            produto.tem_matching = True
            produto.id_match = novo_id_match
            produto.atualizado_em = datetime.now()
        
        return novo_grupo
    
    def _normalizar_nome_site(self, site: str) -> str:
        """
        Normaliza nome do site para o formato das colunas url_*
        Ex: "Dental Cremer" -> "cremer"
        """
        mapeamento = {
            "dental cremer": "cremer",
            "dental speed": "speed",
            "dental medsul": "medsul",
            "dental proclin": "proclin",
            "dental shop": "dentalshop",
            "apoio dental": "apoiodental",
            "interdental": "interdental",
            "surya": "surya"
        }
        
        site_lower = site.lower()
        for chave, valor in mapeamento.items():
            if chave in site_lower:
                return valor
        
        return site_lower.replace(" ", "").replace("dental", "")
    
    def _contar_sites_ativos(self, grupo: ProdutosMestre) -> int:
        """
        Conta quantos sites têm URL no grupo
        """
        sites_url = [
            'url_cremer', 'url_speed', 'url_medsul', 'url_proclin',
            'url_dentalshop', 'url_apoiodental', 'url_interdental', 'url_surya'
        ]
        
        count = 0
        for site in sites_url:
            if hasattr(grupo, site) and getattr(grupo, site):
                count += 1
        
        return count
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas sobre matching
        """
        total_produtos = self.db.query(Produto).filter(Produto.tratado == True).count()
        produtos_com_matching = self.db.query(Produto).filter(
            Produto.tem_matching == True
        ).count()
        produtos_sem_matching = self.db.query(Produto).filter(
            or_(
                Produto.tem_matching == False,
                Produto.tem_matching.is_(None)
            )
        ).count()
        
        total_grupos = self.db.query(ProdutosMestre).count()
        
        # Distribuição de produtos por grupo
        grupos_com_stats = self.db.query(
            ProdutosMestre.total_produtos,
            func.count(ProdutosMestre.id).label('quantidade_grupos')
        ).group_by(ProdutosMestre.total_produtos).all()
        
        distribuicao = {str(produtos): grupos for produtos, grupos in grupos_com_stats}
        
        return {
            "total_produtos": total_produtos,
            "produtos_com_matching": produtos_com_matching,
            "produtos_sem_matching": produtos_sem_matching,
            "total_grupos_mestres": total_grupos,
            "taxa_matching": f"{(produtos_com_matching / total_produtos * 100):.2f}%" if total_produtos > 0 else "0%",
            "distribuicao_produtos_por_grupo": distribuicao,
            "media_produtos_por_grupo": produtos_com_matching / total_grupos if total_grupos > 0 else 0
        }
