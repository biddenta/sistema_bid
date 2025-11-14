"""
Scripts de Teste

Ferramentas para validação e testes do algoritmo de matching:
- test_improvements: Testa melhorias implementadas (antes vs depois)
- test_thresholds: Valida configuração de thresholds dinâmicos
"""

from .test_improvements import (
    backup_banco_atual,
    analisar_banco_antes,
    executar_matching_melhorado,
    comparar_resultados
)

from .test_thresholds import testar_fase2

__all__ = [
    # test_improvements
    'backup_banco_atual',
    'analisar_banco_antes',
    'executar_matching_melhorado',
    'comparar_resultados',
    
    # test_thresholds
    'testar_fase2',
]
