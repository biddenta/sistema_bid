"""
Interface CLI

Interface de linha de comando unificada para todas as ferramentas de matching.

Uso:
    python -m internal_tools.matching.cli.main [comando] [argumentos]

Comandos disponíveis:
    run                    - Executar matching
    analyze [tipo]         - Executar análises (site, manual, divergence, precision)
    import [tipo]          - Importar/exportar dados (manual, export-excel, generate-products)
    test [tipo]            - Executar testes (improvements, thresholds)
"""

from .main import main

__all__ = ['main']
