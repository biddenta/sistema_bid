import re
from typing import Tuple, Optional

def extrair_marca_universal(nome_produto: str) -> Tuple[Optional[str], str]:
    """
    Extrai marca usando o método GENIAL: último hífen.
    
    Args:
        nome_produto: Nome completo do produto
        
    Returns:
        Tuple[marca, nome_produto_sem_marca]
    """
    if not nome_produto or not isinstance(nome_produto, str):
        return None, nome_produto or ""
    
    nome_original = nome_produto.strip()
    
    # Encontrar o último hífen
    ultimo_hifen = -1
    for i, char in enumerate(nome_original):
        if char in ['-', '–']:
            ultimo_hifen = i
    
    # Se não encontrou hífen, retornar None
    if ultimo_hifen == -1:
        return None, nome_original
    
    # Extrair marca (tudo após o último hífen)
    produto_sem_marca = nome_original[:ultimo_hifen].strip()
    possivel_marca = nome_original[ultimo_hifen + 1:].strip()
    
    # Validar e padronizar
    if _validar_marca(possivel_marca):
        return _padronizar_marca(possivel_marca), produto_sem_marca
    
    return None, nome_original

def _validar_marca(marca: str) -> bool:
    """Validação simplificada."""
    if not marca or len(marca.strip()) < 2:
        return False
    
    marca = marca.strip()
    
    # Aceitar marcas numéricas conhecidas
    if marca.upper() in ['3M', '2I', '4M']:
        return True
    
    # Rejeitar apenas números
    if marca.isdigit():
        return False
    
    # Rejeitar unidades de medida
    if marca.lower() in ['ml', 'mg', 'g', 'cm', 'mm', 'un', 'pcs', 'pç']:
        return False
    
    return True

def _padronizar_marca(marca: str) -> str:
    """Padronização simplificada."""
    casos_especiais = {
        '3m': '3M', 'fgm': 'FGM', 'ssplus': 'SSPlus',
        'morelli': 'Morelli', 'angelus': 'Angelus'
    }
    
    marca_lower = marca.lower()
    return casos_especiais.get(marca_lower, marca.title())

# Funções auxiliares para matching
def limpar_nome_produto(nome: str) -> str:
    """Remove caracteres especiais."""
    return re.sub(r'[^\w\s]', '', nome.lower()).strip()

def gerar_chave_matching(marca: str, nome: str) -> str:
    """Gera chave para matching."""
    if not marca or not nome:
        return ""
    return f"{limpar_nome_produto(marca)}_{limpar_nome_produto(nome)}"

def processar_produto_completo(nome_completo: str) -> dict:
    """Processa produto completo."""
    marca, nome_sem_marca = extrair_marca_universal(nome_completo)
    
    return {
        'marca_extraida': marca,
        'nome_sem_marca': nome_sem_marca,
        'nome_limpo': limpar_nome_produto(nome_sem_marca),
        'chave_matching': gerar_chave_matching(marca, nome_sem_marca) if marca else ""
    }

print("[OK] FUNCAO FINAL CRIADA!")
print("[INFO] Pronta para implementacao em todos os 9 scrapers")
print("[INFO] Baseada na ideia do 'ultimo hifen'")
print("[INFO] 10x mais simples que a versao original")
