import sys, os, time, requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Desabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas, atualizar_precos_produtos

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

# Configurar sessão HTTP otimizada
session = requests.Session()
retry_strategy = Retry(
    total=3, 
    backoff_factor=0.1,  
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=50)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Headers para simular navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def fazer_requisicao(url, timeout=15):
    """Faz requisição HTTP otimizada para atualizações rápidas"""
    try:
        response = session.get(
            url, 
            headers=HEADERS, 
            verify=False, 
            timeout=timeout,
            allow_redirects=True
        )
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"[AVISO]  Status HTTP {response.status_code} para {url}")
            return None
            
    except Exception as e:
        print(f"[ERRO] Erro na requisição para {url}: {e}")
        return None

def obter_url_proxima_pagina(html):
    """Encontra a URL da próxima página usando o botão 'Próximo'"""
    soup = BeautifulSoup(html, "html.parser")
    
    botao_proximo = soup.find("li", class_="pages-item-next")
    
    if botao_proximo:
        link_proximo = botao_proximo.find("a")
        if link_proximo and link_proximo.get('href'):
            return link_proximo.get('href')
    
    return None

def extrair_produtos_pagina_rapido_requests(html, url_base):
    """Extrai produtos rapidamente - apenas dados essenciais para atualização"""
    produtos = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Buscar lista de produtos
    product_list = soup.find('ol', class_='products')
    
    if not product_list:
        return produtos
    
    produtos_elementos = product_list.find_all("li", class_="item")
    produtos_elementos = [elem for elem in produtos_elementos if 'product' in ' '.join(elem.get('class', []))]
    
    for i, elemento in enumerate(produtos_elementos):
        try:
            produto = {}
            
            # Nome do produto - Priorizar title completo sobre texto truncado
            nome_completo = ""
            nome_truncado = ""
            
            # 1. Tentar obter nome completo do atributo 'title' do link
            link_elem = elemento.find("a", class_="product-item-link")
            if link_elem:
                nome_completo = link_elem.get('title', '').strip()
                if nome_completo:
                    produto['nome'] = nome_completo
                else:
                    nome_truncado = link_elem.get_text(strip=True)
            
            # 2. Fallback: nome truncado de outros elementos
            if not produto.get('nome'):
                nome_elem = elemento.find("strong", class_="product-item-name") or \
                           elemento.find("a", class_="product-item-link")
                
                if nome_elem:
                    produto['nome'] = nome_elem.get_text(strip=True)
                else:
                    produto['nome'] = f"Produto {i+1}"
            
            # URL do produto
            if not link_elem:
                link_elem = elemento.find("a", class_="product-item-photo") or \
                           elemento.find("a", class_="product-item-link")
            
            if link_elem and link_elem.get('href'):
                produto['url'] = link_elem.get('href')
            else:
                produto['url'] = ""
            
            # Preço atual
            preco_elem = elemento.find("span", class_="price")
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
            preco_antigo_elem = elemento.find("span", class_="old-price") or \
                               elemento.find("span", class_="regular-price")
            
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
                produto['porcentagem_desconto'] = 0
            
            # Marca - Usar função universal com fallbacks para Dental Sorria
            marca_extraida, nome_sem_marca = extrair_marca_universal(produto['nome'])
            
            if marca_extraida:
                # [OK] Marca extraída via função universal
                produto['marca'] = marca_extraida
                produto['nome_limpo'] = nome_sem_marca  # Bonus: nome sem marca
                print(f"   [OK] Marca extraída (universal): {marca_extraida}")
            else:
                # [AVISO] Fallback 1: Tentar div.brand (método original)
                marca_elem = elemento.find("div", class_="brand")
                if marca_elem:
                    produto['marca'] = marca_elem.get_text(strip=True).upper()
                    produto['nome_limpo'] = produto['nome']  # Nome original pois não tem marca no título
                    print(f"   [OK] Marca extraída (div.brand): {produto['marca']}")
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
            
            # SKU/ID para identificação
            if produto['url']:
                url_parts = produto['url'].split('/')
                for part in reversed(url_parts):
                    if part and '.html' in part:
                        sku = part.replace('.html', '')
                        break
                else:
                    sku = f"sorria_{i}"
            else:
                sku = f"sorria_{i}"
            
            produto['sku'] = sku
            
            # Status disponibilidade
            if produto['preco'] > 0:
                produto['disponivel'] = True
                produto['status'] = "Disponível"
            else:
                produto['disponivel'] = False
                produto['status'] = "Indisponível"
            
            # Descrição do produto - tentar extrair do card
            descricao_container = elemento.find("div", class_="product attribute overview")
            if descricao_container:
                descricao_elem = descricao_container.find("div", class_="value", attrs={"itemprop": "description"})
                produto['descricao'] = descricao_elem.get_text(strip=True) if descricao_elem else produto['nome']
            else:
                produto['descricao'] = produto['nome']
            
            produtos.append(produto)
            
        except Exception as e:
            print(f"[AVISO]  Erro no produto {i+1}: {e}")
            continue
    
    return produtos

def atualizar_precos_categoria_requests(url_categoria, categoria_nome):
    """Atualiza preços de uma categoria usando requests puro - ULTRA RÁPIDO"""
    produtos_atualizados = []
    
    print(f"[PRECO] Atualizando preços: {categoria_nome}")
    
    url_atual = url_categoria
    pagina_numero = 1
    
    while url_atual:
        try:
            # Fazer requisição HTTP
            html_content = fazer_requisicao(url_atual, timeout=10)
            
            if not html_content:
                print(f"  [ERRO] Falha ao carregar página {pagina_numero}")
                break
            
            # Produtos da página atual
            produtos_pagina = extrair_produtos_pagina_rapido_requests(html_content, url_categoria)
            
            if produtos_pagina:
                produtos_atualizados.extend(produtos_pagina)
                print(f"  📄 Página {pagina_numero}: {len(produtos_pagina)} produtos")
            else:
                print(f"  📄 Página {pagina_numero}: Vazia - parando")
                break
            
            # Procurar próxima página
            url_proxima = obter_url_proxima_pagina(html_content)
            
            if url_proxima:
                url_atual = url_proxima
                pagina_numero += 1
                # Pausa mínima entre páginas
                time.sleep(0.1)
            else:
                print(f"  🏁 Última página alcançada!")
                break
                
        except Exception as e:
            print(f"  [ERRO] Erro página {pagina_numero}: {e}")
            break
    
    print(f"  [OK] {len(produtos_atualizados)} produtos atualizados")
    return produtos_atualizados

def extrair_marca_do_nome(nome):
    """Tenta extrair a marca do nome do produto como fallback"""
    if not nome:
        return None
    
    # Marcas conhecidas (baseado na análise)
    marcas_conhecidas = [
        'MICRODONT', 'CRISTÓFOLI', 'PROTDESC', 'LUMINOX', 'DANNY', 
        'SSPLUS', 'SCHUSTER', 'JP FARMA', 'DX', 'KSN', 'FGM',
        'DENTSPLY', 'SOLVENTUM', 'DENTSMART', 'ASFER', 'PACK GC'
    ]
    
    nome_upper = nome.upper()
    
    for marca in marcas_conhecidas:
        if marca in nome_upper:
            return marca
    
    # Tentar extrair marca do final do nome (geralmente após " - ")
    if ' - ' in nome:
        partes = nome.split(' - ')
        ultima_parte = partes[-1].strip()
        if len(ultima_parte) > 2 and len(ultima_parte) < 20:
            return ultima_parte
    
    return None

def ler_links_categorias():
    """Lê os links de categorias do arquivo"""
    arquivo_links = os.path.join(os.path.dirname(__file__), "categorias_sorria.txt")
    links = []
    
    if os.path.exists(arquivo_links):
        with open(arquivo_links, "r", encoding="utf-8") as f:
            links = [linha.strip() for linha in f if linha.strip()]
    
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
        
        if path.endswith('.html'):
            path = path[:-5]
        
        categoria_map = {
            'biosseguranca': 'Biossegurança',
            'brocas': 'Brocas',
            'cimentos': 'Cimentos',
            'cirurgia-e-periodontia': 'Cirurgia e Periodontia',
            'dentistica-e-estetica': 'Dentística e Estética',
            'descartaveis': 'Descartáveis',
            'endodontia': 'Endodontia',
            'equipamentos-e-perifericos': 'Equipamentos e Periféricos',
            'harmonizacao': 'Harmonização',
            'instrumentais': 'Instrumentais',
            'moldagem': 'Moldagem',
            'ortodontia': 'Ortodontia',
            'teste': 'Teste'
        }
        
        return categoria_map.get(path.lower(), path.replace('-', ' ').title())
    except:
        return "Categoria Desconhecida"

def main():
    """Função principal - Atualização DIÁRIA ULTRA RÁPIDA com requests"""
    print("[RAPIDO] ATUALIZAÇÃO DIÁRIA ULTRA RÁPIDA - DENTAL SORRIA")
    print("=" * 60)
    print("[INICIO] REQUESTS PURO - SEM PLAYWRIGHT")
    print("[ALVO] Atualizando apenas:")
    print("   [OK] Preços atuais")
    print("   [OK] Descontos") 
    print("   [OK] Disponibilidade")
    print("   [OK] URLs atualizadas")
    print("=" * 60)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Nenhuma categoria encontrada!")
        return
    
    todos_produtos_atualizados = []
    site_nome = "Dental Sorria"
    
    inicio_tempo = time.time()
    
    # Processar cada categoria
    for i, url_categoria in enumerate(links_categorias, 1):
        try:
            categoria_nome = extrair_categoria_do_url(url_categoria)
            
            print(f"\n📂 [{i}/{len(links_categorias)}] {categoria_nome}")
            
            produtos_categoria = atualizar_precos_categoria_requests(url_categoria, categoria_nome)
            
            if produtos_categoria:
                todos_produtos_atualizados.extend(produtos_categoria)
            
            # Pausa mínima entre categorias
            time.sleep(0.5)
                
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
            print(f"\n[STATS] ESTATÍSTICAS:")
            print(f"   [TEMPO]  Tempo total: {tempo_total:.1f}s")
            print(f"   [INICIO] Velocidade: {len(todos_produtos_atualizados)/tempo_total:.1f} produtos/segundo")
            print(f"   📂 Categorias: {len(links_categorias)}")
            print(f"   [DICA] Estimativa Playwright: ~{tempo_total*10:.1f}s")
            
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar banco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERRO] Nenhum produto coletado para atualização.")
    
    print("\n[RAPIDO] ATUALIZAÇÃO DIÁRIA ULTRA RÁPIDA CONCLUÍDA!")

if __name__ == "__main__":
    main()
