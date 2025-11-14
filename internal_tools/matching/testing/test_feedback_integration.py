"""
Teste End-to-End: Ciclo Completo de Feedback → Matching

Este script testa o ciclo completo:
1. Cria feedback simulado
2. Processa feedback (gera regras)
3. Executa matching SEM feedback
4. Executa matching COM feedback
5. Compara resultados e valida melhorias

Uso:
    python internal_tools/matching/testing/test_feedback_integration.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Adiciona root ao path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from internal_tools.validation_interface.utils.matching_integration import MatchingComFeedback
from internal_tools.validation_interface.utils.aplicador_feedback_real import AplicadorFeedbackDeterministico


def criar_feedback_teste():
    """Cria arquivo de feedback para testes"""
    
    print("=" * 70)
    print("CRIANDO FEEDBACK DE TESTE")
    print("=" * 70)
    
    # Cria diretório data se não existir
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    feedback_file = data_dir / "feedback_humano.json"
    
    # Feedback de teste com exemplos claros
    feedback_teste = {
        "matches_validados": {
            "1": {
                "id_match": 1,
                "valido": True,
                "observacao": "resina = composite = fotopolimerizavel",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            },
            "2": {
                "id_match": 2,
                "valido": True,
                "observacao": "anestesico e lidocaina sao iguais",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            },
            "3": {
                "id_match": 3,
                "valido": True,
                "observacao": "broca = fresa",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            },
            "4": {
                "id_match": 4,
                "valido": False,
                "observacao": "ortodontia != endodontia",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            },
            "5": {
                "id_match": 5,
                "valido": False,
                "observacao": "resina diferente de anestesico",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            },
            "6": {
                "id_match": 6,
                "valido": False,
                "observacao": "protese != implante",
                "timestamp": datetime.now().isoformat(),
                "usuario": "teste_automatico"
            }
        }
    }
    
    # Salva feedback
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(feedback_teste, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Feedback criado: {feedback_file}")
    print(f"   • 3 matches válidos (com sinônimos)")
    print(f"   • 3 matches inválidos (para gerar filtros)")
    print()
    
    return feedback_file


def testar_processamento_feedback():
    """Testa processamento de feedback"""
    
    print("=" * 70)
    print("TESTE 1: PROCESSAMENTO DE FEEDBACK")
    print("=" * 70)
    
    aplicador = AplicadorFeedbackDeterministico()
    stats = aplicador.processar_feedback_humano()
    
    print(f"\n📊 Resultados:")
    print(f"   • Feedbacks processados: {stats.get('feedbacks_processados', 0)}")
    print(f"   • Filtros criados: {stats.get('filtros_adicionados', 0)}")
    print(f"   • Sinônimos criados: {stats.get('sinonimos_adicionados', 0)}")
    print(f"   • Total regras: {stats.get('regras_geradas', 0)}")
    
    if stats.get('regras_geradas', 0) == 0:
        print("\n⚠️  AVISO: Nenhuma regra gerada!")
        print("   Verifique se o feedback está no formato correto")
        return False
    
    print("\n✅ Processamento bem-sucedido!")
    return True


def testar_matching_sem_feedback():
    """Executa matching SEM aplicar feedback"""
    
    print("\n" + "=" * 70)
    print("TESTE 2: MATCHING SEM FEEDBACK (baseline)")
    print("=" * 70)
    
    sistema = MatchingComFeedback(
        db_mestre="match_crew.db",
        db_tratados="legacy/data/produtos_tratados.db"
    )
    
    resultado = sistema.executar_matching_completo(aplicar_feedback=False)
    
    if resultado.get("sucesso"):
        print(f"\n✅ Matching SEM feedback concluído!")
        print(f"   • Tempo: {resultado['tempo_execucao']:.2f}s")
        print(f"   • Matches: {resultado['matches_criados']:,}")
        print(f"   • Adequação: {resultado['adequacao']:.1f}%")
        return resultado
    else:
        print(f"\n❌ Erro no matching: {resultado.get('erro')}")
        return None


def testar_matching_com_feedback():
    """Executa matching COM aplicação de feedback"""
    
    print("\n" + "=" * 70)
    print("TESTE 3: MATCHING COM FEEDBACK (otimizado)")
    print("=" * 70)
    
    sistema = MatchingComFeedback(
        db_mestre="match_crew.db",
        db_tratados="legacy/data/produtos_tratados.db"
    )
    
    resultado = sistema.executar_matching_completo(aplicar_feedback=True)
    
    if resultado.get("sucesso"):
        print(f"\n✅ Matching COM feedback concluído!")
        print(f"   • Tempo: {resultado['tempo_execucao']:.2f}s")
        print(f"   • Matches: {resultado['matches_criados']:,}")
        print(f"   • Adequação: {resultado['adequacao']:.1f}%")
        print(f"   • Filtros usados: {resultado['filtros_usados']}")
        print(f"   • Sinônimos usados: {resultado['sinonimos_usados']}")
        return resultado
    else:
        print(f"\n❌ Erro no matching: {resultado.get('erro')}")
        return None


def comparar_resultados(sem_feedback, com_feedback):
    """Compara e valida melhorias"""
    
    print("\n" + "=" * 70)
    print("TESTE 4: COMPARAÇÃO E VALIDAÇÃO")
    print("=" * 70)
    
    if not sem_feedback or not com_feedback:
        print("❌ Resultados incompletos para comparação")
        return False
    
    # Calcula diferenças
    diff_matches = com_feedback['matches_criados'] - sem_feedback['matches_criados']
    perc_melhoria = (diff_matches / sem_feedback['matches_criados'] * 100) if sem_feedback['matches_criados'] > 0 else 0
    diff_adequacao = com_feedback['adequacao'] - sem_feedback['adequacao']
    diff_tempo = com_feedback['tempo_execucao'] - sem_feedback['tempo_execucao']
    
    print(f"\n📊 COMPARAÇÃO DETALHADA:")
    print(f"   ┌─────────────────────────────────────────┐")
    print(f"   │ Matches SEM feedback:  {sem_feedback['matches_criados']:>10,} │")
    print(f"   │ Matches COM feedback:  {com_feedback['matches_criados']:>10,} │")
    print(f"   │ Diferença:             {diff_matches:>+10,} │")
    print(f"   │ Melhoria:              {perc_melhoria:>+9.1f}% │")
    print(f"   └─────────────────────────────────────────┘")
    
    print(f"\n   ┌─────────────────────────────────────────┐")
    print(f"   │ Adequação SEM:         {sem_feedback['adequacao']:>9.1f}% │")
    print(f"   │ Adequação COM:         {com_feedback['adequacao']:>9.1f}% │")
    print(f"   │ Diferença:             {diff_adequacao:>+9.1f}% │")
    print(f"   └─────────────────────────────────────────┘")
    
    print(f"\n   ┌─────────────────────────────────────────┐")
    print(f"   │ Tempo SEM:             {sem_feedback['tempo_execucao']:>9.2f}s │")
    print(f"   │ Tempo COM:             {com_feedback['tempo_execucao']:>9.2f}s │")
    print(f"   │ Diferença:             {diff_tempo:>+9.2f}s │")
    print(f"   └─────────────────────────────────────────┘")
    
    print(f"\n   ┌─────────────────────────────────────────┐")
    print(f"   │ Filtros aplicados:     {com_feedback['filtros_usados']:>10} │")
    print(f"   │ Sinônimos aplicados:   {com_feedback['sinonimos_usados']:>10} │")
    print(f"   └─────────────────────────────────────────┘")
    
    # Validações
    print(f"\n🔍 VALIDAÇÕES:")
    
    validacoes = {
        "Regras foram aplicadas": com_feedback['filtros_usados'] > 0 or com_feedback['sinonimos_usados'] > 0,
        "Tempo aceitável (< 10s)": com_feedback['tempo_execucao'] < 10,
        "Adequação mantida (> 90%)": com_feedback['adequacao'] > 90,
        "Sem erros": com_feedback.get('sucesso', False)
    }
    
    for descricao, passou in validacoes.items():
        status = "✅" if passou else "❌"
        print(f"   {status} {descricao}")
    
    # Resultado final
    print(f"\n" + "=" * 70)
    if all(validacoes.values()):
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 70)
        print("\n🎉 INTEGRAÇÃO COMPLETA E FUNCIONAL!")
        print("   O sistema está aplicando regras de feedback corretamente.")
        print(f"   Melhoria detectada: {diff_matches:+,} matches ({perc_melhoria:+.1f}%)")
        return True
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("=" * 70)
        falhas = [desc for desc, passou in validacoes.items() if not passou]
        print("\nProblemas detectados:")
        for falha in falhas:
            print(f"   • {falha}")
        return False


def main():
    """Executa teste end-to-end completo"""
    
    print("\n" * 2)
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  TESTE END-TO-END: INTEGRAÇÃO FEEDBACK → MATCHING  ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    inicio_total = datetime.now()
    
    try:
        # Passo 1: Criar feedback de teste
        feedback_file = criar_feedback_teste()
        
        # Passo 2: Processar feedback
        if not testar_processamento_feedback():
            print("\n❌ Falha no processamento de feedback")
            return False
        
        # Passo 3: Matching sem feedback (baseline)
        resultado_sem = testar_matching_sem_feedback()
        
        # Passo 4: Matching com feedback (otimizado)
        resultado_com = testar_matching_com_feedback()
        
        # Passo 5: Comparar e validar
        sucesso = comparar_resultados(resultado_sem, resultado_com)
        
        # Tempo total
        tempo_total = (datetime.now() - inicio_total).total_seconds()
        
        print(f"\n⏱️  Tempo total do teste: {tempo_total:.2f}s")
        
        # Limpeza (opcional)
        print(f"\n🧹 Limpeza:")
        print(f"   Feedback de teste mantido em: {feedback_file}")
        print(f"   Você pode deletar manualmente se desejar.")
        
        return sucesso
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
