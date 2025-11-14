import sys, os, time, requests
from playwright.sync_api import sync_playwright
from requests.adapters import HTTPAdapter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Importar função universal de extração de marca
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))
from utils.marca_utils_final import extrair_marca_universal

# Configurar sessão reutilizável com timeout e retry otimizados
session = requests.Session()
retry_strategy = Retry(
    total=2, 
    backoff_factor=0.1,  
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
session.mount("http://", adapter)
session.mount("https://", adapter)


# 1. Extrair marcas do site

print("Acessando o site...")

url = "https://www.dentalspeed.com/marcas"

with sync_playwright() as p:
    page = p.chromium.launch(headless=True).new_page()
    page.goto(url, timeout=30000)
    page.wait_for_load_state('networkidle')
    soup = BeautifulSoup(page.content(), "html.parser")

marcas = [
    (a.text.strip(), a["href"]) 
    for li in soup.find_all("li", class_="filtered") 
    if (a := li.find("a")) and a.text and a.get("href")
]

# 2. Detectar alterações e salvar marcas

# CORREÇÃO: Criar arquivo na pasta do script, não na raiz
script_dir = os.path.dirname(os.path.abspath(__file__))
arquivo_marcas = os.path.join(script_dir, "marcas_extraidas_dental_speed.txt")
marcas_atuais = {f"{nome} -> {link}" for nome, link in marcas}

# Carregar marcas anteriores
marcas_anteriores = set()
if os.path.exists(arquivo_marcas):
    with open(arquivo_marcas, "r", encoding="utf-8") as f:
        marcas_anteriores = {linha.strip() for linha in f if linha.strip()}

# Salvar marcas atuais
with open(arquivo_marcas, "w", encoding="utf-8") as f:
    for linha in sorted(marcas_atuais):
        f.write(linha + "\n")

# Mostrar diferenças
adicionadas = marcas_atuais - marcas_anteriores
removidas = marcas_anteriores - marcas_atuais

for linha in sorted(adicionadas):
    print("[ADICIONADA]", linha)
for linha in sorted(removidas):
    print("[REMOVIDA]", linha)
if not (adicionadas or removidas):
    print("\nNenhuma alteração nas marcas.")

# 3. Função para extrair categorias de forma melhorada ===

def extrair_categorias_melhorada(produto):
    """Extrai categorias de forma mais detalhada usando a estrutura hierárquica da API"""
    categories = produto.get('categories', [])
    
    if not categories:
        return {
            'categoria_principal': 'N/A',
            'subcategoria': 'N/A', 
            'categoria_completa': 'N/A',
            'todas_categorias': []
        }
    
    # Separar por hierarquia
    categoria_principal = None
    subcategorias = []
    
    for cat in categories:
        if not cat.get('parents'):  # Sem pais = categoria principal
            categoria_principal = cat.get('name')
        else:  # Com pais = subcategoria
            subcategorias.append(cat.get('name'))
    
    # Definir categoria principal e subcategoria de forma clara
    categoria_principal_final = categoria_principal if categoria_principal else 'N/A'
    subcategoria_final = subcategorias[0] if subcategorias else 'N/A'
    
    # Montar categoria completa apenas quando necessário
    if categoria_principal and subcategorias:
        categoria_completa = f"{categoria_principal} > {subcategorias[0]}"
    elif subcategorias:
        categoria_completa = subcategorias[0]
    elif categoria_principal:
        categoria_completa = categoria_principal
    else:
        categoria_completa = 'N/A'
    
    return {
        'categoria_principal': categoria_principal_final,
        'subcategoria': subcategoria_final,
        'categoria_completa': categoria_completa,
        'todas_categorias': [cat.get('name') for cat in categories]
    }

def extrair_imagens_produto(produto):
    """Extrai as imagens do produto da estrutura da API"""
    images = produto.get('images', {})
    
    if not images or not isinstance(images, dict):
        return {
            'imagem_principal': None,
            'imagens_extras': None
        }
    
    # Imagem principal (default)
    imagem_principal = images.get('default', None)
    
    # Imagens extras (todas exceto a default)
    imagens_extras = []
    for key, value in images.items():
        if key != 'default' and value:
            imagens_extras.append(value)
    
    # Converter lista de imagens extras para string JSON para armazenar no banco
    imagens_extras_json = None
    if imagens_extras:
        import json
        imagens_extras_json = json.dumps(imagens_extras)
    
    return {
        'imagem_principal': imagem_principal,
        'imagens_extras': imagens_extras_json
    }

# 4 Consulta na API por produtos da marca ===

def buscar_produtos_api(marca_nome):
    """Busca produtos de uma marca de forma otimizada"""
    
    
    headers = {
        "accept": "*/*",
        "accept-language": "pt-BR,pt;q=0.9",
        "origin": "https://www.dentalspeed.com",
        "referer": "https://www.dentalspeed.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
   
    formatos = [
        marca_nome.lower(),                       
        marca_nome.upper(),                          
        marca_nome.title(),                         
        marca_nome.lower().replace(' ', ''),        
        marca_nome.lower().replace(' ', '_'),        
        marca_nome[0].lower() if marca_nome else ""  
    ]
    
    # Endpoints para testar
    endpoints = [
        ("https://api.linximpulse.com/engage/search/v3/navigates", "fields", "brand:{}"),
        ("https://api.linximpulse.com/engage/search/v3/hotsites", "name", "{}")
    ]
    
    def buscar_produtos(url, param_key, param_format, nome_formatado):
        """Busca produtos em um endpoint específico com paginação"""
        todos_produtos = []
        pagina = 1
        max_paginas = 10  
        
        while pagina <= max_paginas:
            params = {
                "apikey": "dentalspeed-api",
                param_key: param_format.format(nome_formatado),
                "source": "desktop",
                "deviceid": "undefined",
                "resultsperpage": 96,  
                "sortby": "relevance"   
            }
            
            
            if pagina > 1:
                params["page"] = pagina
            
            
            params["_"] = int(time.time() * 1000)
            
            try:
                response = session.get(url, headers=headers, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    produtos_pagina = data.get('products', [])
                    
                    if produtos_pagina:
                        todos_produtos.extend(produtos_pagina)
                        
                        # Se menos produtos que o esperado, é a última página
                        if len(produtos_pagina) < params.get('resultsperpage', 96):
                            break
                            
                        pagina += 1
                    else:
                        break
                else:
                    break
            except:
                break
        
        return todos_produtos
    
    # Tenta cada combinação de endpoint + formato
    for url, param_key, param_format in endpoints:
        for nome_formatado in formatos:
            produtos = buscar_produtos(url, param_key, param_format, nome_formatado)
            if produtos:
                produtos_processados = []
                
                for p in produtos:
                    # Extrair categorias usando a nova função
                    categorias_info = extrair_categorias_melhorada(p)
                    
                    # Extrair imagens usando a nova função
                    imagens_info = extrair_imagens_produto(p)
                    
                    # Processar preços e calcular desconto
                    preco_atual = p.get("price", 0)
                    preco_antigo = p.get("oldPrice", preco_atual)
                    
                    # Calcular porcentagem de desconto
                    porcentagem_desconto = 0
                    if preco_antigo > preco_atual and preco_antigo > 0:
                        porcentagem_desconto = ((preco_antigo - preco_atual) / preco_antigo) * 100
                    
                    # Processar marca com sistema híbrido (API + fallback universal)
                    marca_api = p.get("brand")
                    if not marca_api and p.get("details", {}).get("brand"):
                        brand_details = p.get("details", {}).get("brand", [])
                        if isinstance(brand_details, list) and brand_details:
                            marca_api = brand_details[0]
                        elif isinstance(brand_details, str):
                            marca_api = brand_details
                    
                    # Sistema híbrido de marca
                    if marca_api and marca_api.strip() and marca_api not in ['N/A', '']:
                        # [OK] Marca vinda da API
                        marca_produto = marca_api
                        nome_limpo = p.get("name", "")  # Nome já vem limpo da API
                        print(f"   [OK] Marca da API: {marca_produto}")
                    else:
                        # [FALLBACK] Funcao universal
                        nome_produto = p.get("name", "")
                        marca_extraida, nome_sem_marca = extrair_marca_universal(nome_produto)
                        
                        if marca_extraida:
                            # [OK] Marca extraida via funcao universal
                            marca_produto = marca_extraida
                            nome_limpo = nome_sem_marca
                            print(f"   [OK] Marca extraida (universal): {marca_extraida}")
                        else:
                            # [ERRO] Marca nao identificada
                            marca_produto = "Marca não identificada"
                            nome_limpo = nome_produto
                            print(f"   [ERRO] Marca nao identificada: {nome_produto[:50]}...")
                    
                    # Gerar chave de matching
                    if marca_produto and marca_produto not in ['N/A', '', 'Marca não identificada']:
                        chave_matching = f"{nome_limpo.upper().strip()}_{marca_produto.upper().strip()}"
                    else:
                        chave_matching = p.get("name", "").upper().strip()
                    
                    # Processar detalhes (converter dict para string legível)
                    detalhes = p.get("details", {})
                    detalhes_formatados = []
                    for chave, valor in detalhes.items():
                        if isinstance(valor, list):
                            valor_str = ", ".join(map(str, valor))
                        else:
                            valor_str = str(valor)
                        detalhes_formatados.append(f"{chave}: {valor_str}")
                    detalhes_texto = " | ".join(detalhes_formatados) if detalhes_formatados else "N/A"
                    
                    produto_processado = {
                        "nome": p.get("name", "Sem nome"),
                        "nome_limpo": nome_limpo,  # Nome limpo pela função universal
                        "marca": marca_produto,  # Campo marca padronizado
                        "chave_matching": chave_matching,  # Nova chave de matching
                        "preco": preco_atual,
                        "preco_antigo": preco_antigo,
                        "porcentagem_desconto": porcentagem_desconto,
                        "sku": p.get("id", "Sem SKU"),
                        "url": f"https://www.dentalspeed.com{p.get('url', '')}" if p.get('url') else "Sem link",
                        "disponivel": p.get("status", "").upper() == "AVAILABLE",
                        "status": p.get("status", "N/A"),
                        "categoria_principal": categorias_info['categoria_principal'],
                        "subcategoria": categorias_info['subcategoria'],
                        "categorias_completas": categorias_info['categoria_completa'],
                        "imagem_principal": imagens_info['imagem_principal'],
                        "imagens_extras": imagens_info['imagens_extras'],
                        "descricao": p.get("description", "N/A") or "N/A",
                        "detalhes_produto": detalhes_texto,
                        "site": "Dental Speed"
                    }
                    produtos_processados.append(produto_processado)
                
                return produtos_processados
    
    return []

# 3. Buscar produtos por marca

print("\nColetando produtos por marca...\n")

stats = {"total_produtos": 0, "com_produtos": 0, "sem_produtos": 0}
stats_db_global = {"novos": 0, "atualizados": 0, "sem_alteracao": 0, "mudanca_disponibilidade": 0, "novos_descontos": 0, "perdeu_desconto": 0}
inicio = time.time()

for i, (nome_marca, _) in enumerate(marcas, 1):
    print(f"[{i}/{len(marcas)}] {nome_marca}...", end=" ", flush=True)
    
    produtos = buscar_produtos_api(nome_marca)
    
    if produtos:
        stats["total_produtos"] += len(produtos)
        stats["com_produtos"] += 1
        print(f"[OK] {len(produtos)} produtos")
        
        # Salvar produtos no banco de dados
        stats_db = salvar_produtos_db(produtos, nome_marca, "Dental Speed")
        
        # Atualizar estatísticas globais do banco
        for key in stats_db_global:
            stats_db_global[key] += stats_db[key]
        
            
        # Mostrar estatísticas do banco para esta marca
        if (stats_db["novos"] > 0 or stats_db["atualizados"] > 0 or 
            stats_db["mudanca_disponibilidade"] > 0 or stats_db["novos_descontos"] > 0 or 
            stats_db["perdeu_desconto"] > 0):
            info_db = []
            if stats_db["novos"] > 0:
                info_db.append(f"{stats_db['novos']} novos")
            if stats_db["atualizados"] > 0:
                info_db.append(f"{stats_db['atualizados']} atualizados")
            if stats_db["mudanca_disponibilidade"] > 0:
                info_db.append(f"{stats_db['mudanca_disponibilidade']} mudaram disponibilidade")
            if stats_db["novos_descontos"] > 0:
                info_db.append(f"{stats_db['novos_descontos']} novos descontos")
            if stats_db["perdeu_desconto"] > 0:
                info_db.append(f"{stats_db['perdeu_desconto']} perderam desconto")
            print(f"    DB: {', '.join(info_db)}")
    else:
        stats["sem_produtos"] += 1
        print(f"[ERRO] Sem produtos")

# Resumo final
tempo_total = time.time() - inicio
print("\nRESUMO DO SCRAPING:")
print("=================================================")
print(f"Marcas processadas: {len(marcas):>12}")
print(f"Produtos encontrados: {stats['total_produtos']:>12}")
print(f"Marcas com produtos: {stats['com_produtos']:>12}")
print(f"Marcas sem produtos: {stats['sem_produtos']:>12}")
print("-------------------------------------------------")
print(f"Produtos NOVOS no banco: {stats_db_global['novos']:>12}")
print(f"Produtos ATUALIZADOS no banco: {stats_db_global['atualizados']:>12}")
print(f"Mudancas de DISPONIBILIDADE: {stats_db_global['mudanca_disponibilidade']:>12}")
print(f"Produtos com NOVOS DESCONTOS: {stats_db_global['novos_descontos']:>12}")
print(f"Produtos que PERDERAM desconto: {stats_db_global['perdeu_desconto']:>12}")
print(f"Produtos sem alteracao: {stats_db_global['sem_alteracao']:>12}")
print("=================================================")

# Mostrar estatísticas do banco de dados
estatisticas_db = consulta_db_estatisticas('Dental Speed')