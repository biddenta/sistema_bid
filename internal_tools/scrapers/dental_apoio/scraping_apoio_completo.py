import sys, os, time, requests, re, json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

# Configurar sessão HTTP otimizada
session = requests.Session()
retry_strategy = Retry(
    total=2, 
    backoff_factor=0.1,  
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
session.mount("http://", adapter)
session.mount("https://", adapter)

def ler_links_categorias():
    """Lê os links de categorias do arquivo"""
    arquivo_links = os.path.join(os.path.dirname(__file__), "links_categorias_apoio.txt")
    links = []
    
    if os.path.exists(arquivo_links):
        with open(arquivo_links, "r", encoding="utf-8") as f:
            links = [linha.strip() for linha in f if linha.strip()]
    
    # Remove duplicatas mantendo ordem
    links_unicos = []
    for link in links:
        if link not in links_unicos:
            links_unicos.append(link)
    
    print(f"📂 Total de {len(links_unicos)} categorias encontradas.")
    return links_unicos

def extrair_categoria_do_url(url):
    """Extrai o nome da categoria do URL"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        
        if '?' in path:
            path = path.split('?')[0]
        
        # Mapeamento de categorias
        categoria_map = {
            'instrumentais': 'Instrumentais',
            'protese': 'Prótese',
            'ortodontia': 'Ortodontia',
            'dentistica-e-estetica': 'Dentística e Estética',
            'endodontia': 'Endodontia',
            'cimentos': 'Cimentos',
            'brocas': 'Brocas',
            'cirurgia-e-periodontia': 'Cirurgia e Periodontia',
            'descartaveis': 'Descartáveis',
            'para-o-consultorio': 'Para o Consultório',
            'higiene-oral': 'Higiene Oral',
            'prevencao-e-profilaxia': 'Prevenção e Profilaxia',
            'radiologia': 'Radiologia',
            'moldagem': 'Moldagem'
        }
        
        return categoria_map.get(path.lower(), path.replace('-', ' ').title())
    except:
        return "Categoria Desconhecida"

def extrair_categorias_e_subcategorias(url_produto):
    """Extrai categorias e subcategorias da página do produto usando breadcrumb"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(url_produto, timeout=30000)
                page.wait_for_load_state('networkidle')
                html = page.content()
                
                soup = BeautifulSoup(html, "html.parser")
                
                # Buscar breadcrumb para categorias
                breadcrumb = soup.find("nav", {"class": re.compile(r"breadcrumb|navigation")}) or \
                           soup.find("ol", {"class": re.compile(r"breadcrumb")}) or \
                           soup.find("ul", {"class": re.compile(r"breadcrumb")}) or \
                           soup.find("div", {"class": re.compile(r"breadcrumb")})
                
                if breadcrumb:
                    # Extrair todos os links do breadcrumb
                    links_breadcrumb = breadcrumb.find_all("a")
                    categorias = []
                    
                    for link in links_breadcrumb:
                        texto = link.get_text(strip=True)
                        if texto and texto.lower() not in ['home', 'início', 'apoio dental', 'principal']:
                            categorias.append(texto)
                    
                    # Determinar categoria principal e subcategoria
                    if len(categorias) >= 2:
                        categoria_principal = categorias[0]
                        subcategoria = categorias[1]
                    elif len(categorias) == 1:
                        categoria_principal = categorias[0]
                        subcategoria = None
                    else:
                        categoria_principal = None
                        subcategoria = None
                    
                    return {
                        'categoria_principal': categoria_principal,
                        'subcategoria': subcategoria,
                        'categorias_completas': ' > '.join(categorias) if categorias else None
                    }
                
            finally:
                browser.close()
                
        return {
            'categoria_principal': None,
            'subcategoria': None, 
            'categorias_completas': None
        }
        
    except Exception as e:
        print(f"[AVISO]  Erro ao extrair categorias de {url_produto}: {e}")
        return {
            'categoria_principal': None,
            'subcategoria': None,
            'categorias_completas': None
        }

def extrair_imagens_produto(url_produto):
    """Extrai todas as imagens do produto"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(url_produto, timeout=30000)
                page.wait_for_load_state('networkidle')
                html = page.content()
                
                soup = BeautifulSoup(html, "html.parser")
                
                # Buscar todas as imagens do produto
                imagens = soup.find_all("img")
                imagens_produto = []
                
                for img in imagens:
                    src = img.get('src', '')
                    
                    # Filtrar apenas imagens de produto
                    if any(keyword in src.lower() for keyword in ['product', 'item', 'foto', 'imagem', '/uploads/', '/media/', 'produtos']):
                        if src:
                            # Converter para URL absoluta
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif src.startswith('/'):
                                src = urljoin(url_produto, src)
                            elif not src.startswith('http'):
                                src = urljoin(url_produto, src)
                            
                            if src not in imagens_produto:
                                imagens_produto.append(src)
                
                # Retornar no formato esperado pelo banco
                imagem_principal = imagens_produto[0] if imagens_produto else None
                
                # Imagens extras (até 4 adicionais)
                imagens_extras = imagens_produto[1:5] if len(imagens_produto) > 1 else []
                
                return {
                    'imagem_principal': imagem_principal,
                    'imagens_extras': json.dumps(imagens_extras) if imagens_extras else None
                }
                
            finally:
                browser.close()
                
    except Exception as e:
        print(f"[AVISO]  Erro ao extrair imagens de {url_produto}: {e}")
        return {
            'imagem_principal': None,
            'imagens_extras': None
        }

def extrair_detalhes_completos_produto(url_produto):
    """Extrai descrição, especificações e marca da página do produto"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(url_produto, timeout=30000)
                page.wait_for_load_state('networkidle')
                html = page.content()
                
                soup = BeautifulSoup(html, "html.parser")
                detalhes = {}
                
                # Descrição detalhada
                descricao_elem = soup.find("div", {"class": re.compile(r"description|details|content|info")}) or \
                               soup.find("div", {"id": re.compile(r"description|details")}) or \
                               soup.find("section", {"class": re.compile(r"description|product-info")})
                
                if descricao_elem:
                    descricao = descricao_elem.get_text(strip=True)
                    # Limpar texto
                    descricao = re.sub(r'\s+', ' ', descricao)
                    detalhes['descricao_completa'] = descricao[:1000]  # Limitar tamanho
                else:
                    detalhes['descricao_completa'] = None
                
                # Especificações técnicas
                specs_elem = soup.find("div", {"class": re.compile(r"spec|technical|features|caracteristicas")}) or \
                           soup.find("table", {"class": re.compile(r"spec|details|info")})
                
                if specs_elem:
                    specs = specs_elem.get_text(strip=True)
                    specs = re.sub(r'\s+', ' ', specs)
                    detalhes['especificacoes'] = specs[:500]  # Limitar tamanho
                else:
                    detalhes['especificacoes'] = None
                
                # Marca
                marca_elem = soup.find("span", {"class": re.compile(r"brand|marca|manufacturer")}) or \
                           soup.find("div", {"class": re.compile(r"brand|marca")}) or \
                           soup.find("p", {"class": re.compile(r"brand|marca")})
                
                if marca_elem:
                    detalhes['marca_detalhada'] = marca_elem.get_text(strip=True)
                else:
                    detalhes['marca_detalhada'] = None
                
                return detalhes
                
            finally:
                browser.close()
                
    except Exception as e:
        print(f"[AVISO]  Erro ao extrair detalhes de {url_produto}: {e}")
        return {
            'descricao_completa': None,
            'especificacoes': None,
            'marca_detalhada': None
        }

def extrair_produtos_pagina_completo(html, categoria_base, url_base):
    """Extrai produtos de uma página HTML com TODOS os dados"""
    produtos = []
    soup = BeautifulSoup(html, "html.parser")
    
    produtos_elementos = soup.find_all("div", class_="spot")
    print(f"[INFO] Encontrados {len(produtos_elementos)} produtos na página")
    
    for i, elemento in enumerate(produtos_elementos):
        try:
            produto = {}
            
            # DADOS BÁSICOS (sempre coletados)
            
            # Nome do produto - Verificar title completo vs texto truncado
            nome_elem = elemento.find("a", class_="spot-title")
            if nome_elem:
                # Tentar obter nome completo do atributo title
                nome_completo = nome_elem.get('title', '').strip()
                if nome_completo:
                    produto['nome'] = nome_completo
                else:
                    produto['nome'] = nome_elem.get_text(strip=True)
                
                # URL do produto
                href = nome_elem.get('href', '')
                if href:
                    produto['url'] = urljoin(url_base, href)
                else:
                    produto['url'] = ""
            else:
                produto['nome'] = f"Produto {i+1}"
                produto['url'] = ""
            
            # Preço atual
            preco_elem = elemento.find("p", class_="spot-price__after")
            if preco_elem:
                preco_texto = preco_elem.get_text(strip=True)
                preco_match = re.search(r'R\$\s*([\d.,]+)', preco_texto)
                if preco_match:
                    preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                    produto['preco'] = float(preco_str)
                else:
                    produto['preco'] = 0
            else:
                produto['preco'] = 0
            
            # Preço antigo e desconto
            preco_antigo_elem = elemento.find("span", class_="spot-price__line")
            if preco_antigo_elem:
                preco_antigo_texto = preco_antigo_elem.get_text(strip=True)
                preco_antigo_match = re.search(r'R\$\s*([\d.,]+)', preco_antigo_texto)
                if preco_antigo_match:
                    preco_antigo_str = preco_antigo_match.group(1).replace('.', '').replace(',', '.')
                    produto['preco_antigo'] = float(preco_antigo_str)
                else:
                    produto['preco_antigo'] = None
            else:
                produto['preco_antigo'] = None
            
            # Calcular desconto
            if produto['preco_antigo'] and produto['preco_antigo'] > produto['preco'] and produto['preco'] > 0:
                desconto = ((produto['preco_antigo'] - produto['preco']) / produto['preco_antigo']) * 100
                produto['porcentagem_desconto'] = round(desconto, 2)
            else:
                desconto_elem = elemento.find("p", class_="spot-price__discount")
                if desconto_elem:
                    desconto_texto = desconto_elem.get_text(strip=True)
                    desconto_match = re.search(r'(\d+)%', desconto_texto)
                    if desconto_match:
                        produto['porcentagem_desconto'] = float(desconto_match.group(1))
                    else:
                        produto['porcentagem_desconto'] = 0
                else:
                    produto['porcentagem_desconto'] = 0
            
            # Descrição básica
            descricao_elem = elemento.find("p", class_="texto-info-spot")
            produto['descricao'] = descricao_elem.get_text(strip=True) if descricao_elem else ""
            
            # SKU/ID
            sku = None
            botao_compra = elemento.find("a", class_="spot-button__buy")
            if botao_compra and botao_compra.get('onclick'):
                onclick = botao_compra.get('onclick')
                sku_match = re.search(r'["\'](\d+)["\']', onclick)
                if sku_match:
                    sku = sku_match.group(1)
            
            if not sku and produto['url']:
                url_parts = produto['url'].split('/')
                for part in reversed(url_parts):
                    if part and part.isdigit():
                        sku = part
                        break
            
            produto['sku'] = sku if sku else f"apoio_{i}"
            
            # Marca - Usar função universal
            marca_extraida, nome_sem_marca = extrair_marca_universal(produto['nome'])
            
            if marca_extraida:
                # [OK] Marca extraída via função universal
                produto['marca'] = marca_extraida
                produto['nome_limpo'] = nome_sem_marca  # Bonus: nome sem marca
                print(f"   [OK] Marca extraída (universal): {marca_extraida}")
            else:
                # [ERRO] Marca não identificada
                produto['marca'] = "Marca não identificada"
                produto['nome_limpo'] = produto['nome']
                print(f"   [ERRO] Marca não identificada: {produto['nome'][:50]}...")
            
            # Gerar chave de matching
            if produto.get('marca') and produto['marca'] != "Marca não identificada":
                produto['chave_matching'] = f"{produto['nome_limpo'].upper().strip()}_{produto['marca'].upper().strip()}"
            else:
                produto['chave_matching'] = produto['nome'].upper().strip()
            
            # Status disponibilidade
            if produto['preco'] > 0:
                produto['disponivel'] = True
                produto['status'] = "Disponível"
            else:
                produto['disponivel'] = False
                produto['status'] = "Indisponível"
            
            # Categoria base
            produto['categoria_base'] = categoria_base
            
            # DADOS COMPLETOS (coletados da página individual)
            print(f"  📄 Extraindo dados completos do produto {i+1}/{len(produtos_elementos)}: {produto['nome'][:50]}...")
            
            if produto['url']:
                # Extrair categorias e subcategorias
                categorias_info = extrair_categorias_e_subcategorias(produto['url'])
                produto.update(categorias_info)
                
                # Se não conseguiu extrair da página, usar categoria base
                if not produto['categoria_principal']:
                    produto['categoria_principal'] = categoria_base
                    produto['subcategoria'] = None
                
                # Extrair imagens
                imagens_info = extrair_imagens_produto(produto['url'])
                produto.update(imagens_info)
                
                # Extrair detalhes completos
                detalhes_info = extrair_detalhes_completos_produto(produto['url'])
                produto.update(detalhes_info)
                
                # Atualizar marca se encontrou uma melhor
                if detalhes_info.get('marca_detalhada'):
                    produto['marca'] = detalhes_info['marca_detalhada']
                
                # Pausa entre produtos para não sobrecarregar
                time.sleep(0.5)
            else:
                # Se não tem URL, usar dados básicos
                produto['categoria_principal'] = categoria_base
                produto['subcategoria'] = None
                produto['imagem_principal'] = None
                produto['imagens_extras'] = None
                produto['descricao_completa'] = produto['descricao']
                produto['especificacoes'] = None
                produto['marca_detalhada'] = None
            
            produtos.append(produto)
            
        except Exception as e:
            print(f"[ERRO] Erro ao extrair produto {i+1}: {e}")
            continue
    
    return produtos

def obter_numero_total_paginas(html):
    """Extrai o número total de páginas da paginação"""
    soup = BeautifulSoup(html, "html.parser")
    
    paginacao = soup.find("section", class_="pagination")
    
    if paginacao:
        itens_pagina = paginacao.find_all("li", class_="pagination-item")
        
        if itens_pagina:
            max_pagina = 1
            for item in itens_pagina:
                if "dots" not in item.get("class", []) and "next" not in item.get("class", []):
                    data_page = item.get("data-page")
                    if data_page and data_page.isdigit():
                        numero = int(data_page)
                        if numero > max_pagina:
                            max_pagina = numero
            return max_pagina
    
    # Alternativa: buscar informação de total de produtos
    info_total = soup.find(text=re.compile(r'(\d+)\s*produtos?\s*encontrados?', re.IGNORECASE))
    if info_total:
        match = re.search(r'(\d+)', info_total)
        if match:
            total_produtos = int(match.group(1))
            return (total_produtos // 48) + 1  # 48 produtos por página
    
    return 1

def extrair_categoria_completa(url_categoria, categoria_base):
    """Extrai TODOS os produtos de uma categoria com dados completos"""
    produtos_categoria = []
    
    print(f"\n🗂️  === CATEGORIA: {categoria_base} ===")
    print(f"[LINK] URL: {url_categoria}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("📄 Acessando primeira página...")
            page.goto(url_categoria, timeout=30000)
            page.wait_for_load_state('networkidle')
            html_primeira = page.content()
            
            # Descobrir total de páginas
            total_paginas = obter_numero_total_paginas(html_primeira)
            print(f"[STATS] Total de páginas: {total_paginas}")
            
            # Extrair produtos da primeira página
            produtos_pagina = extrair_produtos_pagina_completo(html_primeira, categoria_base, url_categoria)
            produtos_categoria.extend(produtos_pagina)
            print(f"[OK] Página 1: {len(produtos_pagina)} produtos extraídos")
            
            # Processar páginas restantes (limitado a 10 páginas para teste)
            max_paginas = min(total_paginas, 10)  # LIMITE PARA TESTE - remover em produção
            
            for pagina in range(2, max_paginas + 1):
                try:
                    # Construir URL da página
                    url_base_limpa = re.sub(r'[&?]pagina=\d+', '', url_categoria)
                    
                    if "?" in url_base_limpa:
                        url_pagina = f"{url_base_limpa}&pagina={pagina}"
                    else:
                        url_pagina = f"{url_base_limpa}?pagina={pagina}"
                    
                    print(f"📄 Extraindo página {pagina}/{max_paginas}...")
                    
                    page.goto(url_pagina, timeout=30000)
                    page.wait_for_load_state('networkidle')
                    html_pagina = page.content()
                    
                    produtos_pagina = extrair_produtos_pagina_completo(html_pagina, categoria_base, url_categoria)
                    
                    if produtos_pagina:
                        produtos_categoria.extend(produtos_pagina)
                        print(f"[OK] Página {pagina}: {len(produtos_pagina)} produtos extraídos")
                    else:
                        print(f"[AVISO]  Página {pagina}: Nenhum produto encontrado")
                        break
                    
                    # Pausa entre páginas
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[ERRO] Erro na página {pagina}: {e}")
                    continue
        
        finally:
            browser.close()
    
    print(f"[ALVO] Total extraído da categoria {categoria_base}: {len(produtos_categoria)} produtos")
    return produtos_categoria

def main():
    """Função principal - Coleta COMPLETA para comparador de preços"""
    print("[INICIO] SCRAPING COMPLETO - APOIO DENTAL")
    print("=" * 60)
    print("[INFO] Coletando TODOS os dados para comparador de preços:")
    print("   [OK] Categoria principal e subcategoria")
    print("   [OK] Imagens completas")
    print("   [OK] Descrição detalhada")
    print("   [OK] Especificações técnicas")
    print("   [OK] Marca detalhada")
    print("   [OK] Preço, desconto, disponibilidade")
    print("=" * 60)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Nenhuma categoria encontrada!")
        return
    
    todos_produtos = []
    site_nome = "Apoio Dental"
    
    # Processar cada categoria
    for i, url_categoria in enumerate(links_categorias, 1):
        try:
            categoria_base = extrair_categoria_do_url(url_categoria)
            
            print(f"\n{'='*80}")
            print(f"📂 PROCESSANDO {i}/{len(links_categorias)}: {categoria_base}")
            print(f"{'='*80}")
            
            produtos_categoria = extrair_categoria_completa(url_categoria, categoria_base)
            
            if produtos_categoria:
                todos_produtos.extend(produtos_categoria)
                print(f"[OK] {len(produtos_categoria)} produtos coletados de {categoria_base}")
            else:
                print(f"[AVISO]  Nenhum produto encontrado em {categoria_base}")
            
            # Pausa entre categorias
            print("⏳ Pausando 5 segundos...")
            time.sleep(5)
                
        except Exception as e:
            print(f"[ERRO] Erro ao processar categoria {url_categoria}: {e}")
            continue
    
    # Salvar no banco de dados
    if todos_produtos:
        print(f"\n[SALVANDO] SALVANDO {len(todos_produtos)} PRODUTOS NO BANCO")
        print("=" * 50)
        
        try:
            salvar_produtos_db(todos_produtos, "Apoio Dental", site_nome)
            print("[OK] Produtos salvos com sucesso!")
            
            # Estatísticas
            consulta_db_estatisticas(site_nome)
            
        except Exception as e:
            print(f"[ERRO] Erro ao salvar no banco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERRO] Nenhum produto foi coletado.")
    
    print("\n[SUCESSO] COLETA COMPLETA FINALIZADA!")

if __name__ == "__main__":
    main()
