"""
Internal Tools - Sistema de Matching

Ferramentas internas para desenvolvimento, análise e manutenção
do sistema de matching de produtos.

Módulos:
---------
- algorithms: Engines e algoritmos de matching
- analysis: Ferramentas de análise e relatórios
- importers: Importação de dados externos
- testing: Testes e validações
- cli: Interfaces de linha de comando
- utils: Utilitários compartilhados

Uso:
----
>>> from internal_tools.matching.algorithms import HybridMatching
>>> from internal_tools.matching.analysis import analyze_by_site
>>> from internal_tools.matching.importers import ManualMatchesImporter
"""

__version__ = "1.0.0"
__author__ = "Match Crew Team"

# Facilita imports
from . import algorithms
from . import analysis
from . import importers
from . import testing
from . import cli
from . import utils

__all__ = [
    'algorithms',
    'analysis',
    'importers',
    'testing',
    'cli',
    'utils',
]
