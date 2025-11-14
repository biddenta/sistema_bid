"""
Análise de Precisão por Categoria - Base para Fase 2
Objetivo: Calcular a precisão de matching por categoria usando feedbacks
Resultado: Mapa de thresholds dinâmicos
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
from collections import defaultdict
from datetime import datetime
import json


def conectar_db():
    """Conecta ao banco de dados"""
    return sqlite3.connect('match_crew.db')


def analisar_precisao_por_categoria():
    """Analisa precisão de matching por categoria baseado em feedbacks"""
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 ANÁLISE DE PRECISÃO POR CATEGORIA - FASE 2")
    print("="*80)
    print("Objetivo: Identificar categorias que precisam de thresholds diferentes\n")
    
    # 1. ANÁLISE DE FEEDBACKS EXISTENTES
    print("-"*80)
    print("1️⃣  ANÁLISE DE FEEDBACKS")
    print("-"*80)
    
    cursor.execute("""
        SELECT COUNT(*) FROM feedbacks
    """)
    total_feedbacks = cursor.fetchone()[0]
    
    if total_feedbacks == 0:
        print("⚠️  Nenhum feedback encontrado no banco!")
        print("   Vou usar análise baseada em score_match dos grupos\n")
        usar_scores = True
    else:
        print(f"✅ {total_feedbacks} feedbacks encontrados")
        usar_scores = False
        
        # Análise de feedbacks por categoria
        cursor.execute("""
            SELECT 
                pm.categoria,
                COUNT(*) as total_feedbacks,
                SUM(CASE WHEN f.is_correto = 1 THEN 1 ELSE 0 END) as corretos,
                SUM(CASE WHEN f.is_correto = 0 THEN 1 ELSE 0 END) as incorretos,
                AVG(CASE WHEN f.confianca IS NOT NULL THEN f.confianca ELSE 0 END) as avg_confianca
            FROM feedbacks f
            JOIN produtos_mestre pm ON f.match_id = pm.id
            WHERE pm.categoria IS NOT NULL
            GROUP BY pm.categoria
            ORDER BY total_feedbacks DESC
        """)
        
        feedbacks_por_cat = cursor.fetchall()
        
        if feedbacks_por_cat:
            print(f"\n{'Categoria':<30} | {'Total':<8} | {'Corretos':<10} | {'Incorretos':<10} | {'Precisão':<10}")
            print("-" * 85)
            
            for categoria, total, corretos, incorretos, avg_conf in feedbacks_por_cat[:10]:
                precisao = (corretos / total * 100) if total > 0 else 0
                print(f"{categoria:<30} | {total:>6} | {corretos:>8} | {incorretos:>10} | {precisao:>8.1f}%")
    
    # 2. ANÁLISE BASEADA EM SCORES (MÉTODO PRINCIPAL)
    print("\n" + "-"*80)
    print("2️⃣  ANÁLISE BASEADA EM SCORE_MATCH (MÉTODO DETERMINÍSTICO)")
    print("-"*80)
    print("(Usado para calcular thresholds recomendados)\n")
    
    cursor.execute("""
        SELECT 
            categoria,
            COUNT(*) as total_grupos,
            AVG(score_match) as avg_score,
            MIN(score_match) as min_score,
            MAX(score_match) as max_score,
            AVG(total_sites) as avg_sites,
            AVG(total_produtos) as avg_produtos
        FROM produtos_mestre
        WHERE categoria IS NOT NULL 
          AND score_match IS NOT NULL
          AND total_sites > 1
        GROUP BY categoria
        HAVING COUNT(*) >= 10
        ORDER BY total_grupos DESC
    """)
    
    categorias_stats = cursor.fetchall()
    
    print(f"{'Categoria':<30} | {'Grupos':<8} | {'Avg Score':<12} | {'Min-Max':<15} | {'Avg Sites':<10}")
    print("-" * 90)
    
    thresholds_recomendados = {}
    
    for categoria, total, avg_score, min_score, max_score, avg_sites, avg_prods in categorias_stats:
        print(f"{categoria:<30} | {total:>6} | {avg_score:>10.3f} | {min_score:.2f}-{max_score:.2f} | {avg_sites:>8.2f}")
        
        # Calcular threshold recomendado baseado no avg_score
        if avg_score >= 0.95:
            threshold = 0.80  # Rigoroso
        elif avg_score >= 0.90:
            threshold = 0.77  # Padrão alto
        elif avg_score >= 0.85:
            threshold = 0.75  # Padrão
        elif avg_score >= 0.80:
            threshold = 0.72  # Permissivo
        else:
            threshold = 0.70  # Muito permissivo
        
        thresholds_recomendados[categoria] = {
            'threshold': threshold,
            'avg_score': avg_score,
            'total_grupos': total,
            'avg_sites': avg_sites
        }
    
    # 3. CATEGORIAS PROBLEMÁTICAS
    print("\n" + "-"*80)
    print("3️⃣  CATEGORIAS QUE PRECISAM DE ATENÇÃO")
    print("-"*80)
    
    # Categorias com poucos matches (baixa cobertura)
    cursor.execute("""
        SELECT 
            p.categoria,
            COUNT(DISTINCT p.id) as total_produtos,
            COUNT(DISTINCT CASE WHEN pm.id IS NOT NULL THEN p.id END) as produtos_matchados,
            COUNT(DISTINCT pm.id) as grupos
        FROM produtos p
        LEFT JOIN produtos_mestre pm ON (
            p.categoria = pm.categoria 
            AND p.id IN (
                SELECT CAST(value AS INTEGER)
                FROM json_each(pm.id_bids)
            )
        )
        WHERE p.categoria IS NOT NULL
        GROUP BY p.categoria
        HAVING COUNT(DISTINCT p.id) >= 50
        ORDER BY (COUNT(DISTINCT CASE WHEN pm.id IS NOT NULL THEN p.id END) * 1.0 / COUNT(DISTINCT p.id)) ASC
        LIMIT 10
    """)
    
    categorias_problema = cursor.fetchall()
    
    print(f"\n{'Categoria':<30} | {'Total Prods':<12} | {'Matchados':<12} | {'Taxa Match':<12}")
    print("-" * 75)
    
    for categoria, total_prods, matchados, grupos in categorias_problema:
        taxa = (matchados / total_prods * 100) if total_prods > 0 else 0
        emoji = "❌" if taxa < 15 else "⚠️" if taxa < 25 else "📌"
        print(f"{emoji} {categoria:<27} | {total_prods:>10} | {matchados:>10} | {taxa:>10.1f}%")
        
        # Se categoria tem baixa taxa de match, recomendar threshold mais baixo
        if categoria not in thresholds_recomendados:
            if taxa < 15:
                thresholds_recomendados[categoria] = {
                    'threshold': 0.70,
                    'avg_score': 0.0,
                    'total_grupos': grupos,
                    'razao': 'Baixa cobertura (<15%)'
                }
            elif taxa < 25:
                thresholds_recomendados[categoria] = {
                    'threshold': 0.72,
                    'avg_score': 0.0,
                    'total_grupos': grupos,
                    'razao': 'Cobertura média (15-25%)'
                }
    
    # 4. MAPA DE THRESHOLDS DINÂMICOS
    print("\n" + "="*80)
    print("4️⃣  MAPA DE THRESHOLDS DINÂMICOS RECOMENDADOS")
    print("="*80)
    
    # Agrupar por threshold
    por_threshold = defaultdict(list)
    for cat, info in thresholds_recomendados.items():
        por_threshold[info['threshold']].append((cat, info))
    
    print()
    for threshold in sorted(por_threshold.keys(), reverse=True):
        categorias = por_threshold[threshold]
        print(f"\n📊 THRESHOLD {threshold:.2f} ({len(categorias)} categorias):")
        print("-" * 80)
        
        if threshold >= 0.78:
            nivel = "RIGOROSO"
            descricao = "Categorias com alta precisão, exigem match muito similar"
        elif threshold >= 0.74:
            nivel = "PADRÃO"
            descricao = "Categorias com boa precisão, threshold equilibrado"
        else:
            nivel = "PERMISSIVO"
            descricao = "Categorias com baixa cobertura, precisam de mais flexibilidade"
        
        print(f"Nível: {nivel} - {descricao}\n")
        
        for cat, info in sorted(categorias, key=lambda x: x[1]['total_grupos'], reverse=True)[:10]:
            grupos = info['total_grupos']
            avg_score = info['avg_score']
            razao = info.get('razao', f"Score médio: {avg_score:.3f}")
            print(f"   • {cat:<35} ({grupos:>4} grupos) - {razao}")
        
        if len(categorias) > 10:
            print(f"   ... e mais {len(categorias)-10} categorias")
    
    # 5. GERAR ARQUIVO DE CONFIGURAÇÃO
    print("\n" + "-"*80)
    print("5️⃣  GERANDO ARQUIVO DE CONFIGURAÇÃO")
    print("-"*80)
    
    config = {
        'threshold_padrao': 0.75,
        'thresholds_por_categoria': {},
        'metadata': {
            'data_geracao': datetime.now().isoformat(),
            'total_categorias': len(thresholds_recomendados),
            'baseado_em': 'score_match' if usar_scores else 'feedbacks'
        }
    }
    
    for cat, info in thresholds_recomendados.items():
        config['thresholds_por_categoria'][cat] = {
            'threshold': info['threshold'],
            'grupos_existentes': info['total_grupos'],
            'score_medio': round(info['avg_score'], 3) if info['avg_score'] > 0 else None,
            'sites_medio': round(info.get('avg_sites', 0), 2)
        }
    
    # Salvar configuração
    config_path = 'shared/config/thresholds_dinamicos.json'
    import os
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Configuração salva em: {config_path}")
    print(f"   Total de categorias mapeadas: {len(thresholds_recomendados)}")
    
    # 6. IMPACTO ESTIMADO
    print("\n" + "="*80)
    print("6️⃣  IMPACTO ESTIMADO DA FASE 2")
    print("="*80)
    
    # Contar produtos em categorias que terão threshold mais baixo
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT p.id) as total_produtos,
            p.categoria
        FROM produtos p
        LEFT JOIN produtos_mestre pm ON p.id IN (
            SELECT CAST(value AS INTEGER)
            FROM json_each(pm.id_bids)
        )
        WHERE pm.id IS NULL
          AND p.categoria IN ({})
        GROUP BY p.categoria
    """.format(','.join(['?' for _ in thresholds_recomendados.keys()])), 
    list(thresholds_recomendados.keys()))
    
    produtos_sem_match = cursor.fetchall()
    
    total_sem_match = sum([p[0] for p in produtos_sem_match])
    
    # Estimar ganho
    categorias_permissivas = [cat for cat, info in thresholds_recomendados.items() if info['threshold'] <= 0.72]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id) 
        FROM produtos 
        WHERE categoria IN ({})
    """.format(','.join(['?' for _ in categorias_permissivas])), 
    categorias_permissivas)
    
    produtos_em_cats_permissivas = cursor.fetchone()[0] if categorias_permissivas else 0
    
    ganho_estimado = int(produtos_em_cats_permissivas * 0.25)  # 25% de ganho estimado
    
    print(f"\n📊 Estatísticas:")
    print(f"   • Produtos sem match: {total_sem_match:,}")
    print(f"   • Categorias com threshold permissivo: {len(categorias_permissivas)}")
    print(f"   • Produtos nessas categorias: {produtos_em_cats_permissivas:,}")
    print(f"   • Ganho estimado: {ganho_estimado:,} produtos (+{ganho_estimado/45241*100:.1f}%)")
    
    print("\n💡 Próximo passo:")
    print("   Modificar algoritmo de matching para usar thresholds dinâmicos")
    
    conn.close()
    
    return {
        'total_categorias': len(thresholds_recomendados),
        'config_path': config_path,
        'ganho_estimado': ganho_estimado
    }


if __name__ == "__main__":
    try:
        print("Iniciando análise de precisão por categoria...")
        resultado = analisar_precisao_por_categoria()
        print("\n✅ Análise concluída!")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ Erro durante análise: {e}")
        import traceback
        traceback.print_exc()
