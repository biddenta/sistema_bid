import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class AplicadorFeedbackDeterministico:
    """
    Aplica feedback humano usando LÓGICA DETERMINÍSTICA - SEM IA
    """
    
    def __init__(self):
        self.feedback_file = Path("data/feedback_humano.json")
        self.filtros_file = Path("data/filtros_gerados.json")
        self.sinonimos_file = Path("data/sinonimos_gerados.json")
        
        # Carrega dados existentes
        self.filtros_exclusao = self._carregar_filtros()
        self.sinonimos_aprendidos = self._carregar_sinonimos()
    
    def _carregar_filtros(self):
        """Carrega filtros de exclusão salvos"""
        if self.filtros_file.exists():
            with open(self.filtros_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _carregar_sinonimos(self):
        """Carrega sinônimos aprendidos"""
        if self.sinonimos_file.exists():
            with open(self.sinonimos_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _salvar_filtros(self):
        """Salva filtros atualizados"""
        with open(self.filtros_file, 'w', encoding='utf-8') as f:
            json.dump(self.filtros_exclusao, f, ensure_ascii=False, indent=2)
    
    def _salvar_sinonimos(self):
        """Salva sinônimos atualizados"""
        with open(self.sinonimos_file, 'w', encoding='utf-8') as f:
            json.dump(self.sinonimos_aprendidos, f, ensure_ascii=False, indent=2)
    
    def processar_feedback_humano(self):
        """
        MÉTODO PRINCIPAL: Processa feedback e gera regras determinísticas
        """
        if not self.feedback_file.exists():
            print("❌ Nenhum feedback encontrado")
            return {"regras_geradas": 0}
        
        # Carrega feedback
        with open(self.feedback_file, 'r', encoding='utf-8') as f:
            feedback_data = json.load(f)
        
        estatisticas = {
            "feedbacks_processados": 0,
            "filtros_adicionados": 0,
            "sinonimos_adicionados": 0,
            "regras_geradas": 0
        }
        
        print("PROCESSANDO FEEDBACK HUMANO...")
        print("=" * 50)
        
        # Processa cada feedback
        for match_id, dados in feedback_data.get("matches_validados", {}).items():
            estatisticas["feedbacks_processados"] += 1
            
            if dados.get("valido", False):
                # MATCH VÁLIDO: Extrai sinônimos
                novos_sinonimos = self._extrair_sinonimos_do_feedback(dados)
                estatisticas["sinonimos_adicionados"] += len(novos_sinonimos)
                
            else:
                # FALSO POSITIVO: Cria filtros de exclusão
                novos_filtros = self._criar_filtros_de_exclusao(match_id, dados)
                estatisticas["filtros_adicionados"] += len(novos_filtros)
        
        # Salva regras geradas
        self._salvar_filtros()
        self._salvar_sinonimos()
        
        estatisticas["regras_geradas"] = estatisticas["filtros_adicionados"] + estatisticas["sinonimos_adicionados"]
        
        print(f"Processamento concluído:")
        print(f"   • Feedbacks: {estatisticas['feedbacks_processados']}")
        print(f"   • Filtros criados: {estatisticas['filtros_adicionados']}")
        print(f"   • Sinônimos adicionados: {estatisticas['sinonimos_adicionados']}")
        print(f"   • Total regras: {estatisticas['regras_geradas']}")
        
        return estatisticas
    
    def _extrair_sinonimos_do_feedback(self, dados_feedback):
        """
        REGRA DETERMINÍSTICA: Extrai sinônimos das observações usando PADRÕES ESPECÍFICOS
        """
        observacao = dados_feedback.get("observacao", "").lower()
        novos_sinonimos = []
        
        # PADRÕES ESPECÍFICOS que o sistema reconhece
        padroes_sinonimos = [
            " = ",           # "resina = composite"
            " é ",           # "lidocaína é xylocaína"  
            " e ",           # "resina e composite são iguais"
            " mesmo que ",   # "anestésico mesmo que lidocaína"
            " similar a ",   # "composite similar a resina" 
            " igual a ",     # "broca igual a fresa"
            " equivale a ",  # "xylocaína equivale a lidocaína"
            " também ",      # "composite também é resina"
            " ou seja ",     # "anestésico ou seja lidocaína"
            " isto é ",      # "composite isto é resina"
            " significa "    # "xylocaína significa lidocaína"
        ]
        
        print(f"🔍 Analisando observação: '{observacao}'")
        
        for padrao in padroes_sinonimos:
            if padrao in observacao:
                print(f"   Padrão encontrado: '{padrao}'")
                partes = observacao.split(padrao)
                if len(partes) >= 2:
                    palavra_base = partes[0].strip()
                    sinonimo = partes[1].strip()
                    
                    # Limpa palavras extras (artigos, preposições)
                    palavra_base = self._limpar_palavra_para_sinonimo(palavra_base)
                    sinonimo = self._limpar_palavra_para_sinonimo(sinonimo)
                    
                    if palavra_base and sinonimo and len(palavra_base) > 2 and len(sinonimo) > 2:
                        # Adiciona ao dicionário
                        if palavra_base not in self.sinonimos_aprendidos:
                            self.sinonimos_aprendidos[palavra_base] = []
                        
                        if sinonimo not in self.sinonimos_aprendidos[palavra_base]:
                            self.sinonimos_aprendidos[palavra_base].append(sinonimo)
                            novos_sinonimos.append((palavra_base, sinonimo))
                            
                            print(f"Sinônimo identificado: '{palavra_base}' = '{sinonimo}'")
        
        # PADRÕES MÚLTIPLOS: "resina = composite = fotopolimerizável"
        if " = " in observacao:
            partes = observacao.split(" = ")
            if len(partes) > 2:
                palavra_base = self._limpar_palavra_para_sinonimo(partes[0])
                for i in range(1, len(partes)):
                    sinonimo = self._limpar_palavra_para_sinonimo(partes[i])
                    if palavra_base and sinonimo:
                        if palavra_base not in self.sinonimos_aprendidos:
                            self.sinonimos_aprendidos[palavra_base] = []
                        if sinonimo not in self.sinonimos_aprendidos[palavra_base]:
                            self.sinonimos_aprendidos[palavra_base].append(sinonimo)
                            novos_sinonimos.append((palavra_base, sinonimo))
                            print(f"Sinônimo múltiplo: '{palavra_base}' = '{sinonimo}'")
        
        return novos_sinonimos
    
    def _limpar_palavra_para_sinonimo(self, texto):
        """Limpa texto para extrair palavra principal"""
        import re
        
        # Remove palavras comuns que atrapalham
        stop_words = [
            "o", "a", "os", "as", "um", "uma", "de", "da", "do", "das", "dos",
            "para", "com", "por", "em", "na", "no", "são", "também", "produto",
            "material", "dental", "odontológico"
        ]
        
        # Limpa pontuação e normaliza
        texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
        palavras = texto_limpo.split()
        
        # Remove stop words e pega a palavra mais significativa
        palavras_relevantes = [p for p in palavras if p not in stop_words and len(p) > 2]
        
        if palavras_relevantes:
            # Retorna a primeira palavra relevante
            return palavras_relevantes[0]
        
        return ""
    
    def _criar_filtros_de_exclusao(self, match_id, dados_feedback):
        """
        REGRA DETERMINÍSTICA: Cria filtros usando PADRÕES ESPECÍFICOS de exclusão
        """
        observacao = dados_feedback.get("observacao", "").lower()
        
        # PADRÕES ESPECÍFICOS que indicam exclusão
        padroes_exclusao = [
            " != ",                   # "anestésico != resina"
            " diferente de ",         # "ortodontia diferente de endodontia"
            " diferente da ",         # "categoria diferente da outra"
            " não é ",                # "resina não é anestésico"
            " não são ",              # "produtos não são iguais"
            " categorias diferentes", # "categorias diferentes"
            " produtos diferentes",   # "produtos diferentes"
            " especialidades diferentes", # "especialidades diferentes"
            " usos diferentes",       # "usos diferentes"
            " incompatíveis",         # "produtos incompatíveis"
            " distintos",             # "produtos distintos"
            " separados"              # "devem ficar separados"
        ]
        
        print(f"🔍 Analisando feedback de exclusão: '{observacao}'")
        
        # Verifica se contém padrões de exclusão
        contem_exclusao = any(padrao in observacao for padrao in padroes_exclusao)
        
        if not contem_exclusao:
            print("   Nenhum padrão de exclusão encontrado, usando análise por produto")
        
        try:
            # Carrega produtos do match problemático
            produtos = self._obter_produtos_do_match(match_id)
            if len(produtos) < 2:
                return []
            
            novos_filtros = []
            
            # Se encontrou padrão de exclusão, processa de forma mais específica
            if contem_exclusao:
                palavras_exclusao = self._extrair_palavras_de_exclusao(observacao, padroes_exclusao)
                print(f"   Palavras de exclusão identificadas: {palavras_exclusao}")
                
                # Cria filtros específicos baseados nas palavras identificadas
                for palavra1 in palavras_exclusao:
                    for palavra2 in palavras_exclusao:
                        if palavra1 != palavra2:
                            filtro = {
                                "palavra1": palavra1,
                                "palavra2": palavra2,
                                "motivo": f"exclusao_explicita_{observacao[:30]}",
                                "confianca": 0.95,  # Alta confiança - usuário foi explícito
                                "timestamp": datetime.now().isoformat(),
                                "match_origem": match_id,
                                "tipo": "exclusao_explicita"
                            }
                            
                            if not self._filtro_existe(filtro):
                                self.filtros_exclusao.append(filtro)
                                novos_filtros.append(filtro)
                                print(f"Filtro EXPLÍCITO criado: '{palavra1}' ≠ '{palavra2}'")
            
            # Análise adicional por produtos (método existente)
            for i in range(len(produtos)):
                for j in range(i + 1, len(produtos)):
                    produto1 = produtos[i]
                    produto2 = produtos[j]
                    
                    palavras1 = self._extrair_palavras_chave(produto1.get("nome", ""))
                    palavras2 = self._extrair_palavras_chave(produto2.get("nome", ""))
                    
                    # Identifica palavras que não devem ser agrupadas
                    for p1 in palavras1:
                        for p2 in palavras2:
                            if p1 != p2 and len(p1) > 3 and len(p2) > 3:
                                filtro = {
                                    "palavra1": p1,
                                    "palavra2": p2,
                                    "motivo": dados_feedback.get("observacao", "falso_positivo"),
                                    "confianca": 0.7,  # Confiança média - inferido automaticamente
                                    "timestamp": datetime.now().isoformat(),
                                    "match_origem": match_id,
                                    "tipo": "exclusao_inferida"
                                }
                                
                                # Verifica se filtro já existe
                                if not self._filtro_existe(filtro):
                                    self.filtros_exclusao.append(filtro)
                                    novos_filtros.append(filtro)
                                    print(f"Filtro INFERIDO criado: '{p1}' ≠ '{p2}'")
        
            return novos_filtros
            
        except Exception as e:
            print(f"Erro ao criar filtros para {match_id}: {e}")
            return []
    
    def _extrair_palavras_de_exclusao(self, observacao, padroes_exclusao):
        """Extrai palavras específicas mencionadas em padrões de exclusão"""
        palavras_encontradas = []
        
        for padrao in padroes_exclusao:
            if padrao in observacao:
                if padrao in [" != "]:
                    # Para símbolos, pega palavras antes e depois
                    partes = observacao.split(padrao)
                    if len(partes) >= 2:
                        palavra1 = self._limpar_palavra_para_sinonimo(partes[0])
                        palavra2 = self._limpar_palavra_para_sinonimo(partes[1])
                        if palavra1: palavras_encontradas.append(palavra1)
                        if palavra2: palavras_encontradas.append(palavra2)
                
                elif "diferente" in padrao:
                    # Para "diferente de", pega palavras relevantes
                    partes = observacao.split(padrao)
                    for parte in partes:
                        palavra = self._limpar_palavra_para_sinonimo(parte)
                        if palavra: palavras_encontradas.append(palavra)
                
                elif "não é" in padrao or "não são" in padrao:
                    # Para negações, analisa contexto
                    import re
                    # Procura padrões como "X não é Y"
                    match = re.search(r'(\w+)\s+não\s+(é|são)\s+(\w+)', observacao)
                    if match:
                        palavras_encontradas.extend([match.group(1), match.group(3)])
        
        return list(set(palavras_encontradas))  # Remove duplicatas
        try:
            # Carrega produtos do match problemático
            produtos = self._obter_produtos_do_match(match_id)
            if len(produtos) < 2:
                return []
            
            novos_filtros = []
            
            # Extrai palavras-chave de cada produto
            for i in range(len(produtos)):
                for j in range(i + 1, len(produtos)):
                    produto1 = produtos[i]
                    produto2 = produtos[j]
                    
                    palavras1 = self._extrair_palavras_chave(produto1.get("nome", ""))
                    palavras2 = self._extrair_palavras_chave(produto2.get("nome", ""))
                    
                    # Identifica palavras que não devem ser agrupadas
                    for p1 in palavras1:
                        for p2 in palavras2:
                            if p1 != p2 and len(p1) > 3 and len(p2) > 3:
                                filtro = {
                                    "palavra1": p1,
                                    "palavra2": p2,
                                    "motivo": dados_feedback.get("observacao", "falso_positivo"),
                                    "confianca": 0.8,
                                    "timestamp": datetime.now().isoformat(),
                                    "match_origem": match_id
                                }
                                
                                # Verifica se filtro já existe
                                if not self._filtro_existe(filtro):
                                    self.filtros_exclusao.append(filtro)
                                    novos_filtros.append(filtro)
                                    print(f"Filtro criado: '{p1}' ≠ '{p2}'")
            
            return novos_filtros
            
        except Exception as e:
            print(f"Erro ao criar filtros para {match_id}: {e}")
            return []
    
    def _obter_produtos_do_match(self, match_id):
        """Carrega produtos de um match específico"""
        try:
            conn = sqlite3.connect('match_crew.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id_bids, nome_produto FROM produtos_mestre 
                WHERE id = ?
            """, (match_id,))
            
            resultado = cursor.fetchone()
            if not resultado:
                conn.close()
                return []
            
            id_bids, nome_produto = resultado
            ids = json.loads(id_bids)
            
            # Carrega produtos detalhados do mesmo banco
            placeholders = ','.join(['?' for _ in ids])
            cursor.execute(f"""
                SELECT id, nome, categoria, marca 
                FROM produtos 
                WHERE id IN ({placeholders})
            """, ids)
            
            produtos = []
            for row in cursor.fetchall():
                produtos.append({
                    "id_bid": row[0],
                    "nome": row[1],
                    "categoria": row[2],
                    "marca": row[3]
                })
            
            conn.close()
            return produtos
            
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            return []
    
    def _extrair_palavras_chave(self, texto):
        """Extrai palavras-chave relevantes de um texto"""
        import re
        
        # Remove pontuação e normaliza
        texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
        palavras = texto_limpo.split()
        
        # Filtra palavras relevantes (> 3 caracteres)
        stop_words = {"para", "com", "sem", "por", "ate", "desde", "apos", "dental", "odonto"}
        palavras_relevantes = [
            p for p in palavras 
            if len(p) > 3 and p not in stop_words
        ]
        
        return palavras_relevantes[:5]  # Máximo 5 palavras por produto
    
    def _limpar_palavra(self, palavra):
        """Limpa e normaliza uma palavra"""
        import re
        palavra = re.sub(r'[^\w]', '', palavra.strip().lower())
        return palavra if len(palavra) > 2 else ""
    
    def _filtro_existe(self, novo_filtro):
        """Verifica se filtro já existe"""
        for filtro in self.filtros_exclusao:
            if ((filtro["palavra1"] == novo_filtro["palavra1"] and filtro["palavra2"] == novo_filtro["palavra2"]) or
                (filtro["palavra1"] == novo_filtro["palavra2"] and filtro["palavra2"] == novo_filtro["palavra1"])):
                return True
        return False
    
    def aplicar_filtros_no_matching(self, produto1_nome, produto2_nome):
        """
        APLICA OS FILTROS GERADOS: Verifica se dois produtos devem ser agrupados
        """
        palavras1 = self._extrair_palavras_chave(produto1_nome)
        palavras2 = self._extrair_palavras_chave(produto2_nome)
        
        # Verifica todos os filtros de exclusão
        for filtro in self.filtros_exclusao:
            p1, p2 = filtro["palavra1"], filtro["palavra2"]
            
            # Se encontrar palavras problemáticas, REJEITA o match
            if ((p1 in palavras1 and p2 in palavras2) or 
                (p2 in palavras1 and p1 in palavras2)):
                return False, f"Filtro aplicado: {p1} ≠ {p2}"
        
        return True, "Match permitido"
    
    def expandir_com_sinonimos_aprendidos(self, texto):
        """
        APLICA OS SINÔNIMOS GERADOS: Expande texto com sinônimos aprendidos
        """
        palavras = texto.lower().split()
        texto_expandido = []
        
        for palavra in palavras:
            texto_expandido.append(palavra)
            
            # Adiciona sinônimos aprendidos
            if palavra in self.sinonimos_aprendidos:
                texto_expandido.extend(self.sinonimos_aprendidos[palavra])
        
        return " ".join(set(texto_expandido))
    
    def gerar_relatorio_regras(self):
        """Gera relatório das regras criadas"""
        relatorio = f"""
# RELATÓRIO DE REGRAS GERADAS
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## FILTROS DE EXCLUSÃO
Total: {len(self.filtros_exclusao)}

"""
        
        for i, filtro in enumerate(self.filtros_exclusao[:10], 1):  # Top 10
            relatorio += f"{i}. **{filtro['palavra1']}** ≠ **{filtro['palavra2']}**\n"
            relatorio += f"   - Motivo: {filtro['motivo']}\n"
            relatorio += f"   - Confiança: {filtro['confianca']}\n\n"
        
        relatorio += f"""
## SINÔNIMOS APRENDIDOS
Total: {len(self.sinonimos_aprendidos)}

"""
        
        for palavra, sinonimos in list(self.sinonimos_aprendidos.items())[:10]:
            relatorio += f"- **{palavra}**: {', '.join(sinonimos)}\n"
        
        relatorio += f"""

## IMPACTO ESPERADO
- Redução de falsos positivos: ~{len(self.filtros_exclusao) * 5}
- Aumento de matches válidos: ~{len(self.sinonimos_aprendidos) * 20}
- Melhoria na precisão: ~2-5%

## APLICAÇÃO
As regras são aplicadas automaticamente na próxima execução do matching.
"""
        
        return relatorio

def demonstrar_aplicacao():
    """Demonstra como o sistema funciona na prática"""
    print("DEMONSTRAÇÃO: APLICAÇÃO DE FEEDBACK SEM IA")
    print("=" * 60)
    
    aplicador = AplicadorFeedbackDeterministico()
    
    # Processa feedback
    stats = aplicador.processar_feedback_humano()
    
    if stats["regras_geradas"] > 0:
        print(f"\nTESTANDO REGRAS GERADAS:")
        print("-" * 40)
        
        # Testa filtros
        exemplos_teste = [
            ("Resina Charisma Classic", "Composite Z350"),
            ("Anestésico Lidocaína", "Resina Fotopolimerizável"),
            ("Broca Diamantada", "Disco de Corte")
        ]
        
        for produto1, produto2 in exemplos_teste:
            permitido, motivo = aplicador.aplicar_filtros_no_matching(produto1, produto2)
            status = "PERMITE" if permitido else "BLOQUEIA"
            print(f"{status}: '{produto1}' vs '{produto2}'")
            print(f"         Motivo: {motivo}")
        
        # Testa expansão semântica
        print(f"\nTESTANDO SINÔNIMOS APRENDIDOS:")
        print("-" * 40)
        
        exemplos_expansao = ["resina charisma", "composite z350", "anestésico local"]
        for texto in exemplos_expansao:
            expandido = aplicador.expandir_com_sinonimos_aprendidos(texto)
            if expandido != texto:
                print(f"'{texto}' → '{expandido}'")
        
        # Gera relatório
        relatorio = aplicador.gerar_relatorio_regras()
        relatorio_file = Path(f"data/relatorio_regras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(relatorio_file, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        print(f"\nRelatório salvo: {relatorio_file}")
    
    else:
        print("\nNenhuma regra foi gerada (feedback insuficiente)")

if __name__ == "__main__":
    demonstrar_aplicacao()