"""
Análise de Matches Manuais vs Automáticos
Identifica padrões e oportunidades de melhoria no algoritmo
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sqlite3
import json
from collections import defaultdict, Counter
import re
from difflib import SequenceMatcher


def analisar_matches_manuais():
    """Analisa matches manuais para identificar padrões"""
    
    print("\n" + "=" * 100)
    print("🔍 ANÁLISE DE MATCHES MANUAIS - OPORTUNIDADES DE MELHORIA")
    print("=" * 100)
    
    conn = sqlite3.connect('match_crew.db')
    cursor = conn.cursor()
    
    # Buscar matches manuais
    cursor.execute("""
        SELECT id_match, id_bids, nome_produto, marca, categoria, 
               total_sites, total_produtos, score_match
        FROM produtos_mestre
        WHERE metodo_matching = 'importacao_manual'
        ORDER BY total_produtos DESC
    """)
    
    matches_manuais = cursor.fetchall()
    
    print(f"\n📊 Total de matches manuais: {len(matches_manuais):,}")
    
    # Analisar cada match manual
    analises = {
        'variacoes_nome': [],
        'variacoes_marca': [],
        'diferentes_categorias': [],
        'multiplos_sites': [],
        'casos_complexos': [],
        'falsos_negativos': []  # Matches que o algoritmo NÃO pegou
    }
    
    print(f"\n🔄 Analisando padrões dos matches manuais...")
    
    for match in matches_manuais:
        id_match = match[0]
        id_bids = json.loads(match[1])
        nome_grupo = match[2]
        marca_grupo = match[3]
        categoria_grupo = match[4]
        total_sites = match[5]
        total_produtos = match[6]
        
        # Buscar produtos do grupo
        cursor.execute(f"""
            SELECT id, nome, marca, categoria, site, url
            FROM produtos
            WHERE id IN ({','.join('?' * len(id_bids))})
        """, id_bids)
        
        produtos = cursor.fetchall()
        
        if len(produtos) < 2:
            continue
        
        # Analisar variações de nome
        nomes = [p[1] for p in produtos]
        nomes_unicos = set(nomes)
        
        if len(nomes_unicos) > 1:
            # Há variação nos nomes
            analise_nome = analisar_variacoes_nome(nomes)
            analises['variacoes_nome'].append({
                'id_match': id_match,
                'nomes': nomes,
                'analise': analise_nome,
                'produtos': len(produtos)
            })
        
        # Analisar variações de marca
        marcas = [p[2] for p in produtos if p[2]]
        marcas_unicas = set(marcas)
        
        if len(marcas_unicas) > 1:
            analises['variacoes_marca'].append({
                'id_match': id_match,
                'marcas': list(marcas_unicas),
                'produtos': len(produtos)
            })
        
        # Analisar categorias diferentes
        categorias = [p[3] for p in produtos if p[3]]
        categorias_unicas = set(categorias)
        
        if len(categorias_unicas) > 1:
            analises['diferentes_categorias'].append({
                'id_match': id_match,
                'categorias': list(categorias_unicas),
                'produtos': len(produtos)
            })
        
        # Multi-site (3+ sites)
        if total_sites >= 3:
            analises['multiplos_sites'].append({
                'id_match': id_match,
                'nome': nome_grupo,
                'sites': total_sites,
                'produtos': total_produtos
            })
        
        # Verificar se o algoritmo automático pegaria
        seria_detectado = verificar_deteccao_automatica(produtos)
        
        if not seria_detectado:
            analises['falsos_negativos'].append({
                'id_match': id_match,
                'nome': nome_grupo,
                'produtos': produtos,
                'motivo': seria_detectado
            })
    
    # Exibir resultados
    exibir_analises(analises)
    
    # Gerar recomendações
    gerar_recomendacoes(analises, cursor)
    
    conn.close()


def analisar_variacoes_nome(nomes):
    """Analisa padrões nas variações de nome"""
    
    # Normalizar nomes
    nomes_norm = [normalizar_texto(n) for n in nomes]
    
    # Calcular similaridade média
    similaridades = []
    for i in range(len(nomes_norm)):
        for j in range(i + 1, len(nomes_norm)):
            sim = SequenceMatcher(None, nomes_norm[i], nomes_norm[j]).ratio()
            similaridades.append(sim)
    
    sim_media = sum(similaridades) / len(similaridades) if similaridades else 0
    
    # Identificar diferenças
    diferencas = identificar_diferencas(nomes)
    
    return {
        'similaridade_media': sim_media,
        'diferencas': diferencas
    }


def normalizar_texto(texto):
    """Normalização básica"""
    if not texto:
        return ""
    
    import unicodedata
    
    texto = texto.lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    
    # Remover caracteres especiais mas manter números
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()


def identificar_diferencas(nomes):
    """Identifica padrões de diferenças entre nomes"""
    
    diferencas = {
        'preposicoes': False,  # "de", "da", "do"
        'hifen': False,  # Com/sem hífen
        'espacos': False,  # Espaços diferentes
        'abreviacoes': False,  # Abreviações (Ltd, Ltda, etc)
        'numeros_formato': False,  # Números formatados diferente (350 vs 3.5g)
        'ordem_palavras': False,  # Ordem das palavras
    }
    
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            n1 = nomes[i].lower()
            n2 = nomes[j].lower()
            
            # Verificar preposições
            if any(prep in n1 or prep in n2 for prep in [' de ', ' da ', ' do ', ' para ']):
                if n1.replace(' de ', ' ').replace(' da ', ' ').replace(' do ', ' ') == \
                   n2.replace(' de ', ' ').replace(' da ', ' ').replace(' do ', ' '):
                    diferencas['preposicoes'] = True
            
            # Verificar hífen
            if '-' in n1 or '-' in n2:
                if n1.replace('-', ' ') == n2.replace('-', ' '):
                    diferencas['hifen'] = True
            
            # Verificar abreviações
            abrev_map = {'ltda': 'limitada', 'cia': 'companhia', 'ind': 'industria'}
            for abrev, completo in abrev_map.items():
                if (abrev in n1 and completo in n2) or (completo in n1 and abrev in n2):
                    diferencas['abreviacoes'] = True
    
    return diferencas


def verificar_deteccao_automatica(produtos):
    """Verifica se o algoritmo atual detectaria este match"""
    
    # Critérios do algoritmo atual:
    # 1. Categoria deve ser idêntica ou relacionada
    # 2. Marca deve ser coerente
    # 3. Nome deve ter similaridade alta (0.75+)
    
    if len(produtos) < 2:
        return False
    
    # Verificar categorias
    categorias = [p[3] for p in produtos if p[3]]
    if len(set(categorias)) > 1:
        # Categorias diferentes - algoritmo rejeitaria?
        return False
    
    # Verificar marcas
    marcas = [p[2] for p in produtos if p[2]]
    if len(set(marcas)) > 2:
        # Mais de 2 marcas - algoritmo rejeitaria
        return False
    
    # Verificar nomes
    nomes = [normalizar_texto(p[1]) for p in produtos]
    
    # Calcular similaridade mínima entre todos os pares
    min_sim = 1.0
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            sim = SequenceMatcher(None, nomes[i], nomes[j]).ratio()
            min_sim = min(min_sim, sim)
    
    # Se similaridade mínima < 0.75, algoritmo rejeitaria
    if min_sim < 0.75:
        return False
    
    return True


def exibir_analises(analises):
    """Exibe análises detalhadas"""
    
    print(f"\n" + "=" * 100)
    print("📊 RESULTADOS DA ANÁLISE")
    print("=" * 100)
    
    # Variações de nome
    print(f"\n1️⃣  VARIAÇÕES DE NOME ({len(analises['variacoes_nome'])} casos)")
    print("-" * 100)
    
    if analises['variacoes_nome']:
        # Top 10 casos
        casos_nome = sorted(analises['variacoes_nome'], 
                           key=lambda x: x['analise']['similaridade_media'])[:10]
        
        for i, caso in enumerate(casos_nome, 1):
            print(f"\n   Caso {i}:")
            print(f"   Match: {caso['id_match']}")
            print(f"   Similaridade média: {caso['analise']['similaridade_media']:.3f}")
            print(f"   Nomes:")
            for nome in caso['nomes']:
                print(f"      • {nome}")
            
            difs = caso['analise']['diferencas']
            difs_encontradas = [k for k, v in difs.items() if v]
            if difs_encontradas:
                print(f"   Diferenças: {', '.join(difs_encontradas)}")
    
    # Variações de marca
    print(f"\n\n2️⃣  VARIAÇÕES DE MARCA ({len(analises['variacoes_marca'])} casos)")
    print("-" * 100)
    
    if analises['variacoes_marca']:
        counter_marcas = Counter()
        for caso in analises['variacoes_marca']:
            for marca in caso['marcas']:
                counter_marcas[marca] += 1
        
        print("\n   Top marcas com variações:")
        for marca, count in counter_marcas.most_common(10):
            print(f"      {marca}: {count} vezes")
        
        # Exemplo
        print(f"\n   Exemplo:")
        caso_ex = analises['variacoes_marca'][0]
        print(f"      Match: {caso_ex['id_match']}")
        print(f"      Marcas: {', '.join(caso_ex['marcas'])}")
    
    # Categorias diferentes
    print(f"\n\n3️⃣  CATEGORIAS DIFERENTES ({len(analises['diferentes_categorias'])} casos)")
    print("-" * 100)
    
    if analises['diferentes_categorias']:
        print(f"\n   ⚠️  Algoritmo rejeita categorias diferentes!")
        print(f"   Casos encontrados: {len(analises['diferentes_categorias'])}")
        
        # Exemplos
        for i, caso in enumerate(analises['diferentes_categorias'][:5], 1):
            print(f"\n   Caso {i}:")
            print(f"      Match: {caso['id_match']}")
            print(f"      Categorias: {' | '.join(caso['categorias'])}")
    
    # Multi-site
    print(f"\n\n4️⃣  MULTI-SITE ({len(analises['multiplos_sites'])} casos com 3+ sites)")
    print("-" * 100)
    
    if analises['multiplos_sites']:
        # Top por número de sites
        top_sites = sorted(analises['multiplos_sites'], 
                          key=lambda x: x['sites'], reverse=True)[:10]
        
        print(f"\n   Top 10 por sites:")
        for caso in top_sites:
            print(f"      {caso['sites']} sites | {caso['produtos']} produtos | {caso['nome'][:50]}")
    
    # Falsos negativos
    print(f"\n\n5️⃣  FALSOS NEGATIVOS ({len(analises['falsos_negativos'])} casos)")
    print("-" * 100)
    print(f"   Matches manuais que o algoritmo NÃO detectaria automaticamente")
    
    if analises['falsos_negativos']:
        print(f"\n   Total: {len(analises['falsos_negativos'])} casos ({len(analises['falsos_negativos']) / len(analises['variacoes_nome']) * 100:.1f}%)")
        
        # Exemplos
        for i, caso in enumerate(analises['falsos_negativos'][:5], 1):
            print(f"\n   Caso {i}:")
            print(f"      Match: {caso['id_match']}")
            print(f"      Nome: {caso['nome'][:60]}")
            print(f"      Produtos: {len(caso['produtos'])}")


def gerar_recomendacoes(analises, cursor):
    """Gera recomendações de melhorias"""
    
    print(f"\n\n" + "=" * 100)
    print("💡 RECOMENDAÇÕES DE MELHORIA")
    print("=" * 100)
    
    recomendacoes = []
    
    # Recomendação 1: Preposições
    casos_preposicoes = sum(1 for caso in analises['variacoes_nome'] 
                           if caso['analise']['diferencas'].get('preposicoes'))
    
    if casos_preposicoes > 10:
        recomendacoes.append({
            'prioridade': 'ALTA',
            'casos': casos_preposicoes,
            'titulo': 'Normalizar preposições',
            'descricao': 'Remover/normalizar "de", "da", "do", "para" antes da comparação',
            'impacto': f'+{casos_preposicoes} matches potenciais',
            'implementacao': 'Adicionar na função _normalizar_essencial()'
        })
    
    # Recomendação 2: Hífens
    casos_hifen = sum(1 for caso in analises['variacoes_nome'] 
                     if caso['analise']['diferencas'].get('hifen'))
    
    if casos_hifen > 5:
        recomendacoes.append({
            'prioridade': 'MÉDIA',
            'casos': casos_hifen,
            'titulo': 'Normalizar hífens',
            'descricao': 'Converter hífens em espaços antes da comparação',
            'impacto': f'+{casos_hifen} matches potenciais',
            'implementacao': 'Adicionar na função _normalizar_essencial()'
        })
    
    # Recomendação 3: Categorias relacionadas
    if len(analises['diferentes_categorias']) > 50:
        recomendacoes.append({
            'prioridade': 'ALTA',
            'casos': len(analises['diferentes_categorias']),
            'titulo': 'Expandir categorias relacionadas',
            'descricao': 'Adicionar mais grupos de categorias relacionadas',
            'impacto': f'+{len(analises["diferentes_categorias"])} matches potenciais',
            'implementacao': 'Atualizar _compatibilidade_categoria()'
        })
    
    # Recomendação 4: Threshold adaptativo por padrão
    casos_baixa_sim = sum(1 for caso in analises['variacoes_nome'] 
                         if caso['analise']['similaridade_media'] < 0.75)
    
    if casos_baixa_sim > 20:
        recomendacoes.append({
            'prioridade': 'MÉDIA',
            'casos': casos_baixa_sim,
            'titulo': 'Threshold adaptativo mais agressivo',
            'descricao': 'Reduzir threshold para categorias específicas com muitas variações',
            'impacto': f'+{casos_baixa_sim} matches potenciais',
            'implementacao': 'Ajustar thresholds_dinamicos.json'
        })
    
    # Recomendação 5: Variações de marca
    if len(analises['variacoes_marca']) > 30:
        recomendacoes.append({
            'prioridade': 'BAIXA',
            'casos': len(analises['variacoes_marca']),
            'titulo': 'Flexibilizar validação de marca',
            'descricao': 'Permitir até 3 marcas similares (ex: Bio, Bio Art, BioArt)',
            'impacto': f'+{len(analises["variacoes_marca"])} matches potenciais',
            'implementacao': 'Atualizar _coerencia_marca()'
        })
    
    # Ordenar por prioridade e casos
    prioridade_ordem = {'ALTA': 0, 'MÉDIA': 1, 'BAIXA': 2}
    recomendacoes.sort(key=lambda x: (prioridade_ordem[x['prioridade']], -x['casos']))
    
    # Exibir recomendações
    for i, rec in enumerate(recomendacoes, 1):
        print(f"\n{i}. [{rec['prioridade']}] {rec['titulo']}")
        print(f"   📊 Casos identificados: {rec['casos']}")
        print(f"   📝 Descrição: {rec['descricao']}")
        print(f"   📈 Impacto estimado: {rec['impacto']}")
        print(f"   🔧 Implementação: {rec['implementacao']}")
    
    # Calcular impacto total
    impacto_total = sum(r['casos'] for r in recomendacoes[:3])  # Top 3
    
    print(f"\n" + "=" * 100)
    print(f"🎯 IMPACTO ESTIMADO (Top 3 recomendações):")
    print(f"   Matches adicionais potenciais: +{impacto_total}")
    print(f"   Aumento na cobertura: +{impacto_total / 45241 * 100:.2f}%")
    
    return recomendacoes


def main():
    """Execução principal"""
    print("\n🚀 Análise de Matches Manuais - Melhorias no Algoritmo")
    
    try:
        analisar_matches_manuais()
        
        print("\n✅ Análise concluída!")
        print("\n💡 Use as recomendações acima para melhorar o algoritmo de matching.")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
