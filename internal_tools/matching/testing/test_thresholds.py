"""
Teste de Thresholds Dinâmicos (Fase 2)
Verifica se os thresholds estão sendo aplicados corretamente
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
import json
from collections import defaultdict


def testar_fase2():
    """Testa configuração e aplicação de thresholds dinâmicos"""
    print("\n" + "="*80)
    print("🧪 TESTE - FASE 2: THRESHOLDS DINÂMICOS")
    print("="*80)
    
    # 1. Carregar configuração
    print("\n1️⃣  Carregando configuração de thresholds...")
    config_path = Path('shared/config/thresholds_dinamicos.json')
    
    if not config_path.exists():
        print("❌ Arquivo de configuração não encontrado!")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    thresholds_map = config.get('thresholds_por_categoria', {})
    threshold_padrao = config.get('threshold_padrao', 0.75)
    
    print(f"✅ Configuração carregada:")
    print(f"   • Threshold padrão: {threshold_padrao}")
    print(f"   • Categorias mapeadas: {len(thresholds_map)}")
    
    # 2. Análise dos thresholds
    print("\n2️⃣  Distribuição de thresholds:")
    por_threshold = defaultdict(list)
    for cat, info in thresholds_map.items():
        threshold = info['threshold']
        por_threshold[threshold].append(cat)
    
    for threshold in sorted(por_threshold.keys(), reverse=True):
        categorias = por_threshold[threshold]
        print(f"   • {threshold:.2f}: {len(categorias)} categorias")
        if threshold != threshold_padrao:
            print(f"      Exemplos: {', '.join(categorias[:3])}")
    
    # 3. Testar aplicação em produtos reais
    print("\n3️⃣  Testando aplicação em produtos reais...")
    conn = sqlite3.connect('match_crew.db')
    cursor = conn.cursor()
    
    # Buscar produtos de categorias com thresholds diferentes
    categorias_teste = []
    for threshold in sorted(set(por_threshold.keys()), reverse=True):
        if por_threshold[threshold]:
            cat = por_threshold[threshold][0]
            categorias_teste.append((cat, threshold))
            if len(categorias_teste) >= 5:
                break
    
    print(f"\n   Categorias de teste ({len(categorias_teste)}):")
    for cat, threshold in categorias_teste:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM produtos 
            WHERE categoria = ?
        """, (cat,))
        total_produtos = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT pm.id)
            FROM produtos_mestre pm
            WHERE pm.categoria = ?
        """, (cat,))
        total_grupos = cursor.fetchone()[0]
        
        taxa_match = (total_grupos * 2 / total_produtos * 100) if total_produtos > 0 else 0
        
        emoji = "🔒" if threshold >= 0.78 else "⚖️" if threshold >= 0.74 else "🔓"
        print(f"   {emoji} {cat[:40]:<40} | Threshold: {threshold:.2f} | Produtos: {total_produtos:>4} | Grupos: {total_grupos:>4} | Taxa: {taxa_match:.1f}%")
    
    conn.close()
    
    # 4. Análise de impacto
    print("\n4️⃣  Análise de impacto:")
    
    categorias_permissivas = [cat for cat, info in thresholds_map.items() if info['threshold'] < threshold_padrao]
    categorias_rigorosas = [cat for cat, info in thresholds_map.items() if info['threshold'] > threshold_padrao]
    categorias_padrao = [cat for cat, info in thresholds_map.items() if info['threshold'] == threshold_padrao]
    
    print(f"   • Categorias RIGOROSAS (threshold > {threshold_padrao}): {len(categorias_rigorosas)}")
    print(f"   • Categorias PADRÃO (threshold = {threshold_padrao}): {len(categorias_padrao)}")
    print(f"   • Categorias PERMISSIVAS (threshold < {threshold_padrao}): {len(categorias_permissivas)}")
    
    if categorias_permissivas:
        print(f"\n   📈 Categorias que ganharão mais matches:")
        for cat in categorias_permissivas[:5]:
            info = thresholds_map[cat]
            print(f"      • {cat[:35]:<35} (threshold: {info['threshold']:.2f}, grupos atuais: {info['grupos_existentes']})")
    
    print("\n" + "="*80)
    print("✅ Teste concluído!")
    print("="*80)


if __name__ == "__main__":
    try:
        testar_fase2()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
