"""
Importadores e Exportadores

Scripts para importação de dados externos e exportação de resultados:
- manual_matches: Importa matches manuais de arquivos Excel
- excel_exporter: Exporta matches para Excel formatado
- product_generator: Gera arquivos Excel com produtos do mestre
"""

from .manual_matches import (
    normalizar_url,
    analisar_excel,
    processar_matches_manuais,
    adicionar_match,
    atualizar_match
)

from .excel_exporter import exportar_matches_excel

from .product_generator import GeradorExcelProdutos

__all__ = [
    # manual_matches
    'normalizar_url',
    'analisar_excel',
    'processar_matches_manuais',
    'adicionar_match',
    'atualizar_match',
    
    # excel_exporter
    'exportar_matches_excel',
    
    # product_generator
    'GeradorExcelProdutos',
]
