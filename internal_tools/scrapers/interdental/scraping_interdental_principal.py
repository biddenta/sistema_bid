import sys, os, time, requests, re, json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import threading

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))
from utils.marca_utils_final import extrair_marca_universal

def ler_links_categorias():
    """Lê os links de categorias do arquivo"""
    arquivo_links = os.path.join(os.path.dirname(__file__), "categorias_interdental.txt")
    links = []
    
    if os.path.exists(arquivo_links):
        with open(arquivo_links, "r", encoding="utf-8") as f:
            links = [linha.strip() for linha in f if linha.strip()]
    
    print(f"📂 {len(links)} categorias encontradas.")
    return links

def extrair_categoria_do_url(url):
    """Extrai o nome da categoria do URL"""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        categoria = path.replace('-', ' ').title()
        return categoria
    except:
        return "Categoria Desconhecida"

class ScrapingThreadPool:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.produtos_processados = []
        self.lock = threading.Lock()
        self.categorias_com_erro = []
        self.categorias_sem_produtos = []

    def extrair_produtos_pagina(self, html, categoria_base, url_base):
        """Extrai produtos de uma página usando BeautifulSoup"""
        produtos = []
        
        try:
            soup = BeautifulSoup(html, "lxml")
            produtos_elementos = soup.select('.card.card-compact.group')
            
            if not produtos_elementos:
                print(f"   [AVISO] Nenhum produto encontrado em {categoria_base}")
                return []
            
            print(f"   [INFO] Encontrados {len(produtos_elementos)} produtos")
            
            for i, elemento in enumerate(produtos_elementos):
                try:
                    produto = {}
                    
                    # Nome do produto - priorizar title attribute para nome completo
                    nome_elem = elemento.select_one("h3.text-center")
                    if not nome_elem:
                        continue
                    
                    # Tentar extrair nome completo via title attribute primeiro
                    nome_completo = nome_elem.get('title', '').strip()
                    if nome_completo:
                        produto['nome'] = nome_completo
                        print(f"   [INFO] Nome completo (title): {nome_completo[:50]}...")
                    else:
                        # Fallback para text content se não tiver title
                        produto['nome'] = nome_elem.get_text(strip=True)
                        print(f"   [NOTA] Nome (text): {produto['nome'][:50]}...")
                    
                    # URL do produto
                    link_elem = elemento.select_one("a[href*='/p?skuId=']")
                    if link_elem:
                        href = link_elem.get('href', '')
                        produto['url'] = urljoin(url_base, href) if href else ""
                    else:
                        produto['url'] = ""
                    
                    # Preço
                    preco_elem = elemento.select_one(".text-base.xl\\:text-xl.font-bold.text-\\[\\#27239E\\]")
                    if preco_elem:
                        preco_texto = preco_elem.get_text(strip=True)
                        preco_match = re.search(r'R\$\s*([\d.,]+)', preco_texto)
                        if preco_match:
                            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                            try:
                                produto['preco'] = float(preco_str)
                            except:
                                produto['preco'] = 0
                        else:
                            produto['preco'] = 0
                    else:
                        produto['preco'] = 0
                    
                    # SKU
                    sku_match = re.search(r'skuId=(\d+)', produto['url'])
                    produto['sku'] = sku_match.group(1) if sku_match else f"INT_{i}_{int(time.time())}"
                    
                    # Extrair marca usando função universal
                    marca_extraida, nome_sem_marca = extrair_marca_universal(produto['nome'])
                    
                    if marca_extraida:
                        # [OK] Marca extraída via função universal
                        produto['marca'] = marca_extraida
                        nome_limpo = nome_sem_marca
                        print(f"   [OK] Marca extraída (universal): {marca_extraida}")
                    else:
                        # [ERRO] Marca não identificada
                        produto['marca'] = "Marca não identificada"
                        nome_limpo = produto['nome']
                        print(f"   [ERRO] Marca não identificada: {produto['nome'][:50]}...")
                    
                    # Nome limpo e chave de matching
                    produto['nome_limpo'] = nome_limpo
                    
                    # Gerar chave de matching
                    if produto['marca'] and produto['marca'] != "Marca não identificada":
                        chave_matching = f"{nome_limpo.upper().strip()}_{produto['marca'].upper().strip()}"
                    else:
                        chave_matching = produto['nome'].upper().strip()
                    produto['chave_matching'] = chave_matching
                    
                    # Imagem
                    img_elem = elemento.select_one('figure img')
                    if img_elem:
                        src = img_elem.get('src')
                        if src and 'vtexassets.com' in src:
                            produto['imagem_principal'] = src.split('?')[0] if '?' in src else src
                        else:
                            produto['imagem_principal'] = None
                    else:
                        produto['imagem_principal'] = None
                    
                    # Campos obrigatórios
                    produto['preco_antigo'] = None  # Sempre null conforme solicitado
                    produto['porcentagem_desconto'] = 0
                    produto['disponivel'] = produto['preco'] > 0
                    produto['status'] = "Disponível" if produto['preco'] > 0 else "Indisponível"
                    produto['categoria_principal'] = categoria_base
                    produto['subcategoria'] = None
                    produto['categorias_completas'] = categoria_base
                    produto['site'] = "Loja Interdental"
                    produto['descricao'] = ""
                    produto['detalhes_produto'] = ""
                    produto['imagens_extras'] = None
                    produto['historico_precos'] = None
                    produto['historico_disponibilidade'] = None
                    produto['historico_descontos'] = None
                    produto['data_primeira_coleta'] = datetime.now().isoformat()
                    produto['data_ultima_atualizacao'] = datetime.now().isoformat()
                    
                    produtos.append(produto)
                    
                except Exception as e:
                    print(f"   [ERRO] Erro ao processar produto {i+1}: {e}")
                    continue
            
            print(f"   [OK] {len(produtos)} produtos extraídos com sucesso")
            return produtos
            
        except Exception as e:
            print(f"   [ERRO] Erro ao processar página: {e}")
            return []

    def extrair_detalhes_produto(self, url):
        """Extrai detalhes de um produto específico"""
        try:
            response = self.session.get(url, timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Descrição
                descricao = ""
                desc_elem = soup.select_one('#description span.text-base.font-medium')
                if desc_elem:
                    descricao = desc_elem.get_text(strip=True)[:800]
                
                # Especificações
                especificacoes = ""
                spec_section = soup.select_one('section[data-manifest-key*="ProductSpecifications"]')
                if spec_section:
                    specs = []
                    for spec in spec_section.select('.mb-4 .flex'):
                        strong = spec.select_one('strong')
                        if strong:
                            key = strong.get_text(strip=True)
                            value = spec.get_text(strip=True).replace(key, '', 1).strip()
                            if key and value and len(specs) < 8:
                                specs.append(f"{key}: {value}")
                    especificacoes = " | ".join(specs)
                
                return {'url': url, 'descricao': descricao, 'especificacoes': especificacoes}
            
        except Exception as e:
            pass
        
        return {'url': url, 'descricao': '', 'especificacoes': ''}

    def processar_categoria(self, url_categoria, categoria_base):
        """Processa uma categoria completa usando ThreadPool"""
        produtos_categoria = []
        
        print(f"\n📂 {categoria_base}")
        print("=" * 50)
        
        try:
            # Testar acesso à categoria
            response = self.session.get(url_categoria, timeout=12)
            if response.status_code != 200:
                erro = f"Erro HTTP: {response.status_code}"
                print(f"[ERRO] {erro}")
                self.categorias_com_erro.append({
                    'categoria': categoria_base,
                    'url': url_categoria,
                    'erro': erro
                })
                return []
            
            # Verificar se a página é válida
            if len(response.text) < 500:
                erro = f"Página muito pequena ({len(response.text)} bytes)"
                print(f"[ERRO] {erro}")
                self.categorias_com_erro.append({
                    'categoria': categoria_base,
                    'url': url_categoria,
                    'erro': erro
                })
                return []
            
            # Extrair produtos da primeira página
            produtos_pagina_1 = self.extrair_produtos_pagina(response.text, categoria_base, url_categoria)
            
            if not produtos_pagina_1:
                erro = "Nenhum produto encontrado"
                print(f"[AVISO] {erro}")
                self.categorias_sem_produtos.append({
                    'categoria': categoria_base,
                    'url': url_categoria,
                    'motivo': erro
                })
                return []
            
            produtos_categoria.extend(produtos_pagina_1)
            print(f"📄 Página 1: {len(produtos_pagina_1)} produtos")
            
            # Processar páginas adicionais com ThreadPool
            def processar_pagina(pagina_num):
                try:
                    url_pagina = f"{url_categoria}?page={pagina_num}"
                    response = self.session.get(url_pagina, timeout=10)
                    if response.status_code == 200:
                        produtos = self.extrair_produtos_pagina(response.text, categoria_base, url_categoria)
                        if produtos:
                            print(f"📄 Página {pagina_num}: {len(produtos)} produtos")
                            return produtos
                except Exception as e:
                    print(f"[ERRO] Erro página {pagina_num}: {e}")
                return []
            
            # Processar até 15 páginas em paralelo
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for pagina in range(2, 16):  # Páginas 2-15
                    future = executor.submit(processar_pagina, pagina)
                    futures.append(future)
                
                for future in futures:
                    try:
                        produtos_pagina = future.result(timeout=15)
                        if produtos_pagina:
                            produtos_categoria.extend(produtos_pagina)
                        else:
                            break  # Para quando não há mais produtos
                    except Exception as e:
                        continue
            
            # Extrair detalhes usando ThreadPool
            if produtos_categoria:
                urls_com_preco = [p['url'] for p in produtos_categoria if p['url'] and p['preco'] > 0]
                
                if urls_com_preco:
                    print(f"[INFO] Extraindo detalhes de {len(urls_com_preco)} produtos...")
                    
                    # Processar detalhes em lotes
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = {executor.submit(self.extrair_detalhes_produto, url): url for url in urls_com_preco}
                        
                        detalhes_coletados = 0
                        for future in futures:
                            try:
                                detalhes = future.result(timeout=12)
                                # Aplicar detalhes ao produto correspondente
                                for produto in produtos_categoria:
                                    if produto['url'] == detalhes['url']:
                                        produto['descricao'] = detalhes['descricao']
                                        produto['detalhes_produto'] = detalhes['especificacoes']
                                        detalhes_coletados += 1
                                        break
                            except Exception as e:
                                continue
                        
                        print(f"   [OK] {detalhes_coletados} detalhes extraídos")
            
        except Exception as e:
            erro = f"Erro geral: {str(e)}"
            print(f"[ERRO] {erro}")
            self.categorias_com_erro.append({
                'categoria': categoria_base,
                'url': url_categoria,
                'erro': erro
            })
            return []
        
        print(f"[OK] Total coletado: {len(produtos_categoria)} produtos")
        return produtos_categoria

    def relatorio_final(self):
        """Gera relatório final de erros e problemas"""
        if self.categorias_com_erro or self.categorias_sem_produtos:
            print("\n" + "="*60)
            print("[STATS] RELATÓRIO DE PROBLEMAS")
            print("="*60)
            
            if self.categorias_com_erro:
                print(f"\n[ERRO] CATEGORIAS COM ERRO ({len(self.categorias_com_erro)}):")
                for i, erro in enumerate(self.categorias_com_erro, 1):
                    print(f"   {i}. {erro['categoria']}")
                    print(f"      URL: {erro['url']}")
                    print(f"      Erro: {erro['erro']}")
                    print()
            
            if self.categorias_sem_produtos:
                print(f"\n[AVISO] CATEGORIAS SEM PRODUTOS ({len(self.categorias_sem_produtos)}):")
                for i, sem_prod in enumerate(self.categorias_sem_produtos, 1):
                    print(f"   {i}. {sem_prod['categoria']}")
                    print(f"      URL: {sem_prod['url']}")
                    print(f"      Motivo: {sem_prod['motivo']}")
                    print()
        else:
            print("\n[OK] Todas as categorias processadas com sucesso!")

def main():
    """Função principal usando ThreadPool"""
    print("[INICIO] SCRAPING INTERDENTAL - THREADPOOL")
    print("=" * 50)
    print("[RAPIDO] CARACTERÍSTICAS:")
    print("   [IMPORTANTE] ThreadPoolExecutor para páginas e detalhes")
    print("   [PACOTE] Processamento em lotes otimizado")
    print("   [ALVO] Detecção automática de problemas")
    print("   [SALVANDO] Salvamento direto no banco")
    print("=" * 50)
    
    # Ler categorias
    links_categorias = ler_links_categorias()
    
    if not links_categorias:
        print("[ERRO] Arquivo de categorias não encontrado!")
        return
    
    # Inicializar scraper
    scraper = ScrapingThreadPool()
    todos_produtos = []
    
    inicio_total = time.time()
    
    # Processar categorias
    for i, url_categoria in enumerate(links_categorias, 1):
        try:
            categoria_base = extrair_categoria_do_url(url_categoria)
            
            print(f"\n{'='*70}")
            print(f"📂 CATEGORIA {i}/{len(links_categorias)}: {categoria_base}")
            print(f"{'='*70}")
            
            inicio_categoria = time.time()
            produtos = scraper.processar_categoria(url_categoria, categoria_base)
            tempo_categoria = time.time() - inicio_categoria
            
            if produtos:
                todos_produtos.extend(produtos)
                print(f"[RAPIDO] Processado em {tempo_categoria:.1f}s - {len(produtos)} produtos")
            else:
                print(f"[AVISO] Categoria sem produtos coletados")
            
            # Pausa entre categorias
            time.sleep(0.3)
            
        except Exception as e:
            print(f"[ERRO] Erro fatal na categoria {url_categoria}: {e}")
            continue
    
    tempo_total = time.time() - inicio_total
    
    # Relatório de problemas
    scraper.relatorio_final()
    
    # Resultados finais
    if todos_produtos:
        print(f"\n[SUCESSO] SCRAPING THREADPOOL FINALIZADO!")
        print("=" * 50)
        print(f"[RAPIDO] Tempo total: {tempo_total:.1f} segundos ({tempo_total/60:.1f} minutos)")
        print(f"[ALVO] Total de produtos: {len(todos_produtos)}")
        print(f"[CRESCIMENTO] Velocidade: {len(todos_produtos)/tempo_total:.1f} produtos/segundo")
        print(f"[RAPIDO] Estimativa velocidade total: {60*len(todos_produtos)/tempo_total:.0f} produtos/minuto")
        
        # Estatísticas de qualidade
        com_imagem = len([p for p in todos_produtos if p.get('imagem_principal')])
        com_descricao = len([p for p in todos_produtos if p.get('descricao') and len(p['descricao']) > 10])
        com_detalhes = len([p for p in todos_produtos if p.get('detalhes_produto') and len(p['detalhes_produto']) > 10])
        
        print(f"\n[STATS] QUALIDADE DOS DADOS:")
        print(f"   🖼️ Com imagem: {com_imagem}/{len(todos_produtos)} ({com_imagem/len(todos_produtos)*100:.1f}%)")
        print(f"   [NOTA] Com descrição: {com_descricao}/{len(todos_produtos)} ({com_descricao/len(todos_produtos)*100:.1f}%)")
        print(f"   🔧 Com detalhes: {com_detalhes}/{len(todos_produtos)} ({com_detalhes/len(todos_produtos)*100:.1f}%)")
        
        # Resumo por categoria
        categorias = {}
        for produto in todos_produtos:
            cat = produto['categoria_principal']
            categorias[cat] = categorias.get(cat, 0) + 1
        
        print(f"\n📂 RESUMO POR CATEGORIA:")
        for categoria, count in sorted(categorias.items(), key=lambda x: x[1], reverse=True):
            print(f"   📁 {categoria}: {count} produtos")
        
        # Salvar no banco
        print(f"\n[SALVANDO] SALVANDO {len(todos_produtos)} PRODUTOS NO BANCO...")
        try:
            stats = salvar_produtos_db(todos_produtos, "Loja Interdental", "Loja Interdental")
            
            print(f"[OK] DADOS SALVOS COM SUCESSO!")
            print(f"   [PACOTE] Produtos novos: {stats['novos']}")
            print(f"   [PROCESSANDO] Produtos atualizados: {stats['atualizados']}")
            print(f"   ⚪ Sem alteração: {stats['sem_alteracao']}")
            
        except Exception as e:
            print(f"[ERRO] ERRO AO SALVAR: {e}")
            
    else:
        print("\n[ERRO] Nenhum produto foi coletado!")
    
    print(f"\n🏁 CONCLUÍDO EM {tempo_total:.1f} SEGUNDOS!")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == "__main__":
    main()
