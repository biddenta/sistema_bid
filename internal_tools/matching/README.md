# Sistema de Matching - Ferramentas Internas

Sistema profissional de matching de produtos com ferramentas de análise, importação e testes.

## 📁 Estrutura

```
internal_tools/matching/
├── algorithms/          # Algoritmos de matching
│   ├── hybrid_matching.py    # Algoritmo principal (1013 linhas)
│   └── __init__.py
├── analysis/           # Análises de resultados
│   ├── by_site.py           # Análise por site
│   ├── manual_vs_auto.py    # Comparação manual vs automático
│   ├── divergence.py        # Investigação de divergências
│   ├── precision.py         # Precisão por categoria
│   └── __init__.py
├── importers/          # Importação/Exportação
│   ├── manual_matches.py    # Importa matches manuais
│   ├── excel_exporter.py    # Exporta para Excel
│   ├── product_generator.py # Gera arquivos de produtos
│   └── __init__.py
├── testing/            # Testes e validações
│   ├── test_improvements.py # Testa melhorias
│   ├── test_thresholds.py   # Testa thresholds
│   └── __init__.py
├── cli/                # Interface CLI
│   ├── main.py              # CLI principal
│   └── __init__.py
└── utils/              # Utilitários (futuro)
    └── __init__.py
```

## 🚀 Uso Rápido

### Via CLI (Recomendado)

```bash
# Executar matching
python -m internal_tools.matching.cli.main run

# Análises
python -m internal_tools.matching.cli.main analyze site
python -m internal_tools.matching.cli.main analyze manual
python -m internal_tools.matching.cli.main analyze divergence
python -m internal_tools.matching.cli.main analyze precision

# Importar/Exportar
python -m internal_tools.matching.cli.main import manual
python -m internal_tools.matching.cli.main import export-excel
python -m internal_tools.matching.cli.main import generate-products

# Testes
python -m internal_tools.matching.cli.main test improvements
python -m internal_tools.matching.cli.main test thresholds
```

### Via Python

```python
# Executar matching
from internal_tools.matching.algorithms import MatchingHibridoSuperOtimizado

matching = MatchingHibridoSuperOtimizado()
resultado = matching.executar_matching_super_otimizado()

# Análises
from internal_tools.matching.analysis import (
    analisar_matches_por_site,
    analisar_matches_manuais,
    analisar_precisao_por_categoria
)

# Importadores
from internal_tools.matching.importers import (
    processar_matches_manuais,
    exportar_matches_excel,
    GeradorExcelProdutos
)

# Testes
from internal_tools.matching.testing import (
    comparar_resultados,
    testar_fase2
)
```

## 📊 Algoritmo Principal

**Arquivo:** `algorithms/hybrid_matching.py`

### Características

- **4 Fases de Processamento:**
  1. Base Ampliada (threshold baixo)
  2. Validação Rigorosa (4 critérios)
  3. Otimização Avançada
  4. Validação Adaptativa

- **3 Melhorias Implementadas:**
  1. ✅ Normalização essencial (preposições + hífens)
  2. ✅ Categorias relacionadas (9 grupos)
  3. ✅ Thresholds dinâmicos (0.72-0.75 por categoria)

- **Resultado:** +1,750 matches (+29.9%)

### Uso

```python
from internal_tools.matching.algorithms.hybrid_matching import MatchingHibridoSuperOtimizado

# Com bancos padrão (legacy/)
matching = MatchingHibridoSuperOtimizado()

# Com bancos customizados
matching = MatchingHibridoSuperOtimizado(
    db_tratados="path/to/produtos_tratados.db",
    db_mestre="path/to/produtos_mestre.db"
)

resultado = matching.executar_matching_super_otimizado()
print(f"Grupos criados: {resultado['total_grupos']}")
print(f"Tempo: {resultado['tempo_execucao_formatado']}")
```

## 🔍 Análises

### 1. Análise por Site

Mostra cobertura e qualidade de matches por site.

```python
from internal_tools.matching.analysis.by_site import main
main()
```

**Métricas:**
- Total de produtos por site
- Produtos com/sem match
- Percentual de cobertura
- Score médio por site
- Top combinações entre sites

### 2. Análise Manual vs Automático

Identifica padrões e oportunidades de melhoria comparando matches manuais vs automáticos.

```python
from internal_tools.matching.analysis.manual_vs_auto import main
main()
```

**Identifica:**
- Variações de nome
- Variações de marca
- Categorias diferentes
- Falsos negativos
- Recomendações de melhoria

### 3. Análise de Divergência

Investiga divergências entre resultados esperados e reais.

```python
from internal_tools.matching.analysis.divergence import main
main()
```

### 4. Análise de Precisão

Calcula precisão por categoria e gera thresholds dinâmicos.

```python
from internal_tools.matching.analysis.precision import main
main()
```

**Gera:** `shared/config/thresholds_dinamicos.json`

## 📥 Importadores/Exportadores

### 1. Importar Matches Manuais

Importa matches de arquivo Excel (Cadastro Bid Dental).

```python
from internal_tools.matching.importers.manual_matches import main
main()
```

### 2. Exportar Matches para Excel

Exporta tabela de matches com formatação completa.

```python
from internal_tools.matching.importers.excel_exporter import exportar_matches_excel
exportar_matches_excel()
```

**Gera:** `exports/matches_produtos_[timestamp].xlsx`

### 3. Gerar Arquivos de Produtos

Gera arquivos Excel com produtos do mestre (1000 por arquivo).

```python
from internal_tools.matching.importers.product_generator import GeradorExcelProdutos

gerador = GeradorExcelProdutos()
arquivos = gerador.executar(produtos_por_arquivo=1000, pasta_saida="exports")
```

## 🧪 Testes

### 1. Teste de Melhorias

Compara resultados ANTES vs DEPOIS das melhorias.

```python
from internal_tools.matching.testing.test_improvements import main
main()
```

**Compara:**
- Total de grupos
- Distribuição por sites
- Score médio
- Ganho percentual

### 2. Teste de Thresholds

Valida configuração de thresholds dinâmicos.

```python
from internal_tools.matching.testing.test_thresholds import testar_fase2
testar_fase2()
```

## 🔧 Configuração

### Thresholds Dinâmicos

**Arquivo:** `shared/config/thresholds_dinamicos.json`

```json
{
  "threshold_padrao": 0.75,
  "thresholds_por_categoria": {
    "Categoria A": {
      "threshold": 0.72,
      "grupos_existentes": 150,
      "score_medio": 0.88
    }
  }
}
```

### Categorias Relacionadas

Definidas em `hybrid_matching.py` (linha ~460-485):

- Medicamentos + Farmacêuticos + Antibióticos
- Luvas + EPI + Proteção
- Máscaras + Respiratórios + Proteção
- ... (9 grupos no total)

## 📈 Resultados Validados

- ✅ **+1,750 novos matches** (+29.9%)
- ✅ **100% de cobertura** em todos os 8 sites
- ✅ **99.9% qualidade** (score ≥ 0.95)
- ✅ **Tempo: 4.27s** para 45,241 produtos

## 🎯 Próximos Passos

1. ✅ Reorganização completa (concluído)
2. ⏳ Testes de integração
3. ⏳ Integração na API
4. ⏳ Documentação da API
5. ⏳ Deploy em produção

## 📝 Notas

- **Compatibilidade:** Python 3.8+
- **Dependências:** pandas, sqlite3, openpyxl (para Excel)
- **Banco de dados:** SQLite
- **Encoding:** UTF-8

## 🐛 Troubleshooting

### Imports não resolvidos

Os imports são resolvidos via `sys.path.insert(0, ...)`. Se tiver problemas:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
```

### Bancos de dados não encontrados

Verifique os caminhos padrão:
- `legacy/data/produtos_tratados.db`
- `legacy/data/produtos_mestre.db`
- `match_crew.db`

### Erros no Excel (openpyxl)

Instale a dependência:
```bash
pip install openpyxl
```

## 📧 Suporte

Para dúvidas ou problemas, consulte:
- Documentação principal: `docs/`
- Arquitetura: `docs/arquitetura/`
- Changelog: `docs/gestao/RELATORIO_ALTERACOES_*.md`
