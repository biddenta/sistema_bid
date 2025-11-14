import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class HierarchiaCategorizacao:
    """Gerencia a hierarquia de categorização de produtos"""
    
    def __init__(self, json_path: str = None):
        if json_path is None:
            # Usa o arquivo na pasta atual
            json_path = Path(__file__).parent / "hierarquia_categorizacao.json"
        self.json_path = Path(json_path)
        self.hierarquia = self._carregar_hierarquia()
        self.mapeamento_rapido = self._criar_mapeamento()
    
    def _carregar_hierarquia(self) -> Dict:
        """Carrega hierarquia do arquivo JSON"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Arquivo de hierarquia não encontrado: {self.json_path}")
        
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _criar_mapeamento(self) -> Dict[str, Tuple[str, str, str]]:
        """
        Cria mapeamento rápido: subcategoria -> (segmento, categoria, subcategoria)
        """
        mapeamento = {}
        
        for segmento, categorias in self.hierarquia.items():
            for categoria, subcategorias in categorias.items():
                for subcategoria in subcategorias:
                    # Remove espaços extras
                    subcat_clean = subcategoria.strip()
                    mapeamento[subcat_clean.lower()] = (segmento, categoria, subcat_clean)
        
        return mapeamento
    
    def buscar_por_subcategoria(self, subcategoria: str) -> Optional[Tuple[str, str, str]]:
        """
        Busca segmento e categoria pela subcategoria
        Retorna: (segmento, categoria, subcategoria) ou None
        """
        return self.mapeamento_rapido.get(subcategoria.lower())
    
    def listar_segmentos(self) -> List[str]:
        """Lista todos os segmentos disponíveis"""
        return list(self.hierarquia.keys())
    
    def listar_categorias(self, segmento: str) -> List[str]:
        """Lista todas as categorias de um segmento"""
        return list(self.hierarquia.get(segmento, {}).keys())
    
    def listar_subcategorias(self, segmento: str, categoria: str) -> List[str]:
        """Lista todas as subcategorias de uma categoria"""
        return self.hierarquia.get(segmento, {}).get(categoria, [])
    
    def validar_caminho(self, segmento: str, categoria: str, subcategoria: str) -> bool:
        """Valida se um caminho de categorização existe na hierarquia"""
        if segmento not in self.hierarquia:
            return False
        if categoria not in self.hierarquia[segmento]:
            return False
        if subcategoria not in self.hierarquia[segmento][categoria]:
            return False
        return True
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas da hierarquia"""
        total_subcategorias = 0
        detalhes = {}
        
        for segmento, categorias in self.hierarquia.items():
            num_categorias = len(categorias)
            num_subcats = sum(len(subcats) for subcats in categorias.values())
            total_subcategorias += num_subcats
            
            detalhes[segmento] = {
                'categorias': num_categorias,
                'subcategorias': num_subcats
            }
        
        return {
            'total_segmentos': len(self.hierarquia),
            'total_categorias': sum(d['categorias'] for d in detalhes.values()),
            'total_subcategorias': total_subcategorias,
            'detalhes_por_segmento': detalhes
        }


class BancoConhecimento:
    """Gerencia o banco de conhecimento de produtos já categorizados"""
    
    def __init__(self, excel_path: str = None):
        if excel_path is None:
            # Usa o arquivo na pasta atual
            excel_path = Path(__file__).parent / "Cadastro Bid Dental_rev13.xlsx"
        self.excel_path = Path(excel_path)
        self.df = self._carregar_excel()
        self.exemplos_categorizados = self._processar_exemplos()
    
    def _carregar_excel(self) -> pd.DataFrame:
        """Carrega dados do Excel"""
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Arquivo Excel não encontrado: {self.excel_path}")
        
        # Tenta carregar o arquivo (linha 1 tem os cabeçalhos)
        try:
            df = pd.read_excel(self.excel_path, header=1)
            # Remove linhas vazias
            df = df.dropna(how='all')
            print(f"✅ Excel carregado: {len(df)} registros")
            return df
        except Exception as e:
            raise Exception(f"Erro ao carregar Excel: {e}")
    
    def _processar_exemplos(self) -> pd.DataFrame:
        """
        Processa e filtra apenas exemplos que têm categorização completa
        """
        # Identifica colunas relevantes (podem variar dependendo do Excel)
        colunas_possiveis = {
            'nome': ['nome', 'produto', 'nome_produto', 'descricao'],
            'segmento': ['segmento'],
            'categoria': ['categoria'],
            'subcategoria': ['subcategoria', 'sub_categoria']
        }
        
        # Mapeia colunas do DataFrame
        mapeamento_colunas = {}
        for campo, possiveis in colunas_possiveis.items():
            for col_possivel in possiveis:
                cols_encontradas = [c for c in self.df.columns if isinstance(c, str) and col_possivel.lower() in c.lower()]
                if cols_encontradas:
                    mapeamento_colunas[campo] = cols_encontradas[0]
                    break
        
        print(f"📋 Colunas identificadas: {mapeamento_colunas}")
        
        # Filtra apenas registros com categorização completa
        if 'segmento' in mapeamento_colunas and 'categoria' in mapeamento_colunas:
            df_filtrado = self.df[
                self.df[mapeamento_colunas['segmento']].notna() &
                self.df[mapeamento_colunas['categoria']].notna()
            ].copy()
            
            print(f"✅ Exemplos com categorização: {len(df_filtrado)} de {len(self.df)}")
            return df_filtrado
        else:
            print("⚠️ Colunas de categorização não encontradas completamente")
            return self.df
    
    def buscar_similares(self, nome_produto: str, top_n: int = 5) -> List[Dict]:
        """
        Busca produtos similares no banco de conhecimento
        """
        if self.exemplos_categorizados.empty:
            return []
        
        # Identifica coluna de nome
        col_nome = None
        for col in self.exemplos_categorizados.columns:
            if any(x in col.lower() for x in ['nome', 'produto', 'descricao']):
                col_nome = col
                break
        
        if not col_nome:
            return []
        
        # Busca por palavras-chave simples
        palavras = nome_produto.lower().split()
        
        resultados = []
        for idx, row in self.exemplos_categorizados.iterrows():
            nome_ref = str(row[col_nome]).lower()
            
            # Conta quantas palavras coincidem
            score = sum(1 for palavra in palavras if palavra in nome_ref)
            
            if score > 0:
                resultados.append({
                    'nome': row[col_nome],
                    'segmento': row.get('segmento', row.get('Segmento', '')),
                    'categoria': row.get('categoria', row.get('Categoria', '')),
                    'subcategoria': row.get('subcategoria', row.get('Subcategoria', '')),
                    'score': score
                })
        
        # Ordena por score e retorna top N
        resultados.sort(key=lambda x: x['score'], reverse=True)
        return resultados[:top_n]
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas do banco de conhecimento"""
        stats = {
            'total_exemplos': len(self.df),
            'total_produtos': len(self.df),
            'produtos_categorizados': len(self.exemplos_categorizados),
            'percentual_categorizados': (len(self.exemplos_categorizados) / len(self.df) * 100) if len(self.df) > 0 else 0
        }
        
        # Conta por segmento (se disponível)
        colunas_str = [c for c in self.exemplos_categorizados.columns if isinstance(c, str)]
        col_seg = None
        for possivel in ['segmento', 'Segmento']:
            if possivel in colunas_str:
                col_seg = possivel
                break
        
        if col_seg:
            stats['segmentos'] = self.exemplos_categorizados[col_seg].value_counts().to_dict()
        else:
            stats['segmentos'] = {}
        
        return stats


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação"""
    import unicodedata
    
    if not texto or pd.isna(texto):
        return ""
    
    # Remove acentos
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    
    # Lowercase e remove espaços extras
    return texto.lower().strip()


def extrair_palavras_chave(texto: str) -> List[str]:
    """Extrai palavras-chave relevantes de um texto"""
    import re
    
    # Remove pontuação e números
    texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
    
    # Split em palavras
    palavras = texto_limpo.split()
    
    # Remove stopwords comuns
    stopwords = {
        'de', 'da', 'do', 'para', 'com', 'em', 'o', 'a', 'os', 'as',
        'um', 'uma', 'e', 'ou', 'kit', 'com', 'sem', 'pacote', 'unidade'
    }
    
    palavras_filtradas = [p for p in palavras if p not in stopwords and len(p) > 2]
    
    return palavras_filtradas


if __name__ == "__main__":
    # Teste rápido
    print("\n" + "=" * 70)
    print("TESTE DO MÓDULO DE DADOS")
    print("=" * 70)
    
    try:
        # Testa hierarquia
        print("\n📋 Testando Hierarquia...")
        hierarquia = HierarchiaCategorizacao()
        stats = hierarquia.obter_estatisticas()
        
        print(f"   Segmentos: {stats['total_segmentos']}")
        print(f"   Categorias: {stats['total_categorias']}")
        print(f"   Subcategorias: {stats['total_subcategorias']}")
        
        # Testa banco de conhecimento
        print("\n📚 Testando Banco de Conhecimento...")
        banco = BancoConhecimento()
        stats_banco = banco.obter_estatisticas()
        
        print(f"   Total de produtos: {stats_banco['total_produtos']}")
        print(f"   Produtos categorizados: {stats_banco['produtos_categorizados']}")
        print(f"   Percentual: {stats_banco['percentual_categorizados']:.1f}%")
        
        print("\n✅ Módulo funcionando corretamente!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
