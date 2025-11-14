import sys, os, time, requests, json
from datetime import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))
from utils.marca_utils_final import extrair_marca_universal

# Configurar sessão reutilizável com timeout e retry otimizados
session = requests.Session()
retry_strategy = Retry(
    total=2, 
    backoff_factor=0.2,  
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
session.mount("http://", adapter)
session.mount("https://", adapter)

# URLs e configurações
GRAPHQL_URL = "https://www.suryadental.com.br/graphql"
SITE_BASE = "https://www.suryadental.com.br"
SITE_NOME = "surya"

print("Acessando os produtos...")

def fazer_requisicao_graphql(query, variables=None):
    """Faz requisição GraphQL otimizada"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://www.suryadental.com.br',
        'Referer': 'https://www.suryadental.com.br/'
    }
    
    payload = {
        'query': query,
        'variables': variables or {}
    }
    
    try:
        response = session.post(GRAPHQL_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if 'errors' in data:
            print(f"[ERRO] Erros GraphQL: {data['errors']}")
            return None
            
        return data
    except Exception as e:
        print(f"[ERRO] Erro na requisição: {e}")
        return None

def processar_produto_rapido(produto_data):
    """Processa dados de um produto rapidamente"""
    try:
        # Dados básicos
        sku = produto_data.get('sku', '')
        nome = produto_data.get('name', '')
        url_key = produto_data.get('url_key', '')
        url_completa = f"{SITE_BASE}/{url_key}.html" if url_key else ""
        
        # Preços
        price_range = produto_data.get('price_range', {})
        minimum_price = price_range.get('minimum_price', {})
        regular_price = minimum_price.get('regular_price', {})
        final_price = minimum_price.get('final_price', {})
        
        preco_atual = float(final_price.get('value', 0)) if final_price.get('value') else 0
        preco_antigo = float(regular_price.get('value', 0)) if regular_price.get('value') else preco_atual
        
        # Desconto
        porcentagem_desconto = 0
        if preco_antigo > 0 and preco_atual < preco_antigo:
            porcentagem_desconto = round(((preco_antigo - preco_atual) / preco_antigo) * 100, 2)
        
        # Status
        stock_status = produto_data.get('stock_status', 'OUT_OF_STOCK')
        disponivel = stock_status == 'IN_STOCK'
        status = "Disponível" if disponivel else "Indisponível"
        
        # Marca com fallback universal
        marca_api = (produto_data.get('manufacturer') or '').strip()
        
        if marca_api and marca_api != 'N/A' and marca_api != '':
            # [OK] Marca vinda da API GraphQL
            marca = marca_api
            nome_limpo = nome  # Nome já vem limpo da API
            print(f"   [OK] Marca da API: {marca}")
        else:
            # [PROCESSANDO] Fallback para função universal
            marca_extraida, nome_sem_marca = extrair_marca_universal(nome)
            
            if marca_extraida:
                # [OK] Marca extraída via função universal
                marca = marca_extraida
                nome_limpo = nome_sem_marca
                print(f"   [OK] Marca extraída (universal): {marca_extraida}")
            else:
                # [ERRO] Marca não identificada
                marca = "Marca não identificada"
                nome_limpo = nome
                print(f"   [ERRO] Marca não identificada: {nome[:50]}...")
        
        # Gerar chave de matching
        if marca and marca not in ['N/A', '', 'Marca não identificada']:
            chave_matching = f"{(nome_limpo or '').upper().strip()}_{(marca or '').upper().strip()}"
        else:
            chave_matching = (nome or '').upper().strip()
        
        # Categorias
        categorias_produto = []
        if 'categories' in produto_data:
            for cat in produto_data['categories']:
                if 'name' in cat:
                    categorias_produto.append(cat['name'])
        
        categoria_principal = categorias_produto[0] if categorias_produto else "Surya Dental"
        categorias_completas = " > ".join(categorias_produto) if categorias_produto else "Surya Dental"
        
        # Descrição
        descricao = ""
        if 'short_description' in produto_data and produto_data['short_description']:
            descricao = produto_data['short_description'].get('html', '')
        elif 'description' in produto_data and produto_data['description']:
            descricao = produto_data['description'].get('html', '')
        
        # Limpar HTML
        if descricao:
            import re
            descricao = re.sub(r'<[^>]+>', '', str(descricao)).strip()
            if len(descricao) > 500:
                descricao = descricao[:500] + "..."
        
        # Data
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Produto final
        return {
            'sku': sku,
            'nome': nome,
            'nome_limpo': nome_limpo,
            'marca': marca,
            'chave_matching': chave_matching,
            'preco': preco_atual,
            'preco_antigo': preco_antigo if preco_antigo != preco_atual else None,
            'porcentagem_desconto': porcentagem_desconto,
            'url': url_completa,
            'site': SITE_NOME,
            'disponivel': disponivel,
            'status': status,
            'categoria_principal': categoria_principal,
            'categorias_completas': categorias_completas,
            'descricao': descricao,
            'detalhes_produto': json.dumps({"stock_status": stock_status, "url_key": url_key}),
            'data_primeira_coleta': data_atual,
            'data_ultima_atualizacao': data_atual
        }
        
    except Exception as e:
        print(f"[ERRO] Erro ao processar produto: {e}")
        print(f"   Dados do produto: SKU={produto_data.get('sku', 'N/A')}, Nome={produto_data.get('name', 'N/A')[:30]}...")
        return None

def buscar_produtos_otimizado():
    
    todos_produtos = []
    pagina = 1
    
    # UID da categoria Surya Dental
    import base64
    categoria_uid = base64.b64encode(str(2).encode()).decode()
    
    inicio = time.time()
    
    while True:
        print(f"📄 Página {pagina}...", end=" ", flush=True)
        
        query = """
        query GetProducts($filters: ProductAttributeFilterInput!, $pageSize: Int!, $currentPage: Int!) {
            products(filter: $filters, pageSize: $pageSize, currentPage: $currentPage) {
                total_count
                items {
                    sku
                    name
                    url_key
                    price_range {
                        minimum_price {
                            regular_price { value }
                            final_price { value }
                        }
                    }
                    stock_status
                    manufacturer
                    categories { name }
                    short_description { html }
                    description { html }
                }
                page_info {
                    current_page
                    total_pages
                }
            }
        }
        """
        
        variables = {
            "filters": {
                "category_uid": {"eq": categoria_uid}
            },
            "pageSize": 125,  
            "currentPage": pagina
        }
        
        response = fazer_requisicao_graphql(query, variables)
        
        if not response:
            print("[ERRO] Erro")
            break
            
        data = response.get('data', {})
        products_data = data.get('products', {})
        items = products_data.get('items', [])
        page_info = products_data.get('page_info', {})
        total_count = products_data.get('total_count', 0)
        
        if not items:
            print("[OK] Fim")
            break
        
        # Processar página
        produtos_validos = 0
        for produto_raw in items:
            produto = processar_produto_rapido(produto_raw)
            if produto and produto['sku']:
                todos_produtos.append(produto)
                produtos_validos += 1
        
        # Estatísticas da página
        tempo_pagina = time.time() - inicio
        produtos_por_segundo = len(todos_produtos) / tempo_pagina if tempo_pagina > 0 else 0
        
        print(f"{produtos_validos} produtos | Total: {len(todos_produtos)} | {produtos_por_segundo:.1f} prod/s")
        
        # Verificar se acabou
        total_pages = page_info.get('total_pages', 1)
        if pagina >= total_pages:
            print(f"[OK] Concluído! {total_pages} páginas processadas")
            break
        
        pagina += 1
        time.sleep(0.3)
    
    return todos_produtos

def main():
    """Função principal super otimizada - COM salvamento no banco de dados"""
    inicio = time.time()
    
    # Inicializar estatísticas do banco
    stats_db_global = {
        "novos": 0,
        "atualizados": 0,
        "sem_alteracao": 0,
        "mudanca_disponibilidade": 0,
        "novos_descontos": 0,
        "perdeu_desconto": 0
    }
    
    # Buscar produtos
    produtos = buscar_produtos_otimizado()
    
    if not produtos:
        print("[ERRO] Nenhum produto coletado!")
        return []
    
    print(f"\n Salvando {len(produtos):,} produtos no banco de dados...")
    
    # Salvar produtos no banco de dados
    stats_db = salvar_produtos_db(produtos, "surya", "surya")
    
    # Atualizar estatísticas globais do banco
    for key in stats_db_global:
        stats_db_global[key] += stats_db[key]
    
    if not produtos:
        print("[ERRO] Nenhum produto coletado!")
        return []
    
    return produtos

if __name__ == "__main__":
    try:
        produtos_finais = main()
        
        print(f"\n" + "=" * 60)
        print(f"[OK] SCRAPING SURYA DENTAL CONCLUÍDO!")
        print(f"[STATS] {len(produtos_finais):,} produtos únicos salvos no banco")
        print(f"[INICIO] Execução otimizada com salvamento automático")
        print(f"=" * 60)
        
        # Mostrar estatísticas do banco de dados
        print(f"\n")
        consulta_db_estatisticas('surya')
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante execução: {e}")
        print(f"[DICA] Tente executar novamente")
