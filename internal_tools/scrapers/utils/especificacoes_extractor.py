import re
from typing import Dict, List, Optional, Tuple

class ExtractorEspecificacoes:
    """Extrator inteligente de especificações para matching preciso"""
    
    def __init__(self):
        # Padrões baseados nos exemplos analisados
        self.padroes = {
            'percentual': [
                r'(\d+[,.]?\d*)\s*%',                    # 70%, 37%, 50%
                r'(\d+[,.]?\d*)\s*por\s*cento',         # 70 por cento
            ],
            
            'volume_liquido': [
                r'(\d+[,.]?\d*)\s*[Ll](?:\s|$|[^a-z])',  # 5L, 1l, 500ml
                r'(\d+[,.]?\d*)\s*[Mm][Ll]',             # 500ml, 100ML
                r'(\d+[,.]?\d*)\s*litros?',              # 5 litros
                r'(\d+[,.]?\d*)\s*mililitros?',          # 500 mililitros
            ],
            
            'peso_massa': [
                r'(\d+[,.]?\d*)\s*[Gg](?:\s|$|[^a-z])',  # 3,8g, 10G
                r'(\d+[,.]?\d*)\s*[Kk][Gg]',             # 1kg, 2KG
                r'(\d+[,.]?\d*)\s*gramas?',              # 500 gramas
            ],
            
            'dimensoes': [
                r'(\d+[,.]?\d*)\s*x\s*(\d+[,.]?\d*)\s*[Cc][Mm]',  # 20x37cm
                r'(\d+[,.]?\d*)\s*x\s*(\d+[,.]?\d*)\s*[Mm][Mm]',  # 2x5mm
                r'(\d+[,.]?\d*)\s*[Cc][Mm]',                      # 15cm
                r'(\d+[,.]?\d*)\s*[Mm][Mm]',                      # 25mm
            ],
            
            'quantidade': [
                r'[Cc]/(\d+)',                           # C/2, c/5
                r'[Cc]om\s*(\d+)',                       # com 3, Com 5
                r'(\d+)\s*unidades?',                    # 2 unidades
                r'(\d+)\s*seringas?',                    # 3 seringas
                r'[Pp]ack\s*(\d+)',                      # Pack 100
                r'[Cc]aixa\s*(\d+)',                     # Caixa 50
            ],
            
            'publico_alvo': [
                r'(adulto|infantil|criança)',           # Adulto, Infantil
                r'(pediátrico|pediatrico)',             # Pediátrico
                r'(jovem|adolescente)',                  # Jovem
            ],
            
            'cores': [
                r'(verde|azul|rosa|amarelo|branco|transparente|natural|cristal)',
                r'(vermelho|preto|cinza|dourado|prateado)',
            ],
            
            'tamanhos_categoria': [
                r'\b([PPMGXL]{1,3})\b',                  # P, M, G, XL, XXL
                r'(pequeno|médio|grande)',               # pequeno, médio, grande
                r'(mini|maxi|super)',                    # mini, maxi, super
            ]
        }
    
    def extrair_especificacoes_completas(self, nome: str, descricao: str = "") -> Dict:
        """
        Extrai todas as especificações relevantes para matching
        
        Args:
            nome: Nome do produto
            descricao: Descrição do produto (opcional)
            
        Returns:
            Dict com especificações extraídas
        """
        texto_completo = f"{nome} {descricao}".lower()
        specs = {}
        
        # Extrair cada tipo de especificação
        for categoria, padroes in self.padroes.items():
            valores = []
            for padrao in padroes:
                matches = re.findall(padrao, texto_completo, re.IGNORECASE)
                if matches:
                    # Flatten matches se for tuple
                    for match in matches:
                        if isinstance(match, tuple):
                            valores.extend([v for v in match if v])
                        else:
                            valores.append(match)
            
            if valores:
                specs[categoria] = list(set(valores))  # Remove duplicatas
        
        return self._processar_especificacoes(specs, nome)
    
    def _processar_especificacoes(self, specs_brutas: Dict, nome_original: str) -> Dict:
        """Processa e normaliza as especificações extraídas"""
        
        specs_processadas = {
            'percentual': None,
            'volume': None, 
            'peso': None,
            'dimensoes': None,
            'quantidade': None,
            'publico': None,
            'cor': None,
            'tamanho': None,
            'specs_originais': specs_brutas
        }
        
        # Processar percentual (pegar o primeiro encontrado)
        if 'percentual' in specs_brutas:
            specs_processadas['percentual'] = specs_brutas['percentual'][0] + '%'
        
        # Processar volume (normalizar para ml)
        if 'volume_liquido' in specs_brutas:
            volume = specs_brutas['volume_liquido'][0]
            specs_processadas['volume'] = self._normalizar_volume(volume)
        
        # Processar peso (normalizar para g)
        if 'peso_massa' in specs_brutas:
            peso = specs_brutas['peso_massa'][0]  
            specs_processadas['peso'] = self._normalizar_peso(peso)
        
        # Processar dimensões (manter formato original)
        if 'dimensoes' in specs_brutas:
            specs_processadas['dimensoes'] = specs_brutas['dimensoes'][0]
        
        # Processar quantidade
        if 'quantidade' in specs_brutas:
            specs_processadas['quantidade'] = specs_brutas['quantidade'][0]
            
        # Processar público-alvo
        if 'publico_alvo' in specs_brutas:
            specs_processadas['publico'] = specs_brutas['publico_alvo'][0]
            
        # Processar cor
        if 'cores' in specs_brutas:
            specs_processadas['cor'] = specs_brutas['cores'][0]
            
        # Processar tamanho
        if 'tamanhos_categoria' in specs_brutas:
            specs_processadas['tamanho'] = specs_brutas['tamanhos_categoria'][0].upper()
        
        return specs_processadas
    
    def _normalizar_volume(self, volume_str: str) -> str:
        """Normaliza volume para ml"""
        volume = volume_str.replace(',', '.')
        if 'l' in volume.lower():
            # Converter litros para ml
            num = float(re.findall(r'(\d+[.]?\d*)', volume)[0])
            return f"{int(num * 1000)}ml"
        return volume_str + 'ml'
    
    def _normalizar_peso(self, peso_str: str) -> str:
        """Normaliza peso para gramas"""
        peso = peso_str.replace(',', '.')
        if 'kg' in peso.lower():
            # Converter kg para g
            num = float(re.findall(r'(\d+[.]?\d*)', peso)[0])
            return f"{int(num * 1000)}g"
        return peso_str + 'g'
    
    def gerar_chave_matching_com_specs(self, marca: str, nome_limpo: str, specs: Dict) -> str:
        """
        Gera chave de matching incluindo especificações críticas
        
        Exemplo:
        - Sem specs: "prolink_alcool_etilico_saneante"  
        - Com specs: "prolink_alcool_etilico_70%_saneante"
        """
        componentes = [marca.lower() if marca else ""]
        
        # Nome base
        componentes.append(nome_limpo.lower())
        
        # Adicionar especificações críticas na ordem de importância
        specs_criticas = []
        
        if specs.get('percentual'):
            specs_criticas.append(specs['percentual'])
            
        if specs.get('volume'):
            specs_criticas.append(specs['volume'])
            
        if specs.get('peso'):
            specs_criticas.append(specs['peso'])
            
        if specs.get('dimensoes'):
            specs_criticas.append(specs['dimensoes'])
            
        if specs.get('quantidade'):
            specs_criticas.append(f"c{specs['quantidade']}")
            
        if specs.get('publico'):
            specs_criticas.append(specs['publico'])
            
        if specs.get('cor'):
            specs_criticas.append(specs['cor'])
        
        # Montar chave final
        if specs_criticas:
            componentes.extend(specs_criticas)
        
        # Limpar e juntar
        chave = "_".join([c for c in componentes if c])
        chave = re.sub(r'[^\w%]', '_', chave)  # Manter % mas limpar outros caracteres especiais
        chave = re.sub(r'_+', '_', chave)      # Múltiplos _ viram um só
        
        return chave.strip('_')

# Função de conveniência para usar nos scrapers
def extrair_e_processar_especificacoes(nome_produto: str, descricao: str = "") -> Tuple[Dict, str]:
    """
    Função simplificada para usar nos scrapers existentes
    
    Returns:
        Tuple[especificacoes_dict, chave_com_specs]
    """
    extractor = ExtractorEspecificacoes()
    specs = extractor.extrair_especificacoes_completas(nome_produto, descricao)
    
    # Para gerar chave, precisamos da marca (que já temos dos scrapers)
    # Retornamos apenas as specs, a chave será gerada no scraper
    return specs, ""

# Exemplos de teste baseados nos casos reais
def testar_exemplos_reais():
    """Testa com os exemplos fornecidos pelo usuário"""
    
    extractor = ExtractorEspecificacoes()
    
    exemplos = [
        "Álcool Etílico 70% Saneante - Prolink",
        "Água Destilada para Autoclave 5L - SSPlus",
        "Condicionador Acido Fosforico 37% com 3 seringas - Quimidrol",
        "Abridor de Boca com Afastador de Língua Verde - Cotisen",
        "Envelope Auto Selante 20 x 37 Cm - Pack GC",
        "Abridor Boca Adulto E Infantil - Iodontosul",
        "Resina Palfique LX5 3,8g - Tokuyama",
        "Afastador Labial Haste Metálica C/2 – Morelli"
    ]
    
    print("🧪 TESTE COM EXEMPLOS REAIS:")
    print("="*60)
    
    for exemplo in exemplos:
        specs = extractor.extrair_especificacoes_completas(exemplo)
        print(f"\n[PACOTE] PRODUTO: {exemplo}")
        print(f"[INFO] SPECS: {specs}")
        
        # Simular chave com marca fictícia
        chave = extractor.gerar_chave_matching_com_specs("marca", exemplo, specs)
        print(f"🔑 CHAVE: {chave}")

if __name__ == "__main__":
    testar_exemplos_reais()
