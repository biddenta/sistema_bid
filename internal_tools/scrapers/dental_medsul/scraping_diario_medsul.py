import sys, os, time, requests, re, json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

def ler_links_categorias():
    """Lê os links de categorias do arquivo"""
    arquivo_links = os.path.join(os.path.dirname(__file__), "links_categorias_medsul.txt")
    links = []
    
    if os.path.exists(arquivo_links):
        with open(arquivo_links, "r", encoding="utf-8") as f:
            links = [linha.strip() for linha in f if linha.strip()]
    
    print(f"📂 Total de {len(links)} categorias encontradas.")
    return links

def extrair_categoria_do_url(url):
    """Extrai o nome da categoria do URL"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        
        # Remover /c/ se existir
        if path.startswith('c/'):
            path = path[2:]
        
        return path.replace('-', ' ').title()
    except:
        return "Categoria Desconhecida"

def extrair_produtos_pagina_basico(html, categoria_base, url_base):
    """Extrai informações BÁSICAS dos produtos de uma página"""
    produtos = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Buscar produtos na estrutura VTEX
    produtos_elementos = soup.find_all("div", class_=lambda x: x and "product-summary" in " ".join(x))
    
    if not produtos_elementos:
        # Tentar outras estruturas comuns
        produtos_elementos = soup.find_all("div", attrs={"data-testid": "product-summary"}) or \
                           soup.find_all("article") or \
                           soup.find_all("div", class_=lambda x: x and "item" in " ".join(x))
    
    print(f"[INFO] Encontrados {len(produtos_elementos)} produtos na página")
    
    for i, elemento in enumerate(produtos_elementos):
        try:
            produto = {}
            
            # Nome do produto - Verificar title completo vs texto truncado
            nome_elem = elemento.find("h2") or elemento.find("h3") or \
                       elemento.find("a", attrs={"data-testid": "product-summary-name"}) or \
                       elemento.find("span", class_=lambda x: x and "name" in " ".join(x))
            
            if nome_elem:
                # Tentar obter nome completo do atributo title
                nome_completo = nome_elem.get('title', '').strip()
                if nome_completo:
                    produto['nome'] = nome_completo
                else:
                    produto['nome'] = nome_elem.get_text(strip=True)
                
                # URL do produto
                link_elem = nome_elem.find_parent("a") or elemento.find("a")
                if link_elem:
                    href = link_elem.get('href', '')
                    produto['url'] = urljoin(url_base, href) if href else ""
                else:
                    produto['url'] = ""
            else:
                produto['nome'] = f"Produto {i+1}"
                produto['url'] = ""
            
            # Preço atual
            preco_elem = elemento.find("span", class_=lambda x: x and "price" in " ".join(x)) or \
                        elemento.find("div", class_=lambda x: x and "price" in " ".join(x))
            
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
            
            # SKU/ID (extrair da URL)
            sku = None
            if produto['url']:
                url_parts = produto['url'].split('/')
                for part in reversed(url_parts):
                    if part and (part.isdigit() or len(part) > 5):
                        sku = part
                        break
            
            produto['sku'] = sku if sku else f"MEDSUL_{produto['nome'].replace(' ', '-').upper()}"
            
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
            
            # Disponibilidade
            produto['disponivel'] = produto['preco'] > 0
            produto['status'] = "Disponível" if produto['preco'] > 0 else "Indisponível"
            
            # Categoria
            produto['categoria_principal'] = categoria_base
            produto['categoria_base'] = categoria_base
            
            # Descrição do produto - tentar extrair do card
            descricao_elem = elemento.find("span", class_="tfcvgc-custom-0-x-shortDescriptionText")
            produto['descricao'] = descricao_elem.get_text(strip=True) if descricao_elem else ""
            
            # Campos básicos obrigatórios
            produto['porcentagem_desconto'] = 0
            produto['preco_antigo'] = None
            produto['subcategoria'] = None
            produto['categorias_completas'] = categoria_base
            
            # Campos de imagem (vazios no modo diário)
            produto['imagem_principal'] = None
            produto['imagens_extras'] = None
            
            # Campos detalhados (vazios no modo diário)
            produto['descricao_completa'] = None
            produto['especificacoes'] = None
            produto['marca_detalhada'] = None
            
            produtos.append(produto)
            
        except Exception as e:
            print(f"[ERRO] Erro ao extrair produto {i+1}: {e}")
            continue
    
    return produtos

def extrair_categoria_basica(url_categoria, categoria_base, max_paginas=5):
    """Extrai produtos básicos de uma categoria (limitado para execução diária)"""
    produtos_categoria = []
    
    print(f"\n🗂️  === CATEGORIA: {categoria_base} ===")
    print(f"[LINK] URL: {url_categoria}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for pagina in range(1, max_paginas + 1):
        try:
            # Construir URL da página
            if "?" in url_categoria:
                url_pagina = f"{url_categoria}&page={pagina}"
            else:
                url_pagina = f"{url_categoria}?page={pagina}"
            
            print(f"📄 Extraindo página {pagina}/{max_paginas}...")
            
            response = requests.get(url_pagina, headers=headers, timeout=15)
            
            if response.status_code == 200:
                produtos_pagina = extrair_produtos_pagina_basico(response.content, categoria_base, url_categoria)
                
                if produtos_pagina:
                    produtos_categoria.extend(produtos_pagina)
                    print(f"[OK] Página {pagina}: {len(produtos_pagina)} produtos extraídos")
                else:
                    print(f"[AVISO]  Página {pagina}: Nenhum produto encontrado")
                    break
            else:
                print(f"[ERRO] Erro HTTP na página {pagina}: {response.status_code}")
                break
            
            # Pausa entre páginas
            time.sleep(1)
            
        except Exception as e:
            print(f"[ERRO] Erro na página {pagina}: {e}")
            continue
    
    print(f"[ALVO] Total extraído da categoria {categoria_base}: {len(produtos_categoria)} produtos")
    return produtos_categoria

def main():
    """Função principal - Scraping DIÁRIO básico"""
    print("[INICIO] SCRAPING DIARIO - DENTAL MEDSUL")
    print("=" * 60)
    print("[INFO] Modo DIARIO - Informacoes basicas:")
    print("   [OK] Nome, preco, SKU, marca")
    print("   [OK] Categoria e disponibilidade")
    print("   [OK] URLs dos produtos")
    print("   [SKIP] SEM imagens (para velocidade)")
    print("   [SKIP] SEM descricoes detalhadas")
    print("=" * 60)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Nenhuma categoria encontrada!")
        return
    
    todos_produtos = []
    site_nome = "Dental Medsul"
    
    # Processar cada categoria (limitado para execução diária)
    max_categorias = min(len(links_categorias), 10)  # Máximo 10 categorias por dia
    
    for i, url_categoria in enumerate(links_categorias[:max_categorias], 1):
        try:
            categoria_base = extrair_categoria_do_url(url_categoria)
            
            print(f"\n{'='*80}")
            print(f"📂 PROCESSANDO {i}/{max_categorias}: {categoria_base}")
            print(f"{'='*80}")
            
            produtos_categoria = extrair_categoria_basica(url_categoria, categoria_base, max_paginas=3)
            
            if produtos_categoria:
                todos_produtos.extend(produtos_categoria)
                print(f"[OK] {len(produtos_categoria)} produtos coletados de {categoria_base}")
            else:
                print(f"[AVISO]  Nenhum produto encontrado em {categoria_base}")
            
            # Pausa entre categorias
            time.sleep(2)
                
        except Exception as e:
            print(f"[ERRO] Erro ao processar categoria {url_categoria}: {e}")
            continue
    
    # Salvar no banco de dados
    if todos_produtos:
        print(f"\n[SALVANDO] SALVANDO {len(todos_produtos)} PRODUTOS NO BANCO")
        print("=" * 50)
        
        try:
            salvar_produtos_db(todos_produtos, "Dental Medsul", site_nome)
            print("[OK] Produtos salvos com sucesso!")
            
            # Estatísticas
            consulta_db_estatisticas(site_nome)
            
        except Exception as e:
            print(f"[ERRO] Erro ao salvar no banco: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERRO] Nenhum produto foi coletado.")
    
    print(f"\n[SUCESSO] SCRAPING DIÁRIO FINALIZADO!")
    print(f"[TEMPO] Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == "__main__":
    main()
