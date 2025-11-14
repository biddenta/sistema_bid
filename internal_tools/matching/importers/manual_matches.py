"""
Importação de Matches Manuais do Cadastro Bid Dental
Analisa o arquivo Excel e integra matches que não estão no banco
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import sqlite3
import json
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict


def normalizar_url(url):
    """Normaliza URL para comparação"""
    if pd.isna(url) or not url:
        return None
    url = str(url).strip()
    if not url.startswith('http'):
        return None
    # Remove trailing slashes e query params para comparação
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')


def analisar_excel():
    """Analisa estrutura do arquivo Excel"""
    print("\n" + "=" * 100)
    print("📊 ANÁLISE DO CADASTRO BID DENTAL - MATCHES MANUAIS")
    print("=" * 100)
    
    # Ler Excel (começando da linha 3 - índice 2)
    print("\n📂 Lendo arquivo Excel...")
    df = pd.read_excel('Cadastro Bid Dental_rev12.xlsx', header=2)
    
    print(f"✅ Arquivo lido: {len(df)} linhas")
    print(f"\n📋 Colunas encontradas ({len(df.columns)} colunas):")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i:2d}. {col}")
    
    # Mapear sites e suas colunas
    sites_map = {
        'Cremer': {'codigo_col': 'Código Cremer', 'link_col': 'Links Cremer', 'site_bd': 'Dental Cremer'},
        'Speed': {'codigo_col': 'Código Speed', 'link_col': 'Link Speed', 'site_bd': 'Dental Speed'},
        'Surya': {'codigo_col': 'Código Surya', 'link_col': 'Link Surya', 'site_bd': 'Surya'},
        'Apoio': {'codigo_col': 'Código Apoio', 'link_col': 'Link Apoio', 'site_bd': 'Apoio Dental'},
        'Med Sul': {'codigo_col': 'Código Med Sul', 'link_col': 'Link Med Sul', 'site_bd': 'Dental Medsul'},
        'Interdental': {'codigo_col': 'Código Interdental', 'link_col': 'Link Interdental', 'site_bd': 'Loja Interdental'},
        'Dental Shop': {'codigo_col': 'Código Dental Shop', 'link_col': 'Link Dental Shop', 'site_bd': 'Dental Shop'},
        'Proclin': {'codigo_col': 'Código Proclin', 'link_col': 'Link Dental Proclin', 'site_bd': 'Dental Proclin'},
    }
    
    print(f"\n🌐 Sites mapeados: {len(sites_map)}")
    for site in sites_map.keys():
        print(f"   • {site}")
    
    return df, sites_map


def carregar_produtos_cache(cursor):
    """Carrega todos os produtos em memória para busca rápida"""
    print("📦 Carregando produtos do banco em memória...")
    
    cursor.execute("""
        SELECT id, nome, marca, categoria, url, site
        FROM produtos
        WHERE url IS NOT NULL AND url != ''
    """)
    
    produtos = cursor.fetchall()
    
    # Criar índice por URL normalizada
    cache_url = {}
    for produto in produtos:
        url_norm = normalizar_url(produto[4])
        if url_norm:
            # Usar apenas a parte final da URL como chave
            url_final = url_norm.split('/')[-1] if '/' in url_norm else url_norm
            cache_url[url_final] = {
                'id': produto[0],
                'nome': produto[1],
                'marca': produto[2],
                'categoria': produto[3],
                'url': produto[4],
                'site': produto[5]
            }
    
    print(f"✅ {len(cache_url):,} produtos carregados no cache")
    return cache_url


def buscar_produto_por_url(cache_url, url_normalizada, site):
    """Busca produto no cache por URL"""
    if not url_normalizada:
        return None
    
    # Buscar pela parte final da URL
    url_final = url_normalizada.split('/')[-1] if '/' in url_normalizada else url_normalizada
    
    produto = cache_url.get(url_final)
    if produto and site.lower() in produto['site'].lower():
        return produto
    
    return None


def verificar_match_existente(cursor, produtos_ids):
    """Verifica se já existe um match com esses produtos"""
    if not produtos_ids:
        return None
    
    # Buscar em produtos_mestre
    for produto_id in produtos_ids:
        cursor.execute("""
            SELECT id_match, id_bids, nome_produto, total_produtos
            FROM produtos_mestre
            WHERE id_bids LIKE ?
        """, (f'%"{produto_id}"%',))
        
        resultado = cursor.fetchone()
        if resultado:
            return {
                'id_match': resultado[0],
                'id_bids': json.loads(resultado[1]),
                'nome': resultado[2],
                'total_produtos': resultado[3]
            }
    
    return None


def processar_matches_manuais(df, sites_map):
    """Processa matches manuais do Excel"""
    
    conn = sqlite3.connect('match_crew.db')
    cursor = conn.cursor()
    
    print("\n" + "=" * 100)
    print("🔍 PROCESSANDO MATCHES MANUAIS")
    print("=" * 100)
    
    # Carregar produtos em memória (otimização)
    cache_produtos = carregar_produtos_cache(cursor)
    
    estatisticas = {
        'linhas_processadas': 0,
        'grupos_analisados': 0,
        'produtos_encontrados': 0,
        'produtos_nao_encontrados': 0,
        'matches_existentes': 0,
        'matches_novos': 0,
        'matches_adicionados': 0,
        'matches_atualizados': 0,
    }
    
    grupos_novos = []
    grupos_para_atualizar = []
    
    print(f"\n🔄 Processando {len(df)} linhas...")
    
    # Processar cada linha do Excel
    for idx, row in df.iterrows():
        estatisticas['linhas_processadas'] += 1
        
        # Ignorar linhas vazias
        codigo_bid = row.get('Código Bid Dental')
        if pd.isna(codigo_bid):
            continue
        
        nome_produto = row.get('Nome Comercial do Produto', '')
        marca = row.get('Marca', '')
        categoria = row.get('Categoria de Produto', '')
        
        # Coletar produtos de cada site
        produtos_grupo = []
        links_por_site = {}
        
        for site_nome, site_info in sites_map.items():
            link = row.get(site_info['link_col'])
            url_normalizada = normalizar_url(link)
            
            if url_normalizada:
                # Buscar produto no cache
                produto = buscar_produto_por_url(cache_produtos, url_normalizada, site_info['site_bd'])
                
                if produto:
                    produtos_grupo.append(produto)
                    links_por_site[site_nome.lower().replace(' ', '_')] = produto['url']
                    estatisticas['produtos_encontrados'] += 1
                else:
                    estatisticas['produtos_nao_encontrados'] += 1
        
        # Se encontrou 2+ produtos, é um grupo válido
        if len(produtos_grupo) >= 2:
            estatisticas['grupos_analisados'] += 1
            
            # Verificar se já existe
            produtos_ids = [p['id'] for p in produtos_grupo]
            match_existente = verificar_match_existente(cursor, produtos_ids)
            
            if match_existente:
                estatisticas['matches_existentes'] += 1
                
                # Verificar se há produtos novos para adicionar
                ids_existentes = set(match_existente['id_bids'])
                ids_novos = set(str(pid) for pid in produtos_ids) - set(str(eid) for eid in ids_existentes)
                
                if ids_novos:
                    grupos_para_atualizar.append({
                        'id_match': match_existente['id_match'],
                        'produtos_atuais': match_existente['id_bids'],
                        'produtos_novos': list(ids_novos),
                        'produtos_grupo': produtos_grupo,
                        'links': links_por_site
                    })
            else:
                # Novo grupo
                estatisticas['matches_novos'] += 1
                grupos_novos.append({
                    'nome': nome_produto if nome_produto else produtos_grupo[0]['nome'],
                    'marca': marca if marca else produtos_grupo[0]['marca'],
                    'categoria': categoria if categoria else produtos_grupo[0]['categoria'],
                    'produtos': produtos_grupo,
                    'links': links_por_site,
                    'codigo_bid': codigo_bid
                })
        
        # Progresso
        if (idx + 1) % 500 == 0:
            print(f"   Processadas {idx + 1:,} linhas...")
    
    print(f"\n✅ Processamento concluído!")
    
    # Exibir estatísticas
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   Linhas processadas: {estatisticas['linhas_processadas']}")
    print(f"   Grupos analisados: {estatisticas['grupos_analisados']}")
    print(f"   Produtos encontrados no banco: {estatisticas['produtos_encontrados']}")
    print(f"   Produtos NÃO encontrados: {estatisticas['produtos_nao_encontrados']}")
    print(f"   Matches já existentes: {estatisticas['matches_existentes']}")
    print(f"   Matches NOVOS identificados: {estatisticas['matches_novos']}")
    
    # Adicionar novos matches
    if grupos_novos:
        print(f"\n💾 ADICIONANDO {len(grupos_novos)} NOVOS MATCHES...")
        
        for grupo in grupos_novos:
            adicionar_match(cursor, grupo)
            estatisticas['matches_adicionados'] += 1
        
        conn.commit()
        print(f"✅ {estatisticas['matches_adicionados']} matches adicionados!")
    
    # Atualizar matches existentes
    if grupos_para_atualizar:
        print(f"\n🔄 ATUALIZANDO {len(grupos_para_atualizar)} MATCHES EXISTENTES...")
        
        for grupo in grupos_para_atualizar:
            atualizar_match(cursor, grupo)
            estatisticas['matches_atualizados'] += 1
        
        conn.commit()
        print(f"✅ {estatisticas['matches_atualizados']} matches atualizados!")
    
    # Resumo final
    print(f"\n" + "=" * 100)
    print(f"📊 RESUMO FINAL")
    print(f"=" * 100)
    print(f"✅ Matches adicionados: {estatisticas['matches_adicionados']}")
    print(f"🔄 Matches atualizados: {estatisticas['matches_atualizados']}")
    print(f"⚖️  Matches já existentes (sem mudança): {estatisticas['matches_existentes'] - estatisticas['matches_atualizados']}")
    
    # Exibir alguns exemplos
    if grupos_novos:
        print(f"\n📋 EXEMPLOS DE NOVOS MATCHES:")
        for i, grupo in enumerate(grupos_novos[:5], 1):
            print(f"\n   {i}. {grupo['nome']}")
            print(f"      Marca: {grupo['marca']}")
            print(f"      Categoria: {grupo['categoria']}")
            print(f"      Sites: {len(grupo['produtos'])}")
            print(f"      Produtos: {[p['id'] for p in grupo['produtos']]}")
    
    conn.close()
    
    return estatisticas


def adicionar_match(cursor, grupo):
    """Adiciona novo match ao banco"""
    
    # Gerar ID do match
    cursor.execute("SELECT MAX(CAST(SUBSTR(id_match, 7) AS INTEGER)) FROM produtos_mestre WHERE id_match LIKE 'MATCH_%'")
    ultimo_id = cursor.fetchone()[0] or 0
    id_match = f"MATCH_{ultimo_id + 1:06d}"
    
    # Preparar dados
    id_bids = json.dumps([str(p['id']) for p in grupo['produtos']])
    sites = list(set(p['site'] for p in grupo['produtos']))
    
    # Mapear URLs por site
    site_mapping = {
        'dental_cremer': 'url_cremer',
        'dental_speed': 'url_speed',
        'dental_medsul': 'url_medsul',
        'dental_proclin': 'url_proclin',
        'dental_shop': 'url_dentalshop',
        'apoio_dental': 'url_apoiodental',
        'loja_interdental': 'url_interdental',
        'surya': 'url_surya'
    }
    
    urls_colunas = {}
    for produto in grupo['produtos']:
        site_key = produto['site'].lower().replace(' ', '_')
        coluna = site_mapping.get(site_key)
        if coluna:
            urls_colunas[coluna] = produto.get('url', '')
    
    timestamp = datetime.now().isoformat()
    
    # Inserir em produtos_mestre
    cursor.execute("""
        INSERT INTO produtos_mestre (
            id_match, id_bids, nome_produto, categoria, subcategoria,
            marca, embalagem,
            url_cremer, url_speed, url_medsul, url_proclin,
            url_dentalshop, url_apoiodental, url_interdental, url_surya,
            total_sites, total_produtos, score_match,
            metodo_matching, estrategia_base,
            data_criacao, data_atualizacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_match,
        id_bids,
        grupo['nome'],
        grupo['categoria'],
        None,  # subcategoria
        grupo['marca'],
        None,  # embalagem
        urls_colunas.get('url_cremer'),
        urls_colunas.get('url_speed'),
        urls_colunas.get('url_medsul'),
        urls_colunas.get('url_proclin'),
        urls_colunas.get('url_dentalshop'),
        urls_colunas.get('url_apoiodental'),
        urls_colunas.get('url_interdental'),
        urls_colunas.get('url_surya'),
        len(sites),
        len(grupo['produtos']),
        1.0,  # Score máximo (match manual)
        'importacao_manual',
        'cadastro_bid_dental',
        timestamp,
        timestamp
    ))
    
    # Atualizar produtos
    for produto in grupo['produtos']:
        cursor.execute("""
            UPDATE produtos 
            SET id_match = ?,
                tem_matching = 1,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (id_match, produto['id']))


def atualizar_match(cursor, grupo):
    """Atualiza match existente com novos produtos"""
    
    # Combinar IDs
    todos_ids = list(set(grupo['produtos_atuais'] + [int(pid) for pid in grupo['produtos_novos']]))
    id_bids_novo = json.dumps([str(pid) for pid in todos_ids])
    
    # Atualizar registro
    cursor.execute("""
        UPDATE produtos_mestre
        SET id_bids = ?,
            total_produtos = ?,
            data_atualizacao = ?
        WHERE id_match = ?
    """, (
        id_bids_novo,
        len(todos_ids),
        datetime.now().isoformat(),
        grupo['id_match']
    ))
    
    # Atualizar novos produtos
    for produto_id in grupo['produtos_novos']:
        cursor.execute("""
            UPDATE produtos 
            SET id_match = ?,
                tem_matching = 1,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (grupo['id_match'], int(produto_id)))


def main():
    """Execução principal"""
    print("\n🚀 Importação de Matches Manuais - Cadastro Bid Dental")
    
    try:
        # Analisar Excel
        df, sites_map = analisar_excel()
        
        # Processar matches direto
        print("\n▶️  Iniciando processamento...")
        estatisticas = processar_matches_manuais(df, sites_map)
        
        print("\n✅ Importação concluída com sucesso!")
        
    except FileNotFoundError:
        print("\n❌ ERRO: Arquivo 'Cadastro Bid Dental_rev12.xlsx' não encontrado!")
        print("   Certifique-se de que o arquivo está na pasta raiz do projeto.")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
