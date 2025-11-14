"""
Análise de matches por site

Mostra quantos produtos de cada site encontraram matches
e a distribuição de cobertura por site
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
from collections import defaultdict


def analisar_matches_por_site(db_path="legacy/data/produtos_mestre.db"):
    """Analisa distribuição de matches por site"""
    
    print("="*80)
    print("📊 ANÁLISE DE MATCHES POR SITE")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Lista de sites (baseado nas colunas URL)
    sites = [
        'cremer',
        'speed',
        'medsul',
        'proclin',
        'dentalshop',
        'apoiodental',
        'interdental',
        'surya'
    ]
    
    resultados = {}
    
    for site in sites:
        # Conta produtos com URL do site
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM produtos_mestre
            WHERE url_{site} IS NOT NULL AND url_{site} != ''
        """)
        total_com_url = cursor.fetchone()[0]
        
        # Produtos do site em matches com 2+ sites
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM produtos_mestre
            WHERE url_{site} IS NOT NULL 
            AND url_{site} != ''
            AND total_sites >= 2
        """)
        com_match = cursor.fetchone()[0]
        
        # Produtos do site em matches com apenas 1 site (sem match)
        sem_match = total_com_url - com_match
        
        # Percentual de cobertura
        percentual = (com_match / total_com_url * 100) if total_com_url > 0 else 0
        
        resultados[site] = {
            'total': total_com_url,
            'com_match': com_match,
            'sem_match': sem_match,
            'percentual': percentual
        }
    
    conn.close()
    
    return resultados, sites


def exibir_resultados(resultados, sites):
    """Exibe resultados de forma formatada"""
    
    print("\n" + "="*80)
    print("📈 RESULTADOS POR SITE")
    print("="*80)
    
    # Ordena por percentual de cobertura (decrescente)
    sites_ordenados = sorted(sites, key=lambda s: resultados[s]['percentual'], reverse=True)
    
    print("\n┌" + "─"*78 + "┐")
    print("│ {:^20} │ {:^12} │ {:^12} │ {:^12} │ {:^12} │".format(
        "SITE", "TOTAL", "COM MATCH", "SEM MATCH", "COBERTURA"
    ))
    print("├" + "─"*78 + "┤")
    
    for site in sites_ordenados:
        dados = resultados[site]
        nome_site = site.upper()
        
        # Define cor baseado no percentual
        if dados['percentual'] >= 50:
            status = "✅"
        elif dados['percentual'] >= 30:
            status = "⚠️ "
        else:
            status = "❌"
        
        print("│ {:20} │ {:>12,} │ {:>12,} │ {:>12,} │ {:>11.1f}% {} │".format(
            nome_site,
            dados['total'],
            dados['com_match'],
            dados['sem_match'],
            dados['percentual'],
            status
        ))
    
    print("└" + "─"*78 + "┘")


def estatisticas_gerais(resultados):
    """Exibe estatísticas gerais"""
    
    print("\n" + "="*80)
    print("📊 ESTATÍSTICAS GERAIS")
    print("="*80)
    
    total_produtos = sum(r['total'] for r in resultados.values())
    total_com_match = sum(r['com_match'] for r in resultados.values())
    total_sem_match = sum(r['sem_match'] for r in resultados.values())
    
    cobertura_media = (total_com_match / total_produtos * 100) if total_produtos > 0 else 0
    
    print(f"\n📦 Total de produtos (todos os sites): {total_produtos:,}")
    print(f"✅ Produtos com match (2+ sites): {total_com_match:,}")
    print(f"❌ Produtos sem match (1 site): {total_sem_match:,}")
    print(f"📈 Cobertura média: {cobertura_media:.1f}%")
    
    # Site com melhor e pior cobertura
    melhor_site = max(resultados.items(), key=lambda x: x[1]['percentual'])
    pior_site = min(resultados.items(), key=lambda x: x[1]['percentual'])
    
    print(f"\n🏆 Melhor cobertura: {melhor_site[0].upper()} ({melhor_site[1]['percentual']:.1f}%)")
    print(f"⚠️  Pior cobertura: {pior_site[0].upper()} ({pior_site[1]['percentual']:.1f}%)")


def analisar_matches_cross_site(db_path="legacy/data/produtos_mestre.db"):
    """Analisa matches entre sites específicos"""
    
    print("\n" + "="*80)
    print("🔄 MATCHES ENTRE SITES (TOP COMBINAÇÕES)")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    sites = ['cremer', 'speed', 'medsul', 'proclin', 'dentalshop', 'apoiodental', 'interdental', 'surya']
    
    # Conta matches entre pares de sites
    combinacoes = []
    
    for i, site1 in enumerate(sites):
        for site2 in sites[i+1:]:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT id_match)
                FROM produtos_mestre
                WHERE url_{site1} IS NOT NULL 
                AND url_{site1} != ''
                AND url_{site2} IS NOT NULL 
                AND url_{site2} != ''
            """)
            
            count = cursor.fetchone()[0]
            if count > 0:
                combinacoes.append((site1, site2, count))
    
    conn.close()
    
    # Ordena por número de matches
    combinacoes.sort(key=lambda x: x[2], reverse=True)
    
    print("\nTop 10 combinações de sites:")
    print("┌" + "─"*60 + "┐")
    print("│ {:^30} │ {:^25} │".format("COMBINAÇÃO", "MATCHES"))
    print("├" + "─"*60 + "┤")
    
    for i, (site1, site2, count) in enumerate(combinacoes[:10], 1):
        print("│ {:<2}. {:^13} ↔ {:<13} │ {:>25,} │".format(
            i, site1.upper(), site2.upper(), count
        ))
    
    print("└" + "─"*60 + "┘")


def analisar_por_categoria_e_site(db_path="legacy/data/produtos_mestre.db"):
    """Analisa cobertura por categoria em cada site"""
    
    print("\n" + "="*80)
    print("📂 COBERTURA POR CATEGORIA (TOP 10)")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Top categorias com mais produtos matcheados
    cursor.execute("""
        SELECT 
            categoria,
            COUNT(*) as total,
            COUNT(CASE WHEN total_sites >= 2 THEN 1 END) as com_match,
            ROUND(COUNT(CASE WHEN total_sites >= 2 THEN 1 END) * 100.0 / COUNT(*), 1) as percentual
        FROM produtos_mestre
        WHERE categoria IS NOT NULL AND categoria != ''
        GROUP BY categoria
        ORDER BY com_match DESC
        LIMIT 10
    """)
    
    print("\n┌" + "─"*70 + "┐")
    print("│ {:^30} │ {:^10} │ {:^10} │ {:^12} │".format(
        "CATEGORIA", "TOTAL", "MATCHES", "COBERTURA"
    ))
    print("├" + "─"*70 + "┤")
    
    for categoria, total, com_match, percentual in cursor.fetchall():
        # Trunca nome da categoria se muito longo
        cat_nome = categoria[:28] + ".." if len(categoria) > 30 else categoria
        
        print("│ {:<30} │ {:>10,} │ {:>10,} │ {:>11.1f}% │".format(
            cat_nome, total, com_match, percentual
        ))
    
    print("└" + "─"*70 + "┘")
    
    conn.close()


def analisar_qualidade_por_site(db_path="legacy/data/produtos_mestre.db"):
    """Analisa qualidade (score) dos matches por site"""
    
    print("\n" + "="*80)
    print("⭐ QUALIDADE DOS MATCHES POR SITE")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    sites = ['cremer', 'speed', 'medsul', 'proclin', 'dentalshop', 'apoiodental', 'interdental', 'surya']
    
    resultados = []
    
    for site in sites:
        cursor.execute(f"""
            SELECT 
                AVG(score_match) as score_medio,
                COUNT(CASE WHEN score_match >= 0.95 THEN 1 END) as alta_qualidade,
                COUNT(CASE WHEN score_match >= 0.80 AND score_match < 0.95 THEN 1 END) as media_qualidade,
                COUNT(CASE WHEN score_match < 0.80 THEN 1 END) as baixa_qualidade,
                COUNT(*) as total
            FROM produtos_mestre
            WHERE url_{site} IS NOT NULL 
            AND url_{site} != ''
            AND total_sites >= 2
        """)
        
        row = cursor.fetchone()
        if row and row[4] > 0:  # Se tem produtos
            score_medio, alta, media, baixa, total = row
            resultados.append((site, score_medio, alta, media, baixa, total))
    
    conn.close()
    
    # Ordena por score médio
    resultados.sort(key=lambda x: x[1] if x[1] else 0, reverse=True)
    
    print("\n┌" + "─"*85 + "┐")
    print("│ {:^15} │ {:^10} │ {:^12} │ {:^12} │ {:^12} │ {:^10} │".format(
        "SITE", "SCORE", "ALTA (≥0.95)", "MÉDIA (≥0.80)", "BAIXA (<0.80)", "TOTAL"
    ))
    print("├" + "─"*85 + "┤")
    
    for site, score, alta, media, baixa, total in resultados:
        perc_alta = (alta / total * 100) if total > 0 else 0
        
        print("│ {:^15} │ {:^10.3f} │ {:>6,} ({:>3.0f}%) │ {:>6,} ({:>3.0f}%) │ {:>6,} ({:>3.0f}%) │ {:>10,} │".format(
            site.upper(),
            score if score else 0,
            alta, perc_alta,
            media, (media/total*100) if total > 0 else 0,
            baixa, (baixa/total*100) if total > 0 else 0,
            total
        ))
    
    print("└" + "─"*85 + "┘")


def main():
    """Função principal"""
    
    db_path = "legacy/data/produtos_mestre.db"
    
    if not Path(db_path).exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    print("\n🔍 ANÁLISE COMPLETA DE MATCHES POR SITE")
    print("="*80)
    print(f"Banco: {db_path}")
    
    # 1. Análise por site
    resultados, sites = analisar_matches_por_site(db_path)
    exibir_resultados(resultados, sites)
    
    # 2. Estatísticas gerais
    estatisticas_gerais(resultados)
    
    # 3. Matches cross-site
    analisar_matches_cross_site(db_path)
    
    # 4. Por categoria
    analisar_por_categoria_e_site(db_path)
    
    # 5. Qualidade por site
    analisar_qualidade_por_site(db_path)
    
    print("\n" + "="*80)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("="*80)


if __name__ == "__main__":
    main()
