"""
Script de teste para validar reorganização
Executa matching e salva no banco match_crew.db
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
from datetime import datetime


def verificar_estado_inicial():
    """Verifica estado inicial dos bancos"""
    print("\n" + "="*80)
    print("📊 VERIFICANDO ESTADO INICIAL DOS BANCOS")
    print("="*80)
    
    # Banco principal
    conn_main = sqlite3.connect('match_crew.db')
    cursor_main = conn_main.cursor()
    
    cursor_main.execute("SELECT COUNT(*) FROM produtos_mestre")
    matches_main = cursor_main.fetchone()[0]
    
    cursor_main.execute("SELECT COUNT(*) FROM produtos")
    produtos_main = cursor_main.fetchone()[0]
    
    print(f"\n📦 Banco Principal (match_crew.db):")
    print(f"   • Produtos: {produtos_main:,}")
    print(f"   • Matches: {matches_main:,}")
    
    conn_main.close()
    
    # Banco tratados
    conn_tratados = sqlite3.connect('match_crew.db')
    cursor_tratados = conn_tratados.cursor()
    
    # Contar produtos em todas as tabelas
    cursor_tratados.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%_tratado'
    """)
    tables = cursor_tratados.fetchall()
    
    total_tratados = 0
    for (table,) in tables:
        cursor_tratados.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor_tratados.fetchone()[0]
        total_tratados += count
    
    print(f"\n📦 Banco de Dados (match_crew.db):")
    print(f"   • Produtos tratados: {total_tratados:,}")
    print(f"   • Tabelas: {len(tables)}")
    
    conn_tratados.close()
    
    return {
        'matches_antes': matches_main,
        'produtos': produtos_main,
        'produtos_tratados': total_tratados
    }


def executar_matching_no_banco_principal():
    """Executa matching salvando no banco principal"""
    print("\n" + "="*80)
    print("🚀 EXECUTANDO MATCHING NO BANCO PRINCIPAL")
    print("="*80)
    
    from internal_tools.matching.algorithms.hybrid_matching import MatchingHibridoSuperOtimizado
    
    # Criar instância apontando para banco principal
    print("\n⚙️  Configurando matcher...")
    print("   • db: match_crew.db")
    print("   • db_mestre: match_crew.db (BANCO PRINCIPAL)")
    
    matcher = MatchingHibridoSuperOtimizado(
        db_tratados="match_crew.db",
        db_mestre="match_crew.db"  # <-- Salvar no banco principal!
    )
    
    print("\n🔄 Executando matching...")
    resultado = matcher.executar_matching_super_otimizado()
    
    return resultado


def verificar_estado_final(estado_inicial):
    """Verifica estado final e compara com inicial"""
    print("\n" + "="*80)
    print("📊 VERIFICANDO ESTADO FINAL")
    print("="*80)
    
    conn = sqlite3.connect('match_crew.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM produtos_mestre")
    matches_depois = cursor.fetchone()[0]
    
    # Últimos matches criados
    cursor.execute("""
        SELECT id_match, nome_produto, total_sites, total_produtos, score_match, data_criacao
        FROM produtos_mestre
        ORDER BY data_criacao DESC
        LIMIT 5
    """)
    ultimos = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📦 Banco Principal (match_crew.db):")
    print(f"   • Matches ANTES: {estado_inicial['matches_antes']:,}")
    print(f"   • Matches DEPOIS: {matches_depois:,}")
    
    diferenca = matches_depois - estado_inicial['matches_antes']
    if diferenca > 0:
        print(f"   ✅ NOVOS matches criados: +{diferenca:,}")
    elif diferenca < 0:
        print(f"   ⚠️  Matches REMOVIDOS: {diferenca:,}")
    else:
        print(f"   ⚠️  Nenhum match novo (pode ter sobrescrito)")
    
    print(f"\n📋 Últimos 5 matches criados:")
    for match in ultimos:
        id_match, nome, sites, produtos, score, data = match
        print(f"   • {id_match}: {nome[:50]}")
        print(f"     Sites: {sites} | Produtos: {produtos} | Score: {score:.3f}")
        print(f"     Data: {data}")
    
    return diferenca


def main():
    """Função principal do teste"""
    print("\n" + "="*80)
    print("🧪 TESTE DE REORGANIZAÇÃO - MATCHING NO BANCO PRINCIPAL")
    print("="*80)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Estado inicial
        estado_inicial = verificar_estado_inicial()
        
        # 2. Executar matching
        resultado = executar_matching_no_banco_principal()
        
        # 3. Verificar resultado
        diferenca = verificar_estado_final(estado_inicial)
        
        # 4. Resumo
        print("\n" + "="*80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*80)
        
        print(f"\n📊 Resumo:")
        print(f"   • Matches finais: {resultado.get('matches_finais', 'N/A'):,}")
        print(f"   • Tempo execução: {resultado.get('tempo_execucao_formatado', 'N/A')}")
        print(f"   • Adequação: {resultado.get('adequacao', 0)*100:.1f}%")
        print(f"   • Novos matches no banco: +{diferenca:,}")
        
        if diferenca > 0:
            print(f"\n✅ SUCESSO! {diferenca:,} novos matches foram salvos em match_crew.db")
        else:
            print(f"\n⚠️  ATENÇÃO! Nenhum match novo foi criado.")
            print(f"   Possível causa: Matching sobrescreveu dados existentes")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
