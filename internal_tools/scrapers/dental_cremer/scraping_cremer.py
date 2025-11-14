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


# 1 Extrair nomes das marcas do site

print("Acessando o site...")

url = "https://www.dentalcremer.com.br/marcas"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, timeout=30000)
    page.wait_for_load_state('networkidle')
    html = page.content()

soup = BeautifulSoup(html, "html.parser")

marcas = []
for li in soup.find_all("li", class_="filtered"):
    a = li.find("a")
    if a and a.text and a.get("href"):
        marcas.append((a.text.strip(), a["href"]))

# 2 Detectar alterações e salvar

# CORREÇÃO: Criar arquivo na pasta do script, não na raiz  
script_dir = os.path.dirname(os.path.abspath(__file__))
arquivo_marcas = os.path.join(script_dir, "marcas_extraidas_dental_cremer.txt")
marcas_atuais = set(f"{nome} -> {link}" for nome, link in marcas)

marcas_anteriores = set()
if os.path.exists(arquivo_marcas):
    with open(arquivo_marcas, "r", encoding="utf-8") as f:
        marcas_anteriores = set(linha.strip() for linha in f if linha.strip())

with open(arquivo_marcas, "w", encoding="utf-8") as f:
    for linha in sorted(marcas_atuais):
        f.write(linha + "\n")

adicionadas = marcas_atuais - marcas_anteriores
removidas = marcas_anteriores - marcas_atuais

if adicionadas:
    print("Novas marcas adicionadas:")
    for linha in sorted(adicionadas):
        print("[ADICIONADA]", linha)
if removidas:
    print("Marcas removidas:")
    for linha in sorted(removidas):
        print("[REMOVIDA]", linha)
if not adicionadas and not removidas:
    print("Nenhuma alteração nas marcas.")

# 3 Função para extrair categorias de forma melhorada ===

def extrair_marca_corretamente(produto):
    """Extrai a marca correta do produto com fallback universal"""
    # 1. Tentar details.brand primeiro (fonte principal da API)
    if produto.get("details", {}).get("brand"):
        marca = produto["details"]["brand"]
        if isinstance(marca, list) and len(marca) > 0:
            marca_api = marca[0]
            if marca_api and marca_api.strip() and marca_api != "N/A":
                print(f"   [OK] Marca da API: {marca_api}")
                return marca_api, produto.get("name", "")  # Retorna marca e nome original
        elif isinstance(marca, str) and marca.strip() and marca != "N/A":
            print(f"   [OK] Marca da API: {marca}")
            return marca, produto.get("name", "")
    
    # 2. Fallback: verificar SKUs
    if produto.get("skus") and len(produto["skus"]) > 0:
        sku_brand = produto["skus"][0].get("properties", {}).get("details", {}).get("brand")
        if sku_brand and sku_brand.strip() and sku_brand != "N/A":
            print(f"   [OK] Marca do SKU: {sku_brand}")
            return sku_brand, produto.get("name", "")
    
    # 3. Fallback universal: usar função universal
    nome = produto.get("name", "")
    if nome:
        marca_extraida, nome_sem_marca = extrair_marca_universal(nome)
        
        if marca_extraida:
            print(f"   [OK] Marca extraída (universal): {marca_extraida}")
            return marca_extraida, nome_sem_marca
        else:
            print(f"   [ERRO] Marca não identificada: {nome[:50]}...")
            return "Marca não identificada", nome
    
    return "Marca não identificada", nome

def limpar_nome_produto(nome):
    """Padroniza nome do produto para matching"""
    import re
    
    # Remover caracteres especiais e normalizar
    nome = re.sub(r'[^\w\s-]', '', nome)
    nome = re.sub(r'\s+', ' ', nome)
    nome = nome.strip().lower()
    
    # Remover palavras comuns que não ajudam no matching
    palavras_remover = ['unidade', 'embalagem', 'com', 'peça', 'peças', 'kit', 'c/', 'c']
    palavras = nome.split()
    palavras_filtradas = [p for p in palavras if p not in palavras_remover and len(p) > 1]
    
    return ' '.join(palavras_filtradas)

def extrair_codigo_fabricante(produto):
    """Extrai código do fabricante quando disponível"""
    # Verificar em SKUs primeiro
    if produto.get("skus") and len(produto["skus"]) > 0:
        cod_fabricante = produto["skus"][0].get("properties", {}).get("details", {}).get("cod_fabricante")
        if cod_fabricante:
            return cod_fabricante
    
    # Verificar em details
    if produto.get("details", {}).get("cod_fabricante"):
        cod_fabricante = produto["details"]["cod_fabricante"]
        if isinstance(cod_fabricante, list) and len(cod_fabricante) > 0:
            return cod_fabricante[0]
        return cod_fabricante
    
    return None

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
    """Busca produtos de uma marca com paginação completa - OTIMIZADO"""
    # Formatações do nome da marca
    marca_sem_espacos = marca_nome.lower().replace(' ', '')
    marca_com_underscore = marca_nome.lower().replace(' ', '_')
    
    # Headers essenciais
    headers = {
        "accept": "*/*",
        "origin": "https://www.dentalcremer.com.br",
        "referer": "https://www.dentalcremer.com.br/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    def buscar_com_paginacao_rapida(url, params_base, headers):
        """Função auxiliar otimizada para buscar com paginação"""
        todos_produtos = []
        pagina = 1
        max_paginas = 10  # Reduzido para acelerar
        
        while pagina <= max_paginas:
            params = params_base.copy()
            if pagina > 1:
                params['page'] = pagina
            
            try:
                # Timeout reduzido para 5 segundos
                response = session.get(url, headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'products' in data and data['products']:
                        produtos_pagina = data['products']
                        todos_produtos.extend(produtos_pagina)
                        
                        # Se menos produtos que o esperado, é a última página
                        if len(produtos_pagina) < params.get('resultsperpage', 100):
                            break
                            
                        pagina += 1
                    else:
                        break
                else:
                    break
            except (requests.exceptions.RequestException, KeyError, TypeError):
                break
        
        return todos_produtos

    # URLs dos endpoints
    url_navigates = "https://api.linximpulse.com/engage/search/v3/navigates"
    url_hotsites = "https://api.linximpulse.com/engage/search/v3/hotsites"
    
    # Estratégia otimizada: testar primeiro o formato mais comum
    formatos = [marca_com_underscore, marca_sem_espacos]
    
    # 1. Tentar navigates primeiro (mais rápido)
    for nome_formatado in formatos:
        params_navigates = {
            "apikey": "dentalcremer-sandbox",
            "fields": f"brand:{nome_formatado}",
            "source": "desktop",
            "deviceid": "undefined",
            "resultsperpage": 100
        }
        
        produtos = buscar_com_paginacao_rapida(url_navigates, params_navigates, headers)
        
        if produtos:
            produtos_processados = []
            for p in produtos:
                # Extrair categorias usando a nova função
                categorias_info = extrair_categorias_melhorada(p)
                
                # Extrair imagens usando a nova função
                imagens_info = extrair_imagens_produto(p)
                
                # Extrair marca correta com novo sistema híbrido
                marca_produto, nome_limpo_marca = extrair_marca_corretamente(p)
                
                # Gerar chave de matching
                if marca_produto and marca_produto not in ['N/A', '', 'Marca não identificada']:
                    chave_matching = f"{nome_limpo_marca.upper().strip()}_{marca_produto.upper().strip()}"
                else:
                    chave_matching = p.get("name", "").upper().strip()
                
                # REGRA PRINCIPAL (corrigida):
                
                
                preco_produto = float(p.get("price", 0)) if p.get("price") else 0
                flag_disponivel = p.get("available", True)  # Padrão True se campo não existir
                disponivel_real = preco_produto > 0 and flag_disponivel
                
                # Criar nome limpo para matching
                nome_limpo = limpar_nome_produto(p.get("name", ""))
                
                produto_dict = {
                    "nome": p.get("name", "Sem nome"),
                    "preco": preco_produto,
                    "preco_antigo": float(p.get("oldPrice", 0)) if p.get("oldPrice") else None,
                    "porcentagem_desconto": round(((float(p.get("oldPrice", 0)) - float(p.get("price", 0))) / float(p.get("oldPrice", 1))) * 100, 2) if p.get("oldPrice") and float(p.get("oldPrice", 0)) > 0 and float(p.get("price", 0)) > 0 else 0,
                    "sku": p.get("id", "Sem SKU"),
                    "url": f"https://www.dentalcremer.com.br{p.get('url', '')}" if p.get('url') else "Sem link",
                    "disponivel": disponivel_real,
                    "status": "Disponível" if disponivel_real else "Indisponível",
                    "categoria_principal": categorias_info['categoria_principal'],
                    "subcategoria": categorias_info['subcategoria'],
                    "categorias_completas": categorias_info['categoria_completa'],
                    "imagem_principal": imagens_info['imagem_principal'],
                    "imagens_extras": imagens_info['imagens_extras'],
                    "marca_produto": marca_produto,  # CORRIGIDO: usando função adequada
                    "descricao": p.get("description", "N/A")[:200] + "..." if p.get("description") and len(str(p.get("description"))) > 200 else str(p.get("description", "N/A")),
                    "detalhes_produto": str(p.get("details", "N/A")),
                    
                    # Campos adicionais para matching
                    "nome_limpo": nome_limpo,
                    "chave_matching_principal": f"{marca_produto}|{nome_limpo}" if marca_produto != "N/A" else nome_limpo,
                    "codigo_fabricante": extrair_codigo_fabricante(p),
                    "site": "Dental Cremer"
                }
                produtos_processados.append(produto_dict)
            
            return produtos_processados

    # 2. Tentar hotsites se navigates não funcionou
    for nome_formatado in formatos:
        params_hotsites = {
            "apikey": "dentalcremer-sandbox",
            "name": nome_formatado,
            "source": "desktop",
            "deviceid": "undefined",
            "resultsperpage": 100
        }

        produtos = buscar_com_paginacao_rapida(url_hotsites, params_hotsites, headers)
        
        if produtos:
            produtos_processados = []
            for p in produtos:
                # Extrair categorias usando a nova função
                categorias_info = extrair_categorias_melhorada(p)
                
                # Extrair imagens usando a nova função
                imagens_info = extrair_imagens_produto(p)
                
                # Extrair marca correta com novo sistema híbrido
                marca_produto, nome_limpo_marca = extrair_marca_corretamente(p)
                
                # Gerar chave de matching
                if marca_produto and marca_produto not in ['N/A', '', 'Marca não identificada']:
                    chave_matching = f"{nome_limpo_marca.upper().strip()}_{marca_produto.upper().strip()}"
                else:
                    chave_matching = p.get("name", "").upper().strip()
                
                # REGRA PRINCIPAL (corrigida):
                
                
                preco_produto = float(p.get("price", 0)) if p.get("price") else 0
                flag_disponivel = p.get("available", True)  # Padrão True se campo não existir
                disponivel_real = preco_produto > 0 and flag_disponivel
                
                # Criar nome limpo para matching
                nome_limpo = limpar_nome_produto(p.get("name", ""))
                
                produto_dict = {
                    "nome": p.get("name", "Sem nome"),
                    "preco": preco_produto,
                    "preco_antigo": float(p.get("oldPrice", 0)) if p.get("oldPrice") else None,
                    "porcentagem_desconto": round(((float(p.get("oldPrice", 0)) - float(p.get("price", 0))) / float(p.get("oldPrice", 1))) * 100, 2) if p.get("oldPrice") and float(p.get("oldPrice", 0)) > 0 and float(p.get("price", 0)) > 0 else 0,
                    "sku": p.get("id", "Sem SKU"),
                    "url": f"https://www.dentalcremer.com.br{p.get('url', '')}" if p.get('url') else "Sem link",
                    "disponivel": disponivel_real,
                    "status": "Disponível" if disponivel_real else "Indisponível",
                    "categoria_principal": categorias_info['categoria_principal'],
                    "subcategoria": categorias_info['subcategoria'],
                    "categorias_completas": categorias_info['categoria_completa'],
                    "imagem_principal": imagens_info['imagem_principal'],
                    "imagens_extras": imagens_info['imagens_extras'],
                    "marca_produto": marca_produto,  # CORRIGIDO: usando função adequada
                    "descricao": p.get("description", "N/A")[:200] + "..." if p.get("description") and len(str(p.get("description"))) > 200 else str(p.get("description", "N/A")),
                    "detalhes_produto": str(p.get("details", "N/A")),
                    
                    # Campos adicionais para matching
                    "nome_limpo": nome_limpo,
                    "chave_matching_principal": f"{marca_produto}|{nome_limpo}" if marca_produto != "N/A" else nome_limpo,
                    "codigo_fabricante": extrair_codigo_fabricante(p),
                    "site": "Dental Cremer"
                }
                produtos_processados.append(produto_dict)
            
            return produtos_processados

    return []


# 4 Realização das consultas

print("\n Coletando produtos por marca...\n")

# Variáveis para contagem e performance
stats = {"total_produtos": 0, "com_produtos": 0, "sem_produtos": 0}
stats_db_global = {"novos": 0, "atualizados": 0, "sem_alteracao": 0, "mudanca_disponibilidade": 0, "novos_descontos": 0, "perdeu_desconto": 0}

for i, (nome_marca, _) in enumerate(marcas, 1):
    print(f"[{i}/{len(marcas)}] {nome_marca}...", end=" ", flush=True)
    
    produtos = buscar_produtos_api(nome_marca)
    
    if produtos:
        stats["total_produtos"] += len(produtos)
        stats["com_produtos"] += 1
        print(f"[OK] {len(produtos)} produtos")
        
        # Salvar produtos no banco de dados
        stats_db = salvar_produtos_db(produtos, nome_marca, "Dental Cremer")
        
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
print("\nRESUMO DO SCRAPING:")
print("=" * 60)
print(f"Marcas processadas:             {len(marcas):>12}")
print(f"Produtos encontrados:           {stats['total_produtos']:>12}")
print(f"Marcas com produtos:            {stats['com_produtos']:>12}")
print(f"Marcas sem produtos:            {stats['sem_produtos']:>12}")
print("-" * 60)
print(f"Produtos NOVOS no banco:        {stats_db_global['novos']:>12}")
print(f"Produtos ATUALIZADOS no banco:  {stats_db_global['atualizados']:>12}")
print(f"Mudancas de DISPONIBILIDADE:    {stats_db_global['mudanca_disponibilidade']:>12}")
print(f"Produtos com NOVOS DESCONTOS:   {stats_db_global['novos_descontos']:>12}")
print(f"Produtos que PERDERAM desconto: {stats_db_global['perdeu_desconto']:>12}")
print(f"Produtos sem alteracao:         {stats_db_global['sem_alteracao']:>12}")
print("=" * 60)

# Mostrar estatísticas do banco de dados
estatisticas_db = consulta_db_estatisticas('Dental Cremer')