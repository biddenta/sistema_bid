import sys, os, time, requests, re, json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Desabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

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
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

def fazer_requisicao(url, timeout=30):
    """Faz requisição HTTP com configurações otimizadas"""
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
    
    # Procurar botão "Próximo" - diferentes variações possíveis
    botao_proximo = soup.find("li", class_="pages-item-next") or \
                   soup.find("li", class_=lambda x: x and 'next' in str(x).lower() if x else False) or \
                   soup.find("a", class_=lambda x: x and 'next' in str(x).lower() if x else False) or \
                   soup.find("a", title="Próximo") or \
                   soup.find("a", string=re.compile(r'próximo|next', re.IGNORECASE))
    
    if botao_proximo:
        # Se é um li, procurar o link dentro dele
        if botao_proximo.name == 'li':
            link_proximo = botao_proximo.find("a")
        else:
            link_proximo = botao_proximo
        
        if link_proximo and link_proximo.get('href'):
            return link_proximo.get('href')
    
    return None

def extrair_produtos_pagina_requests(html, categoria_base, url_base):
    """Extrai produtos de uma página HTML usando apenas requests/BeautifulSoup"""
    produtos = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Buscar lista de produtos
    product_list = soup.find('ol', class_='products') or \
                  soup.find('ol', class_=lambda x: x and 'product' in str(x).lower() if x else False)
    
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
            
            # Imagem principal
            img_elem = elemento.find("img", class_="product-image-photo")
            if img_elem:
                src = img_elem.get('src', '')
                if src.startswith('/'):
                    src = urljoin(url_base, src)
                produto['imagem_principal'] = src
            else:
                produto['imagem_principal'] = None
            
            # SKU/ID
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
            
            # Categoria
            produto['categoria_principal'] = categoria_base
            produto['subcategoria'] = None
            produto['categorias_completas'] = categoria_base
            
            # Descrição do produto - tentar extrair do card
            descricao_container = elemento.find("div", class_="product attribute overview")
            if descricao_container:
                descricao_elem = descricao_container.find("div", class_="value", attrs={"itemprop": "description"})
                produto['descricao'] = descricao_elem.get_text(strip=True) if descricao_elem else produto['nome']
            else:
                produto['descricao'] = produto['nome']
            
            # Descrição e detalhes
            produto['imagens_extras'] = None
            
            # Detalhes para o banco
            detalhes_produto = {
                'marca': produto['marca'],
                'categoria': produto['categoria_principal'],
                'subcategoria': produto.get('subcategoria'),
                'especificacoes': None,
                'imagens_extras': produto.get('imagens_extras')
            }
            produto['detalhes_produto'] = json.dumps(detalhes_produto, ensure_ascii=False)
            
            produtos.append(produto)
            
        except Exception as e:
            print(f"[AVISO]  Erro ao extrair produto {i+1}: {e}")
            continue
    
    return produtos

def extrair_categoria_requests(url_categoria, categoria_base):
    """Extrai TODOS os produtos de uma categoria usando apenas requests"""
    produtos_categoria = []
    
    print(f"\n🗂️  === CATEGORIA: {categoria_base} ===")
    print(f"[LINK] URL: {url_categoria}")
    
    url_atual = url_categoria
    pagina_numero = 1
    inicio_tempo = time.time()
    
    while url_atual:
        try:
            print(f"📄 Processando página {pagina_numero}...")
            
            # Fazer requisição HTTP
            html_content = fazer_requisicao(url_atual)
            
            if not html_content:
                print(f"[ERRO] Falha ao carregar página {pagina_numero}")
                break
            
            # Extrair produtos da página atual
            produtos_pagina = extrair_produtos_pagina_requests(html_content, categoria_base, url_categoria)
            
            if produtos_pagina:
                produtos_categoria.extend(produtos_pagina)
                print(f"[OK] Página {pagina_numero}: {len(produtos_pagina)} produtos extraídos")
                
                # Mostrar alguns produtos da página
                for j, p in enumerate(produtos_pagina[:2], 1):
                    print(f"   {j}. {p['nome'][:45]}... - R$ {p['preco']:.2f} - {p['marca']}")
            else:
                print(f"[AVISO]  Página {pagina_numero}: Nenhum produto encontrado")
                break
            
            # Procurar próxima página
            url_proxima = obter_url_proxima_pagina(html_content)
            
            if url_proxima:
                url_atual = url_proxima
                pagina_numero += 1
                print(f"   [NEXT]  Próxima página encontrada")
                
                # Pausa menor entre páginas (requests é mais rápido)
                time.sleep(0.5)
            else:
                print(f"   🏁 Última página alcançada!")
                break
                
        except Exception as e:
            print(f"[ERRO] Erro na página {pagina_numero}: {e}")
            break
    
    tempo_categoria = time.time() - inicio_tempo
    print(f"[ALVO] Total extraído da categoria {categoria_base}: {len(produtos_categoria)} produtos em {pagina_numero} páginas")
    print(f"[TEMPO]  Tempo: {tempo_categoria:.1f}s | Velocidade: {len(produtos_categoria)/tempo_categoria:.1f} produtos/segundo")
    
    return produtos_categoria

def ler_links_categorias():
    """Lê os links de categorias do arquivo"""
    arquivo_links = os.path.join(os.path.dirname(__file__), "categorias_sorria.txt")
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

def extrair_categoria_do_url(url):
    """Extrai o nome da categoria do URL"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        
        if '?' in path:
            path = path.split('?')[0]
        
        # Remover .html
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

def testar_requests_puro():
    """Testa extração usando apenas requests (muito mais rápido)"""
    
    print("[INICIO] TESTE SCRAPING COM REQUESTS PURO")
    print("=" * 60)
    print("[RAPIDO] Vantagens:")
    print("   [OK] 10x mais rápido que Playwright")
    print("   [OK] Menor uso de memória")
    print("   [OK] Mais estável")
    print("   [OK] Não precisa de navegador")
    print("=" * 60)
    
    # Testar apenas uma categoria primeiro
    url_teste = 'https://www.dentalsorria.com.br/biosseguranca.html'
    categoria_nome = 'Biossegurança'
    site_nome = "Dental Sorria"
    
    inicio_tempo_total = time.time()
    
    # Extrair categoria
    produtos = extrair_categoria_requests(url_teste, categoria_nome)
    
    tempo_total = time.time() - inicio_tempo_total
    
    if produtos:
        print(f"\n[SALVANDO] SALVANDO {len(produtos)} PRODUTOS NO BANCO")
        print("=" * 50)
        
        try:
            salvar_produtos_db(produtos, "Dental Sorria", site_nome)
            print("[OK] Produtos salvos com sucesso!")
            
            # Estatísticas
            consulta_db_estatisticas(site_nome)
            
        except Exception as e:
            print(f"[ERRO] Erro ao salvar no banco: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[STATS] RESUMO FINAL:")
    print(f"   [TEMPO]  Tempo total: {tempo_total:.1f}s")
    print(f"   [PACOTE] Produtos coletados: {len(produtos)}")
    print(f"   [INICIO] Velocidade média: {len(produtos)/tempo_total:.1f} produtos/segundo")
    print(f"   [DICA] Comparação: Playwright seria ~{tempo_total*10:.1f}s para a mesma tarefa")
    
    print("\n[SUCESSO] TESTE REQUESTS PURO CONCLUÍDO!")

def main_requests_completo():
    """Versão completa usando apenas requests para todas as categorias"""
    
    print("[INICIO] SCRAPING COMPLETO - DENTAL SORRIA (REQUESTS PURO)")
    print("=" * 70)
    print("[RAPIDO] ULTRA RÁPIDO - SEM PLAYWRIGHT")
    print("[INFO] Coletando dados básicos para comparador de preços:")
    print("   [OK] Nome, preço, marca, disponibilidade")
    print("   [OK] URLs dos produtos") 
    print("   [OK] Imagens principais")
    print("   [OK] Categorias")
    print("=" * 70)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Nenhuma categoria encontrada!")
        return
    
    todos_produtos = []
    site_nome = "Dental Sorria"
    inicio_tempo_total = time.time()
    
    # Processar cada categoria
    for i, url_categoria in enumerate(links_categorias, 1):
        try:
            categoria_base = extrair_categoria_do_url(url_categoria)
            
            print(f"\n{'='*80}")
            print(f"📂 PROCESSANDO {i}/{len(links_categorias)}: {categoria_base}")
            print(f"{'='*80}")
            
            produtos_categoria = extrair_categoria_requests(url_categoria, categoria_base)
            
            if produtos_categoria:
                todos_produtos.extend(produtos_categoria)
                print(f"[OK] {len(produtos_categoria)} produtos coletados de {categoria_base}")
            else:
                print(f"[AVISO]  Nenhum produto encontrado em {categoria_base}")
            
            # Pausa entre categorias
            print("⏳ Pausando 2 segundos...")
            time.sleep(2)
                
        except Exception as e:
            print(f"[ERRO] Erro ao processar categoria {url_categoria}: {e}")
            continue
    
    tempo_total = time.time() - inicio_tempo_total
    
    # Salvar no banco de dados
    if todos_produtos:
        print(f"\n[SALVANDO] SALVANDO {len(todos_produtos)} PRODUTOS NO BANCO")
        print("=" * 50)
        
        try:
            salvar_produtos_db(todos_produtos, "Dental Sorria", site_nome)
            print("[OK] Produtos salvos com sucesso!")
            
            # Estatísticas
            consulta_db_estatisticas(site_nome)
            
        except Exception as e:
            print(f"[ERRO] Erro ao salvar no banco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERRO] Nenhum produto foi coletado.")
    
    print(f"\n[STATS] ESTATÍSTICAS FINAIS:")
    print(f"   [TEMPO]  Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} minutos)")
    print(f"   [PACOTE] Produtos coletados: {len(todos_produtos)}")
    print(f"   📂 Categorias processadas: {len(links_categorias)}")
    print(f"   [INICIO] Velocidade média: {len(todos_produtos)/tempo_total:.1f} produtos/segundo")
    print(f"   [DICA] Estimativa Playwright: ~{tempo_total*10/60:.1f} minutos")
    
    print("\n[SUCESSO] COLETA COMPLETA FINALIZADA!")

if __name__ == "__main__":
    # Escolher qual executar:
    # testar_requests_puro()        # Teste com uma categoria
    main_requests_completo()       # Todas as categorias
