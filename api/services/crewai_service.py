import sys
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Carregar variáveis de ambiente do .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Verificar se OpenAI API Key está configurada
if not os.getenv('OPENAI_API_KEY'):
    logging.warning("⚠️  OPENAI_API_KEY não encontrada no .env")

# Adicionar path do legacy
LEGACY_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'legacy', 'src')
sys.path.insert(0, LEGACY_PATH)

from tinder_crew.crew import TinderCrew
from sqlalchemy.orm import Session
from ..models import Produto

logger = logging.getLogger(__name__)


class CrewAIService:
    """Serviço para processar produtos usando CrewAI"""
    
    def __init__(self, db: Session):
        self.db = db
        self.crew = None
        
    def _initialize_crew(self):
        """Inicializa a crew do TinderCrew"""
        if self.crew is None:
            try:
                self.crew = TinderCrew()
                logger.info("✅ CrewAI inicializado com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar CrewAI: {e}")
                raise
    
    async def processar_produto(self, produto: Produto) -> Dict:
        """
        Processa um único produto usando os agentes do CrewAI
        
        Args:
            produto: Produto a ser processado
            
        Returns:
            Dict com dados tratados do produto
        """
        try:
            self._initialize_crew()
            
            # Preparar dados do produto para os agentes
            produto_data = {
                'id': produto.id,
                'nome': produto.nome,
                'descricao': produto.descricao,
                'marca': produto.marca,
                'categoria': produto.categoria,
                'subcategoria': produto.subcategoria,
                'embalagem': produto.embalagem,
                'preco': produto.preco,
                'preco_promocional': produto.preco_promocional,
                'site': produto.site,
                'url': produto.url
            }
            
            # Processar com a equipe de tratamento de dados
            logger.info(f"🤖 Processando produto {produto.id} com CrewAI...")
            
            resultado = self.crew.equipe_tratamento_dados().kickoff(inputs={
                'produto': produto_data,
                'current_year': str(datetime.now().year)
            })
            
            # Extrair dados tratados do resultado
            if isinstance(resultado, dict):
                return resultado
            else:
                # Se retornou string ou outro formato, parsear
                return self._parse_crew_output(resultado, produto_data)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar produto {produto.id}: {e}")
            # Em caso de erro, retornar dados originais
            return self._fallback_processing(produto)
    
    async def processar_lote(self, produtos: List[Produto], batch_size: int = 10) -> List[Dict]:
        """
        Processa lote de produtos usando CrewAI
        
        Args:
            produtos: Lista de produtos
            batch_size: Tamanho do lote (CrewAI processa um por vez)
            
        Returns:
            Lista de produtos processados
        """
        resultados = []
        total = len(produtos)
        
        logger.info(f"🚀 Iniciando processamento de {total} produtos com CrewAI")
        
        for i, produto in enumerate(produtos, 1):
            try:
                logger.info(f"📊 Progresso: {i}/{total} ({i/total*100:.1f}%)")
                resultado = await self.processar_produto(produto)
                resultados.append(resultado)
                
            except Exception as e:
                logger.error(f"❌ Erro no produto {produto.id}: {e}")
                # Adicionar fallback
                resultados.append(self._fallback_processing(produto))
        
        logger.info(f"✅ Processamento concluído: {len(resultados)}/{total} produtos")
        return resultados
    
    def _parse_crew_output(self, resultado: any, produto_original: Dict) -> Dict:
        """
        Parseia saída do CrewAI para formato estruturado
        """
        # Tentar converter string JSON
        if isinstance(resultado, str):
            import json
            try:
                return json.loads(resultado)
            except:
                pass
        
        # Se não conseguir parsear, retornar estrutura padrão
        return {
            'id': produto_original.get('id'),
            'nome': produto_original.get('nome'),
            'marca': produto_original.get('marca'),
            'categoria': produto_original.get('categoria'),
            'subcategoria': produto_original.get('subcategoria'),
            'embalagem': produto_original.get('embalagem'),
            'preco': produto_original.get('preco'),
            'crew_output': str(resultado)[:500]  # Primeiros 500 chars
        }
    
    def _fallback_processing(self, produto: Produto) -> Dict:
        """
        Processamento fallback quando CrewAI falha
        Aplica regras básicas de limpeza
        """
        return {
            'id': produto.id,
            'sku': produto.sku or f"SKU-{produto.id}",
            'nome': self._limpar_nome(produto.nome),
            'marca': self._limpar_marca(produto.marca),
            'categoria': self._limpar_categoria(produto.categoria),
            'subcategoria': produto.subcategoria,
            'embalagem': produto.embalagem,
            'preco': produto.preco,
            'preco_promocional': produto.preco_promocional,
            'site': produto.site,
            'url': produto.url,
            'processado_com': 'fallback',
            'tratado': True
        }
    
    def _limpar_nome(self, nome: str) -> str:
        """Limpeza básica de nome"""
        if not nome:
            return ""
        # Remover excesso de espaços
        return " ".join(nome.split())
    
    def _limpar_marca(self, marca: str) -> str:
        """Limpeza básica de marca"""
        if not marca:
            return "Sem Marca"
        
        # Lista de marcas conhecidas
        marcas_validas = [
            'Angelus', 'Morelli', 'Golgran', 'Orthometric', 'Maquira',
            'Jota', 'Quinelato', 'Talmax', 'Wilcos', 'Fgm', 'Bio-Art'
        ]
        
        # Se for marca válida, retornar
        if any(m.lower() in marca.lower() for m in marcas_validas):
            return marca
            
        return marca
    
    def _limpar_categoria(self, categoria: str) -> str:
        """Limpeza básica de categoria"""
        if not categoria:
            return "Sem Categoria"
        
        # Lista de categorias inválidas
        invalidas = ['promocoes', 'lancamento', 'ofertas', 'novidades']
        
        if categoria.lower() in invalidas:
            return "Diversos"
        
        # Normalizar acentuação
        mapa_acentos = {
            'descartaveis': 'Descartáveis',
            'protese': 'Prótese',
            'biosseguranca': 'Biossegurança',
            'estetica': 'Estética',
            'dentistica': 'Dentística'
        }
        
        cat_lower = categoria.lower()
        for key, value in mapa_acentos.items():
            if key in cat_lower:
                return value
        
        return categoria
