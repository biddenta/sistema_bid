import sys, os, time, requests, re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import atualizar_precos_produtos, consulta_db_estatisticas

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
    
    print(f"📂 {len(links_unicos)} categorias para atualização.")
    return links_unicos

def extrair_categoria_do_url(url):
    """Extrai o nome da categoria do URL"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        
        if '?' in path:
            path = path.split('?')[0]
        
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

def extrair_produtos_pagina_rapido(html, url_base):
    """Extrai produtos de uma página HTML - APENAS dados para atualização diária"""
    produtos = []
    soup = BeautifulSoup(html, "html.parser")
    
    produtos_elementos = soup.find_all("div", class_="spot")
    
    for i, elemento in enumerate(produtos_elementos):
        try:
            produto = {}
            
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
            
            # Preço antigo
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
                # Verificar desconto explícito
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
            
            # Descrição do produto
            descricao_elem = elemento.find("p", class_="texto-info-spot")
            produto['descricao'] = descricao_elem.get_text(strip=True) if descricao_elem else ""
            
            # SKU/ID para identificação
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
                # Verificar se há indicadores específicos
                elemento_html = str(elemento).lower()
                if any(indicador in elemento_html for indicador in ['indisponível', 'esgotado', 'fora de estoque']):
                    produto['status'] = "Esgotado"
                else:
                    produto['status'] = "Indisponível"
            
            produtos.append(produto)
            
        except Exception as e:
            print(f"[AVISO]  Erro no produto {i+1}: {e}")
            continue
    
    return produtos

def obter_numero_total_paginas_rapido(html):
    """Extrai o número total de páginas rapidamente"""
    soup = BeautifulSoup(html, "html.parser")
    
    # Buscar paginação
    paginacao = soup.find("section", class_="pagination")
    
    if paginacao:
        itens_pagina = paginacao.find_all("li", class_="pagination-item")
        
        max_pagina = 1
        for item in itens_pagina:
            if "dots" not in item.get("class", []) and "next" not in item.get("class", []):
                data_page = item.get("data-page")
                if data_page and data_page.isdigit():
                    numero = int(data_page)
                    if numero > max_pagina:
                        max_pagina = numero
        return max_pagina
    
    return 1

def atualizar_precos_categoria(url_categoria, categoria_nome):
    """Atualiza preços de uma categoria - OTIMIZADO para velocidade"""
    produtos_atualizados = []
    
    print(f"[PRECO] Atualizando preços: {categoria_nome}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Primeira página
            page.goto(url_categoria, timeout=30000)
            page.wait_for_load_state('networkidle')
            html_primeira = page.content()
            
            # Total de páginas
            total_paginas = obter_numero_total_paginas_rapido(html_primeira)
            
            # Produtos da primeira página
            produtos_pagina = extrair_produtos_pagina_rapido(html_primeira, url_categoria)
            produtos_atualizados.extend(produtos_pagina)
            print(f"  📄 Página 1: {len(produtos_pagina)} produtos")
            
            # Páginas restantes
            for pagina in range(2, total_paginas + 1):
                try:
                    # URL da página
                    url_base_limpa = re.sub(r'[&?]pagina=\d+', '', url_categoria)
                    
                    if "?" in url_base_limpa:
                        url_pagina = f"{url_base_limpa}&pagina={pagina}"
                    else:
                        url_pagina = f"{url_base_limpa}?pagina={pagina}"
                    
                    page.goto(url_pagina, timeout=30000)
                    page.wait_for_load_state('networkidle')
                    html_pagina = page.content()
                    
                    produtos_pagina = extrair_produtos_pagina_rapido(html_pagina, url_categoria)
                    
                    if produtos_pagina:
                        produtos_atualizados.extend(produtos_pagina)
                        print(f"  📄 Página {pagina}: {len(produtos_pagina)} produtos")
                    else:
                        print(f"  📄 Página {pagina}: Vazia - parando")
                        break
                    
                    # Pausa mínima
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"  [ERRO] Erro página {pagina}: {e}")
                    continue
        
        finally:
            browser.close()
    
    print(f"  [OK] {len(produtos_atualizados)} produtos atualizados")
    return produtos_atualizados

def main():
    """Função principal - Atualização DIÁRIA rápida"""
    print("[RAPIDO] ATUALIZAÇÃO DIÁRIA - APOIO DENTAL")
    print("=" * 50)
    print("[ALVO] Atualizando apenas:")
    print("   [OK] Preços atuais")
    print("   [OK] Descontos") 
    print("   [OK] Disponibilidade")
    print("   [OK] URLs atualizadas")
    print("=" * 50)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Nenhuma categoria encontrada!")
        return
    
    todos_produtos_atualizados = []
    site_nome = "Apoio Dental"
    
    inicio_tempo = time.time()
    
    # Processar cada categoria
    for i, url_categoria in enumerate(links_categorias, 1):
        try:
            categoria_nome = extrair_categoria_do_url(url_categoria)
            
            print(f"\n📂 [{i}/{len(links_categorias)}] {categoria_nome}")
            
            produtos_categoria = atualizar_precos_categoria(url_categoria, categoria_nome)
            
            if produtos_categoria:
                todos_produtos_atualizados.extend(produtos_categoria)
            
            # Pausa mínima entre categorias
            time.sleep(1)
                
        except Exception as e:
            print(f"[ERRO] Erro na categoria {url_categoria}: {e}")
            continue
    
    # Atualizar banco de dados
    if todos_produtos_atualizados:
        tempo_coleta = time.time() - inicio_tempo
        
        print(f"\n[SALVANDO] ATUALIZANDO BANCO DE DADOS")
        print(f"[TEMPO]  Tempo de coleta: {tempo_coleta:.1f}s")
        print(f"[STATS] Produtos coletados: {len(todos_produtos_atualizados)}")
        print("-" * 40)
        
        try:
            # Atualizar preços no banco
            atualizar_precos_produtos(todos_produtos_atualizados, site_nome)
            print("[OK] Preços atualizados com sucesso!")
            
            # Estatísticas
            consulta_db_estatisticas(site_nome)
            
            tempo_total = time.time() - inicio_tempo
            print(f"\n[TEMPO]  Tempo total: {tempo_total:.1f}s")
            print(f"[INICIO] Velocidade: {len(todos_produtos_atualizados)/tempo_total:.1f} produtos/segundo")
            
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar banco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERRO] Nenhum produto coletado para atualização.")
    
    print("\n[RAPIDO] ATUALIZAÇÃO DIÁRIA CONCLUÍDA!")

if __name__ == "__main__":
    main()
