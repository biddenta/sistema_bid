import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Adiciona root ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Importar dicionário de sinônimos do local correto
try:
    from internal_tools.validation_interface.utils.dicionario_sinonimos import (
        expandir_sinonimos, 
        expandir_texto_com_sinonimos
    )
except ImportError:
    # Fallback: tentar import relativo
    from .dicionario_sinonimos import expandir_sinonimos, expandir_texto_com_sinonimos

# Manter compatibilidade
try:
    SINONIMOS_PRODUTOS_DENTAIS = {}
    ABREVIACOES = {}
except:
    pass

class ProcessadorFeedback:
    """Processa e aplica feedback humano ao sistema"""
    
    def __init__(self):
        self.feedback_file = Path("data/feedback_humano.json")
        self.sinonimos_atualizados_file = Path("data/sinonimos_atualizados.json")
        
    def carregar_feedback(self):
        """Carrega feedback salvo"""
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"matches_validados": {}, "sinonimos_sugeridos": {}}
    
    def analisar_falsos_positivos(self):
        """Analisa padrões de falsos positivos"""
        feedback = self.carregar_feedback()
        validados = feedback.get("matches_validados", {})
        
        falsos_positivos = []
        matches_validos = []
        
        for id_match, dados in validados.items():
            if dados.get("valido", False):
                matches_validos.append({
                    "id_match": id_match,
                    "observacao": dados.get("observacao", ""),
                    "timestamp": dados.get("timestamp", "")
                })
            else:
                falsos_positivos.append({
                    "id_match": id_match,
                    "observacao": dados.get("observacao", ""),
                    "timestamp": dados.get("timestamp", "")
                })
        
        return {
            "total_avaliados": len(validados),
            "falsos_positivos": falsos_positivos,
            "matches_validos": matches_validos,
            "taxa_precisao": len(matches_validos) / len(validados) if validados else 0
        }
    
    def extrair_padroes_problematicos(self, falsos_positivos):
        """Extrai padrões comuns em falsos positivos"""
        padroes = defaultdict(int)
        
        # Conecta ao banco para analisar os matches problemáticos
        conn = sqlite3.connect('data/produtos_mestre.db')
        
        for fp in falsos_positivos:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nome_produto, categoria, marca, id_bids 
                    FROM produtos_mestre 
                    WHERE id_match = ?
                """, (fp["id_match"],))
                
                resultado = cursor.fetchone()
                if resultado:
                    nome, categoria, marca, id_bids = resultado
                    
                    # Analisa padrões problemáticos
                    palavras = nome.lower().split()
                    for palavra in palavras:
                        if len(palavra) > 3:  # Palavras significativas
                            padroes[f"palavra_{palavra}"] += 1
                    
                    padroes[f"categoria_{categoria}"] += 1
                    if marca:
                        padroes[f"marca_{marca}"] += 1
                        
            except Exception as e:
                print(f"Erro ao analisar {fp['id_match']}: {e}")
        
        conn.close()
        
        # Retorna padrões mais comuns
        return dict(sorted(padroes.items(), key=lambda x: x[1], reverse=True))
    
    def gerar_sinonimos_do_feedback(self):
        """Gera novos sinônimos baseado no feedback"""
        feedback = self.carregar_feedback()
        novos_sinonimos = {}
        
        # Analisa observações de matches válidos para extrair sinônimos
        for id_match, dados in feedback.get("matches_validados", {}).items():
            if dados.get("valido", False):
                observacao = dados.get("observacao", "").lower()
                
                # Procura por padrões de sinônimos nas observações
                if "=" in observacao or "similar" in observacao or "mesmo que" in observacao:
                    # Extrai possíveis sinônimos das observações
                    partes = observacao.replace("=", "|").replace(" e ", "|").split("|")
                    if len(partes) >= 2:
                        base = partes[0].strip()
                        sinonimos = [p.strip() for p in partes[1:] if p.strip()]
                        if base and sinonimos:
                            novos_sinonimos[base] = sinonimos
        
        return novos_sinonimos
    
    def aplicar_melhorias_automaticas(self):
        """Aplica melhorias automáticas baseadas no feedback"""
        feedback = self.carregar_feedback()
        analise = self.analisar_falsos_positivos()
        
        melhorias = {
            "timestamp": datetime.now().isoformat(),
            "total_feedback": analise["total_avaliados"],
            "precisao_atual": analise["taxa_precisao"],
            "melhorias_aplicadas": []
        }
        
        # 1. Extrai novos sinônimos
        novos_sinonimos = self.gerar_sinonimos_do_feedback()
        if novos_sinonimos:
            melhorias["melhorias_aplicadas"].append({
                "tipo": "novos_sinonimos",
                "quantidade": len(novos_sinonimos),
                "sinonimos": novos_sinonimos
            })
        
        # 2. Identifica padrões problemáticos
        if analise["falsos_positivos"]:
            padroes_problematicos = self.extrair_padroes_problematicos(analise["falsos_positivos"])
            melhorias["melhorias_aplicadas"].append({
                "tipo": "padroes_problematicos",
                "padroes": dict(list(padroes_problematicos.items())[:10])  # Top 10
            })
        
        # 3. Calcula métricas de qualidade
        melhorias["metricas_qualidade"] = {
            "taxa_falsos_positivos": len(analise["falsos_positivos"]) / analise["total_avaliados"] if analise["total_avaliados"] > 0 else 0,
            "matches_por_validacao": analise["total_avaliados"],
            "necessita_retreino": analise["taxa_precisao"] < 0.85
        }
        
        # Salva melhorias
        melhorias_file = Path("data/melhorias_aplicadas.json")
        with open(melhorias_file, 'w', encoding='utf-8') as f:
            json.dump(melhorias, f, ensure_ascii=False, indent=2)
        
        return melhorias
    
    def gerar_relatorio_feedback(self):
        """Gera relatório completo do feedback"""
        analise = self.analisar_falsos_positivos()
        melhorias = self.aplicar_melhorias_automaticas()
        
        relatorio = f"""
# RELATÓRIO DE FEEDBACK HUMANO
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## 📊 ESTATÍSTICAS GERAIS
- **Total de matches avaliados**: {analise['total_avaliados']:,}
- **Matches válidos**: {len(analise['matches_validos']):,}
- **Falsos positivos**: {len(analise['falsos_positivos']):,}
- **Taxa de precisão**: {analise['taxa_precisao']:.1%}

## ✅ QUALIDADE DO ALGORITMO
"""
        
        if analise['taxa_precisao'] >= 0.90:
            relatorio += "🎊 **EXCELENTE** - Algoritmo com alta precisão\n"
        elif analise['taxa_precisao'] >= 0.80:
            relatorio += "✅ **BOM** - Algoritmo funcionando bem\n"
        elif analise['taxa_precisao'] >= 0.70:
            relatorio += "⚠️ **REGULAR** - Necessita otimizações\n"
        else:
            relatorio += "❌ **CRÍTICO** - Necessita revisão urgente\n"
        
        relatorio += f"\n## 🔧 MELHORIAS APLICADAS\n"
        for melhoria in melhorias.get("melhorias_aplicadas", []):
            if melhoria["tipo"] == "novos_sinonimos":
                relatorio += f"- **Novos sinônimos**: {melhoria['quantidade']} adicionados\n"
            elif melhoria["tipo"] == "padroes_problematicos":
                relatorio += f"- **Padrões problemáticos**: {len(melhoria['padroes'])} identificados\n"
        
        relatorio += f"\n## 💡 RECOMENDAÇÕES\n"
        if melhorias["metricas_qualidade"]["necessita_retreino"]:
            relatorio += "- 🔄 **Retreinar o algoritmo** com o feedback acumulado\n"
        
        if len(analise['falsos_positivos']) > 5:
            relatorio += "- 📊 **Analisar padrões** de falsos positivos recorrentes\n"
        
        if analise['total_avaliados'] < 50:
            relatorio += "- 📈 **Coletar mais feedback** para análises mais robustas\n"
        
        relatorio += f"\n## 📋 PRÓXIMOS PASSOS\n"
        relatorio += "1. Revisar sinônimos sugeridos pelos usuários\n"
        relatorio += "2. Implementar filtros para padrões problemáticos\n"
        relatorio += "3. Continuar coletando feedback para melhoria contínua\n"
        relatorio += "4. Executar teste de regressão após mudanças\n"
        
        return relatorio
    
    def salvar_relatorio(self):
        """Salva relatório em arquivo"""
        relatorio = self.gerar_relatorio_feedback()
        
        relatorio_file = Path(f"data/relatorio_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(relatorio_file, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        
        return relatorio_file

def main():
    """Execução principal"""
    print("PROCESSADOR DE FEEDBACK HUMANO")
    print("=" * 50)
    
    processador = ProcessadorFeedback()
    
    # Analisa feedback
    print("Analisando feedback...")
    analise = processador.analisar_falsos_positivos()
    
    print(f"   • Total avaliados: {analise['total_avaliados']:,}")
    print(f"   • Válidos: {len(analise['matches_validos']):,}")
    print(f"   • Falsos positivos: {len(analise['falsos_positivos']):,}")
    print(f"   • Precisão: {analise['taxa_precisao']:.1%}")
    
    if analise['total_avaliados'] == 0:
        print("\nNenhum feedback encontrado!")
        print("Use a interface Streamlit para avaliar matches primeiro.")
        return
    
    # Aplica melhorias
    print("\n🔧 Aplicando melhorias...")
    melhorias = processador.aplicar_melhorias_automaticas()
    
    for melhoria in melhorias.get("melhorias_aplicadas", []):
        print(f"   {melhoria['tipo']}: {melhoria.get('quantidade', 'aplicado')}")
    
    # Gera relatório
    print("\nGerando relatório...")
    relatorio_file = processador.salvar_relatorio()
    print(f"   Salvo em: {relatorio_file}")
    
    # Exibe resumo
    print(f"\nPROCESSAMENTO CONCLUÍDO!")
    print(f"Abra o arquivo '{relatorio_file}' para ver o relatório completo")

if __name__ == "__main__":
    main()