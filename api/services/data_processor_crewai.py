import logging
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models import Produto
from .crewai_service import CrewAIService

logger = logging.getLogger(__name__)


class DataProcessorCrewAI:
    """
    Processador de dados usando CrewAI para tratamento inteligente
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.crew_service = CrewAIService(db)
    
    async def processar_produtos_nao_tratados(
        self,
        limite: int = 100,
        usar_crewai: bool = True
    ) -> Dict:
        """
        Processa produtos que ainda não foram tratados
        
        Args:
            limite: Máximo de produtos a processar
            usar_crewai: Se True, usa CrewAI; se False, usa lógica simples
            
        Returns:
            Dict com estatísticas do processamento
        """
        inicio = datetime.now()
        
        try:
            # 1. Buscar produtos não tratados
            produtos_nao_tratados = self.db.query(Produto).filter(
                or_(
                    Produto.tratado == False,
                    Produto.tratado.is_(None)
                )
            ).limit(limite).all()
            
            if not produtos_nao_tratados:
                return {
                    "status": "success",
                    "message": "Nenhum produto pendente de tratamento",
                    "produtos_processados": 0,
                    "tempo_processamento": 0.0
                }
            
            logger.info(f"🔄 Processando {len(produtos_nao_tratados)} produtos...")
            
            # 2. Processar produtos
            if usar_crewai:
                resultados = await self._processar_com_crewai(produtos_nao_tratados)
            else:
                resultados = await self._processar_simples(produtos_nao_tratados)
            
            # 3. Salvar resultados
            produtos_salvos = 0
            for resultado in resultados:
                try:
                    self._atualizar_produto(resultado)
                    produtos_salvos += 1
                except Exception as e:
                    logger.error(f"Erro ao salvar produto {resultado.get('id')}: {e}")
            
            self.db.commit()
            
            tempo_total = (datetime.now() - inicio).total_seconds()
            
            return {
                "status": "success",
                "message": f"{produtos_salvos} produtos processados com sucesso",
                "produtos_processados": produtos_salvos,
                "produtos_totais": len(produtos_nao_tratados),
                "tempo_processamento": tempo_total,
                "velocidade": f"{produtos_salvos/tempo_total:.2f} produtos/segundo" if tempo_total > 0 else "N/A",
                "metodo": "CrewAI" if usar_crewai else "Simples"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro no processamento: {e}")
            return {
                "status": "error",
                "message": f"Erro: {str(e)}",
                "produtos_processados": 0,
                "tempo_processamento": 0.0
            }
    
    async def _processar_com_crewai(self, produtos: List[Produto]) -> List[Dict]:
        """
        Processa produtos usando CrewAI (agentes inteligentes)
        """
        logger.info("🤖 Processando com CrewAI...")
        return await self.crew_service.processar_lote(produtos)
    
    async def _processar_simples(self, produtos: List[Produto]) -> List[Dict]:
        """
        Processamento simples sem IA (fallback)
        """
        logger.info("⚡ Processamento simples (sem IA)...")
        resultados = []
        
        for produto in produtos:
            resultado = {
                'id': produto.id,
                'sku': produto.sku or f"SKU-{produto.id}",
                'nome': self._limpar_texto(produto.nome),
                'marca': self._corrigir_marca(produto.marca, produto.categoria),
                'categoria': self._corrigir_categoria(produto.categoria, produto.marca),
                'subcategoria': produto.subcategoria,
                'embalagem': produto.embalagem,
                'preco': produto.preco,
                'preco_promocional': produto.preco_promocional,
                'descricao': produto.descricao,
                'site': produto.site,
                'url': produto.url,
                'imagem_url': produto.imagem_url,
                'tratado': True,
                'data_tratamento': datetime.now()
            }
            resultados.append(resultado)
        
        return resultados
    
    def _atualizar_produto(self, dados_tratados: Dict):
        """
        Atualiza produto no banco com dados tratados
        """
        produto_id = dados_tratados.get('id')
        produto = self.db.query(Produto).filter(Produto.id == produto_id).first()
        
        if produto:
            # Atualizar campos
            produto.sku = dados_tratados.get('sku', produto.sku)
            produto.nome = dados_tratados.get('nome', produto.nome)
            produto.marca = dados_tratados.get('marca', produto.marca)
            produto.categoria = dados_tratados.get('categoria', produto.categoria)
            produto.subcategoria = dados_tratados.get('subcategoria', produto.subcategoria)
            produto.embalagem = dados_tratados.get('embalagem', produto.embalagem)
            produto.tratado = True
            produto.data_tratamento = datetime.now()
            produto.atualizado_em = datetime.now()
    
    def _limpar_texto(self, texto: str) -> str:
        """Limpeza básica de texto"""
        if not texto:
            return ""
        return " ".join(texto.split())
    
    def _corrigir_marca(self, marca: str, categoria: str) -> str:
        """
        Corrige marca quando está trocada com categoria
        """
        # Lista de marcas conhecidas
        marcas_conhecidas = [
            'Angelus', 'Morelli', 'Golgran', 'Orthometric', 'Maquira',
            'Jota', 'Quinelato', 'Talmax', 'Wilcos', 'Fgm', 'Bio-Art',
            'Abzil', 'Bausch', 'Bioline', 'Dentsply', 'Ivoclar', 'Kerr',
            'Kulzer', '3M', 'Tdv', 'Ultradent', 'Vigodent'
        ]
        
        # Se categoria é uma marca, fazer swap
        if categoria and any(m.lower() in categoria.lower() for m in marcas_conhecidas):
            # Categoria tem marca, então deve ser a marca real
            if not marca or marca == 'Sem Marca':
                return categoria
        
        return marca or "Sem Marca"
    
    def _corrigir_categoria(self, categoria: str, marca: str) -> str:
        """
        Corrige categoria quando está trocada com marca
        """
        # Lista de marcas conhecidas
        marcas_conhecidas = [
            'Angelus', 'Morelli', 'Golgran', 'Orthometric', 'Maquira',
            'Jota', 'Quinelato', 'Talmax', 'Wilcos', 'Fgm', 'Bio-Art',
            'Abzil', 'Bausch', 'Bioline'
        ]
        
        # Se categoria é uma marca, usar marca como categoria (temporário)
        if categoria and any(m.lower() in categoria.lower() for m in marcas_conhecidas):
            return "Diversos"  # Ou tentar inferir da marca
        
        # Normalizar acentuação
        if categoria:
            mapa = {
                'descartaveis': 'Descartáveis',
                'protese': 'Prótese',
                'biosseguranca': 'Biossegurança',
                'dentistica': 'Dentística',
                'estetica': 'Estética'
            }
            
            cat_lower = categoria.lower()
            for key, value in mapa.items():
                if key == cat_lower:
                    return value
        
        # Remover categorias inválidas
        invalidas = ['promocoes', 'lancamento', 'ofertas', 'novidades', 'diversos']
        if categoria and categoria.lower() in invalidas:
            return "Diversos"
        
        return categoria or "Sem Categoria"
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas de produtos
        """
        total = self.db.query(Produto).count()
        tratados = self.db.query(Produto).filter(Produto.tratado == True).count()
        nao_tratados = self.db.query(Produto).filter(
            or_(Produto.tratado == False, Produto.tratado.is_(None))
        ).count()
        com_matching = self.db.query(Produto).filter(Produto.tem_matching == True).count()
        
        return {
            "total_produtos": total,
            "produtos_tratados": tratados,
            "produtos_nao_tratados": nao_tratados,
            "produtos_com_matching": com_matching,
            "porcentagem_tratados": f"{(tratados/total*100):.1f}%" if total > 0 else "0%",
            "porcentagem_matching": f"{(com_matching/total*100):.1f}%" if total > 0 else "0%"
        }
