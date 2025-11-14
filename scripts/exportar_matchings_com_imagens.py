#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportar Matchings com Imagens para JSON
Gera arquivo JSON com todos os matches e suas imagens representativas
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def conectar_banco(db_path: str = "match_crew.db"):
    """Conecta ao banco de dados"""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")
    return sqlite3.connect(db_path)


def buscar_imagem_valida(cursor, id_bids: str) -> tuple:
    """
    Busca uma imagem válida para o produto
    id_bids é um JSON array com múltiplos IDs
    Retorna: (url_imagem, origem)
    """
    # Parse do JSON array
    try:
        ids_list = json.loads(id_bids)
        if not isinstance(ids_list, list) or len(ids_list) == 0:
            return None, None
    except:
        return None, None
    
    # Tenta buscar imagem de cada produto na lista
    for produto_id in ids_list:
        cursor.execute("""
            SELECT imagem_url, imagens_extras, nome, site, id
            FROM produtos
            WHERE id = ?
        """, (produto_id,))
        
        resultado = cursor.fetchone()
        if not resultado:
            continue
        
        imagem_url, imagens_extras, nome_produto, site, pid = resultado
        
        # Verifica imagem_url principal
        if imagem_url and imagem_url.strip():
            return imagem_url.strip(), f"{pid} - {site}"
        
        # Se não tem imagem principal, tenta imagens_extras
        if imagens_extras and imagens_extras.strip():
            # imagens_extras pode ser JSON array ou string separada
            try:
                # Tenta parsear como JSON
                extras = json.loads(imagens_extras)
                if isinstance(extras, list) and len(extras) > 0:
                    primeira_extra = extras[0]
                    if primeira_extra and primeira_extra.strip():
                        return primeira_extra.strip(), f"{pid} - {site} (extra)"
            except:
                # Se não é JSON, tenta como string separada por vírgula
                extras = imagens_extras.split(',')
                if len(extras) > 0:
                    primeira_extra = extras[0].strip()
                    if primeira_extra:
                        return primeira_extra, f"{pid} - {site} (extra)"
    
    # Nenhum produto tinha imagem
    return None, None


def exportar_matchings_com_imagens():
    """Exporta matchings com imagens para JSON"""
    
    print("="*100)
    print("EXPORTAÇÃO DE MATCHINGS COM IMAGENS")
    print("="*100)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Conecta ao banco
    print("📊 Conectando ao banco de dados...")
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Busca todos os matches
    print("🔍 Buscando matchings...")
    cursor.execute("""
        SELECT 
            id_match,
            id_bids,
            nome_produto,
            categoria,
            subcategoria,
            marca,
            url_cremer,
            url_speed,
            url_medsul,
            url_proclin,
            url_dentalshop,
            url_apoiodental,
            url_interdental,
            url_surya,
            total_sites,
            score_match
        FROM produtos_mestre
        ORDER BY id_match
    """)
    
    produtos = cursor.fetchall()
    print(f"✅ {len(produtos)} grupos de matches encontrados")
    
    # Processa cada match
    print("\n📦 Processando matchings...")
    matches_dict = {}
    
    for row in produtos:
        (id_match, id_bids, nome, categoria, subcategoria, marca,
         url_cremer, url_speed, url_medsul, url_proclin, url_dentalshop,
         url_apoiodental, url_interdental, url_surya, total_sites, score) = row
        
        # Identifica quais sites têm este produto
        sites_presentes = []
        urls_por_site = {
            'Cremer': url_cremer,
            'Speed': url_speed,
            'Medsul': url_medsul,
            'Proclin': url_proclin,
            'Dentalshop': url_dentalshop,
            'Apoio Dental': url_apoiodental,
            'Interdental': url_interdental,
            'Surya': url_surya
        }
        
        for site, url in urls_por_site.items():
            if url and url.strip():
                sites_presentes.append(site)
        
        matches_dict[id_match] = {
            'id_bids': id_bids,
            'nome': nome,
            'categoria': categoria,
            'subcategoria': subcategoria,
            'marca': marca,
            'sites': sites_presentes,
            'total_sites': total_sites,
            'score': score
        }
    
    print(f"✅ {len(matches_dict)} grupos de matching encontrados")
    
    # Busca imagens para cada match
    print("\n🖼️  Buscando imagens para cada match...")
    matches_list = []
    com_imagem = 0
    sem_imagem = 0
    
    for idx, (id_match, info_match) in enumerate(matches_dict.items(), 1):
        if idx % 500 == 0:
            print(f"   Processados {idx}/{len(matches_dict)} matches...")
        
        # Busca uma imagem válida
        imagem_url, imagem_origem = buscar_imagem_valida(cursor, info_match['id_bids'])
        
        if imagem_url:
            com_imagem += 1
        else:
            sem_imagem += 1
        
        # Monta objeto do match
        match_obj = {
            'id_match': id_match,
            'id_bids': info_match['id_bids'],
            'total_sites': info_match['total_sites'],
            'nome_representativo': info_match['nome'],
            'categoria': info_match['categoria'],
            'subcategoria': info_match['subcategoria'],
            'marca': info_match['marca'],
            'score_match': info_match['score'],
            'sites': info_match['sites'],
            'imagem_url': imagem_url,
            'imagem_origem': imagem_origem
        }
        
        matches_list.append(match_obj)
    
    print(f"✅ Processamento concluído!")
    print(f"   Com imagem: {com_imagem}")
    print(f"   Sem imagem: {sem_imagem}")
    
    # Monta objeto final
    percentual_com_imagem = (com_imagem / len(matches_list) * 100) if len(matches_list) > 0 else 0
    
    # Calcula total de produtos
    total_produtos_matches = sum(m['total_sites'] for m in matches_list)
    
    output = {
        'metadata': {
            'data_exportacao': datetime.now().isoformat(),
            'versao': '1.0',
            'descricao': 'Matchings de produtos com imagens representativas'
        },
        'estatisticas': {
            'total_matches': len(matches_list),
            'total_produtos': total_produtos_matches,
            'media_sites_por_match': round(total_produtos_matches / len(matches_list), 2) if len(matches_list) > 0 else 0,
            'com_imagem': com_imagem,
            'sem_imagem': sem_imagem,
            'percentual_com_imagem': round(percentual_com_imagem, 2)
        },
        'matches': matches_list
    }
    
    # Salva JSON
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = exports_dir / f"matchings_com_imagens_{timestamp}.json"
    
    print(f"\n💾 Salvando arquivo JSON...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # Estatísticas finais
    print("\n" + "="*100)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*100)
    print(f"Total de matches: {len(matches_list):,}")
    
    # Calcula total de produtos nos matches (soma de total_sites)
    total_produtos_matches = sum(m['total_sites'] for m in matches_list)
    print(f"Total de produtos nos matches: {total_produtos_matches:,}")
    print(f"Média sites/match: {total_produtos_matches/len(matches_list):.2f}")
    print()
    print(f"Matches COM imagem: {com_imagem:,} ({percentual_com_imagem:.1f}%)")
    print(f"Matches SEM imagem: {sem_imagem:,} ({100-percentual_com_imagem:.1f}%)")
    print()
    
    # Top categorias com mais matches
    print("🏆 TOP 10 CATEGORIAS COM MAIS MATCHES:")
    print("-"*100)
    categorias = defaultdict(int)
    for match in matches_list:
        cat = match['categoria']
        if cat:
            categorias[cat] += 1
    
    top_categorias = sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (cat, count) in enumerate(top_categorias, 1):
        print(f"  {i:2d}. {cat:50s} {count:,} matches")
    
    print()
    print("="*100)
    print("✅ EXPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*100)
    print()
    print(f"📄 Arquivo gerado: {output_path.name}")
    print(f"📁 Localização: {output_path.absolute()}")
    
    tamanho_kb = output_path.stat().st_size / 1024
    print(f"📦 Tamanho: {tamanho_kb:.2f} KB")
    
    print()
    print("💡 Próximos passos:")
    print("   1. Verificar arquivo JSON gerado")
    print("   2. Usar JSON para processar imagens")
    print("   3. Integrar com sistema de visualização")
    
    conn.close()
    return output_path


if __name__ == "__main__":
    try:
        output_path = exportar_matchings_com_imagens()
        print("\n✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro durante exportação: {e}")
        import traceback
        traceback.print_exc()
