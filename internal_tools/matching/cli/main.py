"""
CLI Principal do Sistema de Matching
Interface unificada para todas as ferramentas de matching
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import argparse


def executar_matching():
    """Executa o algoritmo de matching"""
    print("\n🚀 Executando Matching...")
    from internal_tools.matching.algorithms.hybrid_matching import MatchingHibridoSuperOtimizado
    
    matching = MatchingHibridoSuperOtimizado()
    resultado = matching.executar_matching_super_otimizado()
    
    print(f"\n✅ Matching concluído!")
    print(f"   Tempo: {resultado['tempo_execucao_formatado']}")
    print(f"   Grupos criados: {resultado['total_grupos']:,}")


def executar_analise(tipo):
    """Executa análises"""
    print(f"\n📊 Executando análise: {tipo}...")
    
    if tipo == "site":
        from internal_tools.matching.analysis.by_site import main
        main()
    elif tipo == "manual":
        from internal_tools.matching.analysis.manual_vs_auto import main
        main()
    elif tipo == "divergence":
        from internal_tools.matching.analysis.divergence import main
        main()
    elif tipo == "precision":
        from internal_tools.matching.analysis.precision import main
        main()
    else:
        print(f"❌ Tipo de análise '{tipo}' não reconhecido")
        print("   Tipos disponíveis: site, manual, divergence, precision")


def executar_importacao(tipo):
    """Executa importações"""
    print(f"\n📥 Executando importação: {tipo}...")
    
    if tipo == "manual":
        from internal_tools.matching.importers.manual_matches import main
        main()
    elif tipo == "export-excel":
        from internal_tools.matching.importers.excel_exporter import exportar_matches_excel
        exportar_matches_excel()
    elif tipo == "generate-products":
        from internal_tools.matching.importers.product_generator import main
        main()
    else:
        print(f"❌ Tipo de importação '{tipo}' não reconhecido")
        print("   Tipos disponíveis: manual, export-excel, generate-products")


def executar_teste(tipo):
    """Executa testes"""
    print(f"\n🧪 Executando teste: {tipo}...")
    
    if tipo == "improvements":
        from internal_tools.matching.testing.test_improvements import main
        main()
    elif tipo == "thresholds":
        from internal_tools.matching.testing.test_thresholds import testar_fase2
        testar_fase2()
    else:
        print(f"❌ Tipo de teste '{tipo}' não reconhecido")
        print("   Tipos disponíveis: improvements, thresholds")


def main():
    """Função principal do CLI"""
    parser = argparse.ArgumentParser(
        description="Sistema de Matching - CLI Unificado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Executar matching
  python -m internal_tools.matching.cli.main run
  
  # Análises
  python -m internal_tools.matching.cli.main analyze site
  python -m internal_tools.matching.cli.main analyze manual
  
  # Importar/Exportar
  python -m internal_tools.matching.cli.main import manual
  python -m internal_tools.matching.cli.main import export-excel
  
  # Testes
  python -m internal_tools.matching.cli.main test improvements
  python -m internal_tools.matching.cli.main test thresholds
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a executar')
    
    # Comando: run (executar matching)
    subparsers.add_parser('run', help='Executar algoritmo de matching')
    
    # Comando: analyze (análises)
    parser_analyze = subparsers.add_parser('analyze', help='Executar análises')
    parser_analyze.add_argument(
        'type',
        choices=['site', 'manual', 'divergence', 'precision'],
        help='Tipo de análise'
    )
    
    # Comando: import (importações/exportações)
    parser_import = subparsers.add_parser('import', help='Importar/Exportar dados')
    parser_import.add_argument(
        'type',
        choices=['manual', 'export-excel', 'generate-products'],
        help='Tipo de importação/exportação'
    )
    
    # Comando: test (testes)
    parser_test = subparsers.add_parser('test', help='Executar testes')
    parser_test.add_argument(
        'type',
        choices=['improvements', 'thresholds'],
        help='Tipo de teste'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("\n" + "="*70)
    print("🔧 SISTEMA DE MATCHING - CLI")
    print("="*70)
    
    try:
        if args.command == 'run':
            executar_matching()
        elif args.command == 'analyze':
            executar_analise(args.type)
        elif args.command == 'import':
            executar_importacao(args.type)
        elif args.command == 'test':
            executar_teste(args.type)
        
        print("\n" + "="*70)
        print("✅ Operação concluída com sucesso!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
