import json
import asyncio
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models import ProdutosBruto, Produto
from ..database import get_db


class DataProcessorOptimized:
    """
    Processador otimizado que:
    1. Busca apenas produtos brutos não processados
    2. Envia para IA apenas produtos novos
    3. Move produtos processados para tabela 'produtos'
    4. Marca produtos como tratados
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def processar_produtos_novos(
        self,
        batch_size: int = 100,
        site_filtro: Optional[str] = None
    ) -> Dict:
        """
        Processa apenas produtos que ainda não foram tratados
        
        Args:
            batch_size: Quantos produtos processar por vez
            site_filtro: Filtrar por site específico (opcional)
        
        Returns:
            Dict com estatísticas do processamento
        """
        start_time = datetime.now()
        
        try:
            # 1. Buscar produtos brutos que não estão na tabela produtos
            produtos_novos = self._buscar_produtos_nao_processados(
                batch_size=batch_size,
                site=site_filtro
            )
            
            if not produtos_novos:
                return {
                    "status": "success",
                    "message": "Nenhum produto novo para processar",
                    "produtos_processados": 0,
                    "produtos_com_erro": 0,
                    "tempo_processamento": 0.0
                }
            
            print(f"📦 {len(produtos_novos)} produtos novos encontrados para processamento")
            
            # 2. Processar produtos em lotes pela IA
            produtos_tratados = []
            produtos_com_erro = []
            
            for i in range(0, len(produtos_novos), 10):  # Lotes de 10 para a IA
                lote = produtos_novos[i:i+10]
                print(f"🤖 Processando lote {i//10 + 1} ({len(lote)} produtos)...")
                
                try:
                    # Aqui você vai chamar sua equipe de IA (CrewAI)
                    lote_tratado = await self._processar_com_ia(lote)
                    produtos_tratados.extend(lote_tratado)
                except Exception as e:
                    print(f"❌ Erro ao processar lote: {e}")
                    produtos_com_erro.extend(lote)
            
            # 3. Salvar produtos tratados na tabela 'produtos'
            produtos_salvos = 0
            for produto_tratado in produtos_tratados:
                try:
                    self._salvar_produto_tratado(produto_tratado)
                    produtos_salvos += 1
                except Exception as e:
                    print(f"❌ Erro ao salvar produto {produto_tratado.get('id')}: {e}")
            
            self.db.commit()
            
            # 4. Calcular estatísticas
            end_time = datetime.now()
            tempo_total = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "message": f"{produtos_salvos} produtos processados com sucesso",
                "produtos_processados": produtos_salvos,
                "produtos_com_erro": len(produtos_com_erro),
                "tempo_processamento": tempo_total,
                "detalhes": {
                    "total_novos": len(produtos_novos),
                    "processados_com_sucesso": produtos_salvos,
                    "erros": len(produtos_com_erro),
                    "tempo_medio_por_produto": tempo_total / len(produtos_novos) if produtos_novos else 0
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Erro no processamento: {str(e)}",
                "produtos_processados": 0,
                "produtos_com_erro": 0,
                "tempo_processamento": 0.0
            }
    
    def _buscar_produtos_nao_processados(
        self,
        batch_size: int = 100,
        site: Optional[str] = None
    ) -> List[ProdutosBruto]:
        """
        Busca produtos em produtos_bruto que não existem em produtos
        """
        # Query otimizada: buscar IDs de produtos_bruto que não estão em produtos
        subquery = self.db.query(Produto.sku).filter(
            Produto.sku.isnot(None)
        ).subquery()
        
        query = self.db.query(ProdutosBruto).filter(
            and_(
                ProdutosBruto.status == "ativo",
                or_(
                    ProdutosBruto.sku.is_(None),  # Produtos sem SKU
                    ProdutosBruto.sku.notin_(subquery)  # SKU não existe em produtos
                )
            )
        )
        
        if site:
            query = query.filter(ProdutosBruto.site == site)
        
        # Buscar apenas o lote especificado
        produtos = query.limit(batch_size).all()
        
        return produtos
    
    async def _processar_com_ia(self, produtos: List[ProdutosBruto]) -> List[Dict]:
        """
        Envia produtos para a equipe de IA processar
        
        IMPORTANTE: Aqui você deve integrar com seu CrewAI
        Por enquanto, vou simular o processamento
        """
        produtos_tratados = []
        
        for produto in produtos:
            # TODO: INTEGRAR COM CREWAI
            # Exemplo de como seria a chamada:
            # resultado = await crew_processar_produto(produto)
            
            # Simulação temporária (remover depois)
            produto_tratado = {
                "id_bruto": produto.id,
                "sku": produto.sku or f"SKU-{produto.id}",
                "nome": produto.nome,
                "descricao": produto.descricao,
                "marca": produto.marca or "Marca Desconhecida",
                "categoria": produto.categoria or "Sem Categoria",
                "subcategoria": produto.subcategoria,
                "embalagem": produto.embalagem,
                "preco": produto.preco,
                "preco_promocional": produto.preco_promocional,
                "site": produto.site,
                "url": produto.url,
                "imagem_url": produto.imagem_url,
                "imagens_extras": produto.imagens_extras,
                "status": "ativo",
                "tratado": True,
                "data_tratamento": datetime.now(),
                "tem_matching": False,
                "id_match": None
            }
            
            produtos_tratados.append(produto_tratado)
        
        return produtos_tratados
    
    def _salvar_produto_tratado(self, produto_data: Dict):
        """
        Salva produto tratado na tabela 'produtos'
        """
        # Verificar se produto já existe (por SKU ou nome+site)
        produto_existente = self.db.query(Produto).filter(
            and_(
                Produto.sku == produto_data.get("sku"),
                Produto.site == produto_data.get("site")
            )
        ).first()
        
        if produto_existente:
            # Atualizar produto existente
            for key, value in produto_data.items():
                if key != "id_bruto" and hasattr(produto_existente, key):
                    setattr(produto_existente, key, value)
            
            produto_existente.atualizado_em = datetime.now()
        else:
            # Criar novo produto
            produto_data_limpo = {k: v for k, v in produto_data.items() if k != "id_bruto"}
            novo_produto = Produto(**produto_data_limpo)
            self.db.add(novo_produto)
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas sobre produtos brutos e tratados
        """
        total_bruto = self.db.query(ProdutosBruto).count()
        total_tratados = self.db.query(Produto).filter(Produto.tratado == True).count()
        total_nao_tratados = self.db.query(Produto).filter(
            or_(Produto.tratado == False, Produto.tratado.is_(None))
        ).count()
        total_com_matching = self.db.query(Produto).filter(Produto.tem_matching == True).count()
        total_sem_matching = self.db.query(Produto).filter(
            or_(Produto.tem_matching == False, Produto.tem_matching.is_(None))
        ).count()
        
        # Produtos por site
        produtos_por_site = {}
        sites = self.db.query(ProdutosBruto.site).distinct().all()
        for (site,) in sites:
            count = self.db.query(ProdutosBruto).filter(ProdutosBruto.site == site).count()
            produtos_por_site[site] = count
        
        return {
            "produtos_bruto_total": total_bruto,
            "produtos_tratados": total_tratados,
            "produtos_nao_tratados": total_nao_tratados,
            "produtos_com_matching": total_com_matching,
            "produtos_sem_matching": total_sem_matching,
            "produtos_por_site": produtos_por_site,
            "pendentes_processamento": total_bruto - total_tratados,
            "taxa_processamento": f"{(total_tratados / total_bruto * 100):.2f}%" if total_bruto > 0 else "0%"
        }
