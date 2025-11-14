"""
Gerador de Arquivos Excel com Produtos
Gera arquivos Excel com produtos do produtos_mestre e informações da tabela produtos
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
from datetime import datetime
import pandas as pd
from typing import List, Dict, Optional
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GeradorExcelProdutos:
    """Gerador de arquivos Excel com produtos"""
    
    def __init__(self, db_path: str = "match_crew.db"):
        self.db_path = db_path
        self.conn = None
        
        # Hierarquia de sites preferidos
        self.hierarquia_sites = ['dental_cremer', 'dental_speed']
    
    def conectar(self):
        """Conecta ao banco de dados"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"✅ Conectado ao banco: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao banco: {e}")
            raise
    
    def desconectar(self):
        """Desconecta do banco"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado do banco")
    
    def buscar_produtos_mestre(self, limite: int = 1000, offset: int = 0) -> List[Dict]:
        """Busca produtos da tabela produtos_mestre"""
        query = """
        SELECT 
            id,
            id_match,
            id_bids,
            nome_produto,
            marca,
            categoria,
            subcategoria
        FROM produtos_mestre
        WHERE id_match IS NOT NULL
        ORDER BY id
        LIMIT ? OFFSET ?
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query, (limite, offset))
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append(dict(row))
        
        return produtos
    
    def buscar_produtos_do_match(self, id_bids: str) -> List[Dict]:
        """Busca produtos da tabela produtos baseado nos IDs do match"""
        if not id_bids:
            return []
        
        try:
            ids = json.loads(id_bids)
            if isinstance(ids, list):
                ids = [str(id).strip() for id in ids if id]
            else:
                return []
        except (json.JSONDecodeError, ValueError):
            ids = [id.strip() for id in id_bids.split(',') if id.strip()]
        
        if not ids:
            return []
        
        placeholders = ','.join(['?' for _ in ids])
        
        query = f"""
        SELECT 
            id,
            site,
            nome,
            marca,
            descricao,
            preco,
            preco_promocional,
            url,
            imagem_url
        FROM produtos
        WHERE id IN ({placeholders})
        """
        
        cursor = self.conn.cursor()
        cursor.execute(query, ids)
        
        produtos = []
        for row in cursor.fetchall():
            produtos.append(dict(row))
        
        return produtos
    
    def selecionar_melhor_preco(self, produtos: List[Dict]) -> Optional[Dict]:
        """Seleciona o produto com melhor preço"""
        if not produtos:
            return None
        
        produtos_com_preco = []
        for p in produtos:
            preco = p.get('preco_promocional') or p.get('preco')
            if preco and preco > 0:
                produtos_com_preco.append({
                    **p,
                    'preco_final': preco
                })
        
        if not produtos_com_preco:
            return produtos[0]
        
        produtos_com_preco.sort(key=lambda x: x['preco_final'])
        return produtos_com_preco[0]
    
    def selecionar_url_hierarquica(self, produtos: List[Dict]) -> str:
        """Seleciona URL seguindo hierarquia: dental_cremer > dental_speed > mais barato"""
        if not produtos:
            return ""
        
        # 1. Tentar dental_cremer
        for produto in produtos:
            site = produto.get('site', '').lower()
            if 'cremer' in site:
                url = produto.get('url', '')
                if url:
                    return url
        
        # 2. Tentar dental_speed
        for produto in produtos:
            site = produto.get('site', '').lower()
            if 'speed' in site:
                url = produto.get('url', '')
                if url:
                    return url
        
        # 3. Pegar o mais barato
        mais_barato = self.selecionar_melhor_preco(produtos)
        if mais_barato:
            url = mais_barato.get('url', '')
            if url:
                return url
        
        # 4. Qualquer URL
        for produto in produtos:
            url = produto.get('url', '')
            if url:
                return url
        
        return ""
    
    def processar_produto(self, produto_mestre: Dict) -> Dict:
        """Processa um produto mestre e busca informações complementares"""
        id_bids = produto_mestre.get('id_bids', '')
        produtos_match = self.buscar_produtos_do_match(id_bids)
        
        # Processar preço (menor de todos)
        lista_precos = []
        for produto in produtos_match:
            preco = produto.get('preco_promocional') or produto.get('preco')
            if preco and preco > 0:
                lista_precos.append(preco)
        
        preco_final = min(lista_precos) if lista_precos else ''
        
        # Processar descrição (primeira disponível)
        descricao = ''
        for produto in produtos_match:
            desc = produto.get('descricao', '')
            if desc and len(desc.strip()) > 0:
                descricao = desc.strip()
                break
        
        # Processar URL (sempre dental_cremer)
        company_url = ''
        for produto in produtos_match:
            site = produto.get('site', '').lower()
            if 'cremer' in site:
                url = produto.get('url', '')
                if url:
                    company_url = url
                    break
        
        if not company_url:
            for produto in produtos_match:
                url = produto.get('url', '')
                if url:
                    company_url = url
                    break
        
        # Processar imagem
        imagem = ''
        for produto in produtos_match:
            img = produto.get('imagem_url', '')
            if img:
                imagem = img
                break
        
        # Montar linha do Excel
        return {
            'image': imagem,
            'bid_code': produto_mestre.get('id_match', ''),
            'segment': 'dentista',
            'name': produto_mestre.get('nome_produto', ''),
            'name_commercial': produto_mestre.get('nome_produto', ''),
            'code_manufacturer': '',
            'bar_code': '',
            'code_ean': '',
            'code_anvisa': '',
            'type': '',
            'brand': produto_mestre.get('marca', ''),
            'packaging': '',
            'description': descricao,
            'feature': '',
            'category': produto_mestre.get('categoria', ''),
            'subcategories': produto_mestre.get('subcategoria', ''),
            'supplier': '',
            'price': preco_final,
            'company_code': '1',
            'company_code_company': '1',
            'company_url': company_url
        }
    
    def gerar_excel(self, produtos: List[Dict], numero_arquivo: int, pasta_saida: str = "exports"):
        """Gera arquivo Excel com os produtos"""
        pasta = Path(pasta_saida)
        pasta.mkdir(exist_ok=True)
        
        df = pd.DataFrame(produtos)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = pasta / f"produtos_lote_{numero_arquivo:03d}_{timestamp}.xlsx"
        
        df.to_excel(nome_arquivo, index=False, engine='openpyxl')
        
        logger.info(f"✅ Excel gerado: {nome_arquivo} ({len(produtos)} produtos)")
        
        return nome_arquivo
    
    def executar(self, produtos_por_arquivo: int = 1000, pasta_saida: str = "exports"):
        """Executa o processo completo de geração de arquivos Excel"""
        logger.info("🚀 Iniciando geração de arquivos Excel")
        logger.info(f"📊 Produtos por arquivo: {produtos_por_arquivo}")
        logger.info(f"📁 Pasta de saída: {pasta_saida}")
        
        try:
            self.conectar()
            
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM produtos_mestre WHERE id_match IS NOT NULL")
            total_produtos = cursor.fetchone()[0]
            
            logger.info(f"📈 Total de produtos no produtos_mestre: {total_produtos}")
            
            total_arquivos = (total_produtos + produtos_por_arquivo - 1) // produtos_por_arquivo
            logger.info(f"📄 Serão gerados {total_arquivos} arquivos")
            
            arquivos_gerados = []
            offset = 0
            numero_arquivo = 1
            
            while offset < total_produtos:
                logger.info(f"\n📦 Processando lote {numero_arquivo}/{total_arquivos}...")
                
                produtos_mestre = self.buscar_produtos_mestre(produtos_por_arquivo, offset)
                
                if not produtos_mestre:
                    break
                
                produtos_processados = []
                for i, produto in enumerate(produtos_mestre, 1):
                    if i % 100 == 0:
                        logger.info(f"  Processando produto {i}/{len(produtos_mestre)}...")
                    
                    try:
                        produto_excel = self.processar_produto(produto)
                        produtos_processados.append(produto_excel)
                    except Exception as e:
                        logger.error(f"  ⚠️  Erro ao processar produto {produto.get('id')}: {e}")
                        continue
                
                arquivo = self.gerar_excel(produtos_processados, numero_arquivo, pasta_saida)
                arquivos_gerados.append(arquivo)
                
                offset += produtos_por_arquivo
                numero_arquivo += 1
            
            logger.info(f"\n🎉 Processo concluído!")
            logger.info(f"✅ {len(arquivos_gerados)} arquivos gerados")
            logger.info(f"📁 Localização: {Path(pasta_saida).absolute()}")
            
            return arquivos_gerados
            
        except Exception as e:
            logger.error(f"❌ Erro durante execução: {e}")
            raise
        finally:
            self.desconectar()


def main():
    """Função principal"""
    print("="*70)
    print("📊 GERADOR DE EXCEL - PRODUTOS MESTRE")
    print("="*70)
    
    print("\n📝 Configurações:")
    print("  • Produtos por arquivo: 1000")
    print("  • Hierarquia de sites: dental_cremer > dental_speed > mais barato")
    print("  • Segment: todos 'dentista'")
    print("  • Company code: todos '1'")
    
    print("\n🔄 Iniciando processamento...\n")
    
    try:
        gerador = GeradorExcelProdutos()
        arquivos = gerador.executar(produtos_por_arquivo=1000, pasta_saida="exports")
        
        print("\n" + "="*70)
        print("✅ SUCESSO!")
        print("="*70)
        print(f"\n📄 Arquivos gerados: {len(arquivos)}")
        for arquivo in arquivos:
            print(f"  • {arquivo.name}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
