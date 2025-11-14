import sqlite3
import re
import json
import pandas as pd
from typing import Tuple, Dict
from collections import defaultdict, Counter
from pathlib import Path


class CategorizadorHibridoMemoria:
    """
    Categorizador que PRIORIZA as categorizações manuais
    """
    
    def __init__(self, excel_path: str = None, json_path: str = None):
        """Inicializa o categorizador com memória manual"""
        
        # Paths
        base_dir = Path(__file__).parent
        self.excel_path = excel_path or base_dir / "Cadastro Bid Dental_rev13.xlsx"
        self.json_path = json_path or base_dir / "hierarquia_categorizacao.json"
        
        print("🚀 Inicializando Categorizador Híbrido com Memória Manual...")
        
        # 1. Carregar hierarquia JSON
        print("   📋 Carregando hierarquia de categorias...")
        self.hierarquia = self._carregar_hierarquia()
        print(f"   ✅ {len(self.hierarquia)} segmentos carregados")
        
        # 2. Carregar categorizações manuais do Excel
        print("   📊 Carregando categorizações manuais...")
        self.memoria_manual = self._carregar_memoria_manual()
        print(f"   ✅ {len(self.memoria_manual)} produtos manuais carregados")
        
        # 3. Criar índice de padrões das categorizações manuais
        print("   🧠 Aprendendo padrões das categorizações manuais...")
        self.padroes_aprendidos = self._aprender_padroes_manuais()
        print(f"   ✅ {len(self.padroes_aprendidos)} padrões aprendidos")
        
        # 4. Carregar regras do categorizador inteligente (fallback)
        print("   🔧 Carregando regras inteligentes como fallback...")
        self._carregar_regras_inteligentes()
        print("   ✅ Regras carregadas")
        
        print("✅ Categorizador Híbrido pronto!\n")
    
    def _carregar_hierarquia(self) -> Dict:
        """Carrega hierarquia do JSON"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _carregar_memoria_manual(self) -> Dict:
        """Carrega categorizações manuais do Excel"""
        
        # Ler Excel
        df = pd.read_excel(self.excel_path, skiprows=1)
        
        # Renomear colunas
        colunas = {
            'Unnamed: 1': 'codigo',
            'Unnamed: 2': 'segmento',
            'Unnamed: 3': 'categoria',
            'Unnamed: 4': 'subcategoria',
            'Unnamed: 5': 'tipo1',
            'Unnamed: 6': 'nome_produto',
            'Unnamed: 7': 'marca'
        }
        
        # Primeira linha tem headers, remove
        df = df.iloc[1:]
        
        for old, new in colunas.items():
            if old in df.columns:
                df.rename(columns={old: new}, inplace=True)
        
        # Filtrar válidos
        df_valido = df[df['nome_produto'].notna() & df['segmento'].notna()].copy()
        
        # Criar dicionário de lookup
        memoria = {}
        
        for _, row in df_valido.iterrows():
            nome = str(row['nome_produto']).lower().strip()
            if nome and nome != 'nan':
                # Lookup exato
                memoria[nome] = {
                    'segmento': str(row['segmento']),
                    'categoria': str(row['categoria']),
                    'subcategoria': str(row['subcategoria']),
                    'confianca': 1.0,  # 100% de confiança (manual)
                    'fonte': 'manual'
                }
                
                # Lookup sem acentos
                nome_sem_acento = self._normalizar(nome)
                if nome_sem_acento != nome:
                    memoria[nome_sem_acento] = memoria[nome].copy()
                    memoria[nome_sem_acento]['confianca'] = 0.98
        
        return memoria
    
    def _normalizar(self, texto: str) -> str:
        """Remove acentos e normaliza texto"""
        if not texto:
            return ""
        
        texto = texto.lower()
        
        # Remove acentos
        replacements = {
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
            'é': 'e', 'ê': 'e', 'è': 'e',
            'í': 'i', 'î': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'û': 'u',
            'ç': 'c'
        }
        
        for old, new in replacements.items():
            texto = texto.replace(old, new)
        
        return texto.strip()
    
    def _aprender_padroes_manuais(self) -> Dict:
        """Aprende padrões das categorizações manuais"""
        
        padroes = defaultdict(lambda: defaultdict(list))
        
        for nome, info in self.memoria_manual.items():
            # Extrair palavras-chave
            palavras = re.findall(r'\b\w{3,}\b', nome)
            
            chave_cat = f"{info['segmento']}|{info['categoria']}|{info['subcategoria']}"
            
            for palavra in palavras:
                if palavra not in ['com', 'para', 'unidades', 'kit']:
                    padroes[palavra][chave_cat].append(nome)
        
        # Calcular scores
        padroes_score = {}
        for palavra, categorias in padroes.items():
            total = sum(len(prods) for prods in categorias.values())
            if total >= 3:  # Mínimo 3 ocorrências
                melhor_cat = max(categorias.items(), key=lambda x: len(x[1]))
                score = len(melhor_cat[1]) / total
                if score >= 0.6:  # 60% de confiança
                    seg, cat, subcat = melhor_cat[0].split('|')
                    padroes_score[palavra] = {
                        'segmento': seg,
                        'categoria': cat,
                        'subcategoria': subcat,
                        'confianca': score,
                        'ocorrencias': len(melhor_cat[1])
                    }
        
        return padroes_score
    
    def _carregar_regras_inteligentes(self):
        """Carrega regras do categorizador inteligente como fallback"""
        # Importa o categorizador anterior
        try:
            from categorizador_inteligente_final import CategorizadorInteligenteFinal
            self.categorizador_fallback = CategorizadorInteligenteFinal()
        except Exception as e:
            print(f"   ⚠️  Não foi possível carregar fallback: {e}")
            self.categorizador_fallback = None
    
    def categorizar(self, nome: str, marca: str = '') -> Tuple[str, str, str, float]:
        """
        Categoriza um produto usando a hierarquia de prioridades:
        1. LOOKUP EXATO na memória manual (100% confiança)
        2. PADRÕES APRENDIDOS da memória manual (60-90% confiança)
        3. REGRAS INTELIGENTES (fallback)
        
        Returns: (segmento, categoria, subcategoria, confianca)
        """
        
        if not nome:
            return ('Dentista', 'Outros', 'Não Classificado', 0.0)
        
        nome_lower = nome.lower().strip()
        nome_norm = self._normalizar(nome_lower)
        
        # ==========================================
        # PRIORIDADE 1: LOOKUP EXATO (manual)
        # ==========================================
        if nome_lower in self.memoria_manual:
            info = self.memoria_manual[nome_lower]
            return (
                info['segmento'],
                info['categoria'],
                info['subcategoria'],
                info['confianca']
            )
        
        # Lookup normalizado
        if nome_norm in self.memoria_manual:
            info = self.memoria_manual[nome_norm]
            return (
                info['segmento'],
                info['categoria'],
                info['subcategoria'],
                info['confianca'] * 0.98  # Pequena penalidade por normalização
            )
        
        # ==========================================
        # PRIORIDADE 2: PADRÕES APRENDIDOS
        # ==========================================
        palavras = re.findall(r'\b\w{3,}\b', nome_norm)
        
        matches_padroes = []
        for palavra in palavras:
            if palavra in self.padroes_aprendidos:
                padrao = self.padroes_aprendidos[palavra]
                matches_padroes.append((padrao, padrao['confianca']))
        
        if matches_padroes:
            # Pegar o de maior confiança
            melhor_padrao, conf = max(matches_padroes, key=lambda x: x[1])
            return (
                melhor_padrao['segmento'],
                melhor_padrao['categoria'],
                melhor_padrao['subcategoria'],
                conf * 0.85  # Penalidade por ser padrão (não exato)
            )
        
        # ==========================================
        # PRIORIDADE 3: FALLBACK (regras inteligentes)
        # ==========================================
        if self.categorizador_fallback:
            return self.categorizador_fallback.categorizar(nome, marca)
        
        # Último recurso
        return ('Dentista', 'Outros', 'Não Classificado', 0.0)


# ===================================
# TESTE
# ===================================
if __name__ == "__main__":
    categorizador = CategorizadorHibridoMemoria()
    
    casos_teste = [
        ("Abaixador de Língua Bruenings", ""),  # No Excel
        ("Resina Filtek Z350", "3M"),  # Não no Excel, mas tem padrão
        ("Broca Carbide FG 1014", "KG"),  # Não no Excel
    ]
    
    print("="*80)
    print("TESTE DO CATEGORIZADOR HÍBRIDO COM MEMÓRIA")
    print("="*80)
    
    for nome, marca in casos_teste:
        seg, cat, subcat, conf = categorizador.categorizar(nome, marca)
        print(f"\n{nome}")
        print(f"  → {seg} > {cat} > {subcat}")
        print(f"  → Confiança: {conf*100:.1f}%")
