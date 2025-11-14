"""
Ferramentas de Análise

Scripts para análise de resultados, qualidade e performance do matching:
- by_site: Análise de cobertura por site
- manual_vs_auto: Comparação entre matches manuais e automáticos
- divergence: Investigação de divergências entre resultados
- precision: Análise de precisão por categoria
"""

from .by_site import (
    analisar_matches_por_site,
    exibir_resultados,
    estatisticas_gerais,
    analisar_matches_cross_site,
    analisar_por_categoria_e_site,
    analisar_qualidade_por_site
)

from .manual_vs_auto import (
    analisar_matches_manuais,
    analisar_variacoes_nome,
    verificar_deteccao_automatica,
    gerar_recomendacoes
)

from .divergence import (
    analisar_matches_manuais_no_banco,
    comparar_bancos,
    analisar_overlaps,
    analisar_cobertura_produtos,
    analisar_categorias_relacionadas
)

from .precision import (
    analisar_precisao_por_categoria,
    conectar_db
)

__all__ = [
    # by_site
    'analisar_matches_por_site',
    'exibir_resultados',
    'estatisticas_gerais',
    'analisar_matches_cross_site',
    'analisar_por_categoria_e_site',
    'analisar_qualidade_por_site',
    
    # manual_vs_auto
    'analisar_matches_manuais',
    'analisar_variacoes_nome',
    'verificar_deteccao_automatica',
    'gerar_recomendacoes',
    
    # divergence
    'analisar_matches_manuais_no_banco',
    'comparar_bancos',
    'analisar_overlaps',
    'analisar_cobertura_produtos',
    'analisar_categorias_relacionadas',
    
    # precision
    'analisar_precisao_por_categoria',
    'conectar_db',
]
