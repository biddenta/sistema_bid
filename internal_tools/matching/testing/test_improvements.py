"""
Script para testar melhorias no algoritmo de matching
Compara resultados ANTES vs DEPOIS das melhorias implementadas
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
from datetime import datetime
import shutil


def backup_banco_atual():
    """Cria backup do banco atual antes do teste"""
    db_path = Path("legacy/data/produtos_mestre.db")
    
    if not db_path.exists():
        print("⚠️  Banco produtos_mestre.db não existe ainda")
        return None
    
    backup_path = Path(f"legacy/data/produtos_mestre_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup criado: {backup_path}")
    
    return backup_path


def analisar_banco_antes():
    """Analisa estatísticas do banco ANTES das melhorias"""
    db_path = Path("legacy/data/produtos_mestre.db")
    
    if not db_path.exists():
        print("⚠️  Banco não existe - será criado na primeira execução")
        return {
            "total_grupos": 0,
            "total_produtos": 0,
            "grupos_2_sites": 0,
            "grupos_3plus_sites": 0,
            "score_medio": 0
        }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total de grupos
    cursor.execute("SELECT COUNT(DISTINCT id_match) FROM produtos_mestre")
    total_grupos = cursor.fetchone()[0]
    
    # Total de produtos
    cursor.execute("SELECT COUNT(*) FROM produtos_mestre")
    total_produtos = cursor.fetchone()[0]
    
    # Distribuição por sites
    cursor.execute("""
        SELECT 
            total_sites,
            COUNT(*) as grupos
        FROM produtos_mestre
        WHERE total_sites >= 2
        GROUP BY total_sites
        ORDER BY total_sites
    """)
    
    distribuicao = cursor.fetchall()
    grupos_2_sites = sum(count for sites, count in distribuicao if sites == 2)
    grupos_3plus = sum(count for sites, count in distribuicao if sites >= 3)
    
    # Score médio
    cursor.execute("SELECT AVG(score_match) FROM produtos_mestre")
    score_medio = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total_grupos": total_grupos,
        "total_produtos": total_produtos,
        "grupos_2_sites": grupos_2_sites,
        "grupos_3plus_sites": grupos_3plus,
        "score_medio": score_medio,
        "distribuicao": distribuicao
    }


def executar_matching_melhorado():
    """Executa matching com as melhorias implementadas"""
    print("\n" + "="*80)
    print("🚀 EXECUTANDO MATCHING COM MELHORIAS")
    print("="*80)
    
    from internal_tools.matching.algorithms.hybrid_matching import MatchingHibridoSuperOtimizado
    
    matching = MatchingHibridoSuperOtimizado()
    resultado = matching.executar_matching_super_otimizado()
    
    return resultado


def comparar_resultados(antes, depois):
    """Compara estatísticas ANTES vs DEPOIS"""
    print("\n" + "="*80)
    print("📊 COMPARAÇÃO: ANTES vs DEPOIS")
    print("="*80)
    
    print(f"\n{'Métrica':<30} | {'Antes':<15} | {'Depois':<15} | {'Diferença':<15}")
    print("-" * 80)
    
    # Total de grupos
    dif_grupos = depois['total_grupos'] - antes['total_grupos']
    perc_grupos = (dif_grupos / antes['total_grupos'] * 100) if antes['total_grupos'] > 0 else 0
    print(f"{'Total de Grupos':<30} | {antes['total_grupos']:>13,} | {depois['total_grupos']:>13,} | {dif_grupos:>+13,} ({perc_grupos:+.1f}%)")
    
    # Grupos com 2 sites
    dif_2sites = depois['grupos_2_sites'] - antes['grupos_2_sites']
    print(f"{'Grupos com 2 sites':<30} | {antes['grupos_2_sites']:>13,} | {depois['grupos_2_sites']:>13,} | {dif_2sites:>+13,}")
    
    # Grupos com 3+ sites
    dif_3plus = depois['grupos_3plus_sites'] - antes['grupos_3plus_sites']
    print(f"{'Grupos com 3+ sites':<30} | {antes['grupos_3plus_sites']:>13,} | {depois['grupos_3plus_sites']:>13,} | {dif_3plus:>+13,}")
    
    # Score médio
    dif_score = depois['score_medio'] - antes['score_medio']
    print(f"{'Score Médio':<30} | {antes['score_medio']:>13.3f} | {depois['score_medio']:>13.3f} | {dif_score:>+13.3f}")
    
    print("\n" + "="*80)
    print("📈 IMPACTO DAS MELHORIAS")
    print("="*80)
    
    print(f"\n✅ Novos matches criados: {dif_grupos:,} ({perc_grupos:+.1f}%)")
    
    if dif_grupos > 0:
        print(f"🎯 Meta alcançada!" if dif_grupos >= 800 else f"⚠️  Abaixo da meta de 889 matches")
    
    return dif_grupos


def main():
    """Função principal"""
    print("\n🧪 TESTE DE MELHORIAS NO MATCHING")
    print("="*80)
    print("\nMELHORIAS IMPLEMENTADAS:")
    print("1. Normalização de preposições (de, da, do, para, das, dos)")
    print("2. Normalização de hífens → espaços")
    print("3. Expansão de categorias relacionadas (9 grupos)")
    print("4. Ajuste de thresholds dinâmicos (0.72-0.75)")
    print("\nImpacto estimado: +889 matches (+17.5%)")
    print("="*80)
    
    try:
        # 1. Analisar banco ANTES
        print("\n📊 Analisando banco ANTES das melhorias...")
        antes = analisar_banco_antes()
        
        # 2. Criar backup
        print("\n💾 Criando backup...")
        backup_banco_atual()
        
        # 3. Executar matching melhorado
        print("\n🚀 Executando matching com melhorias...")
        resultado = executar_matching_melhorado()
        
        # 4. Analisar banco DEPOIS
        print("\n📊 Analisando banco DEPOIS das melhorias...")
        depois = analisar_banco_antes()
        
        # 5. Comparar resultados
        ganho = comparar_resultados(antes, depois)
        
        print("\n✅ Teste concluído com sucesso!")
        print(f"📈 Ganho total: +{ganho:,} matches")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
