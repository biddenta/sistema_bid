import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys
import os

# Adicionar o diretório pai ao sys.path para importar db_utils_v2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

class DentalShopScraper:
    def __init__(self):
        self.base_url = "https://www.dentalshop.com.br"
        self.site_nome = "Dental Shop"
        self.browser = None
        self.context = None
        self.page = None
        self.produtos_coletados = []
        self.categorias_processadas = 0
        self.total_produtos = 0

    async def inicializar_browser(self):
        """Inicializa o navegador Playwright"""
        print("[WEB] Inicializando navegador...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        
        # Configurar timeouts mais generosos para evitar problemas
        self.page.set_default_timeout(60000)  # 60 segundos
        self.page.set_default_navigation_timeout(90000)  # 90 segundos para navegação

    async def fechar_browser(self):
        """Fecha o navegador"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    def extrair_sku_da_url(self, url):
        """Extrai SKU da URL do produto"""
        try:
            # Padrão: /produto-nome-1234/p
            match = re.search(r'/([^/]+)-(\d+)/p$', url)
            if match:
                return match.group(2)
            
            # Padrão alternativo: sku no final da URL
            match = re.search(r'-(\d+)/?$', url)
            if match:
                return match.group(1)
            
            # Último recurso: usar hash da URL
            return str(abs(hash(url)))[:8]
        except:
            return str(abs(hash(url)))[:8]

    def extrair_preco(self, preco_text):
        """Extrai valor numérico do preço"""
        if not preco_text:
            return 0.0
        
        # Remove caracteres não numéricos exceto vírgula e ponto
        preco_limpo = re.sub(r'[^\d,.]', '', preco_text)
        
        # Substitui vírgula por ponto para conversão
        preco_limpo = preco_limpo.replace(',', '.')
        
        try:
            return float(preco_limpo)
        except:
            return 0.0

    def calcular_desconto(self, preco_atual, preco_antigo):
        """Calcula porcentagem de desconto"""
        try:
            if preco_antigo and preco_atual and preco_antigo > preco_atual:
                desconto = ((preco_antigo - preco_atual) / preco_antigo) * 100
                return round(desconto, 2)
            return 0.0
        except:
            return 0.0

    def extrair_categorias(self, soup):
        """Extrai categorias do breadcrumb"""
        try:
            breadcrumb = soup.find('div', {'data-testid': 'breadcrumb'})
            if not breadcrumb:
                return "Categoria não identificada", None, "Categoria não identificada"
            
            links = breadcrumb.find_all('a')
            categorias = []
            
            for link in links:
                texto = link.get_text(strip=True)
                if texto and texto.lower() not in ['início', 'home']:
                    categorias.append(texto)
            
            if categorias:
                categoria_principal = categorias[0]
                subcategoria = categorias[1] if len(categorias) > 1 else None
                categorias_completas = " > ".join(categorias)
                return categoria_principal, subcategoria, categorias_completas
            
            return "Categoria não identificada", None, "Categoria não identificada"
        except Exception as e:
            print(f"[AVISO]  Erro ao extrair categorias: {e}")
            return "Categoria não identificada", None, "Categoria não identificada"

    async def extrair_detalhes_produto(self, url_produto):
        """Extrai informações detalhadas da página individual do produto"""
        try:
            await self.page.goto(url_produto, wait_until='networkidle')
            
            # Aguardar carregamento do conteúdo
            await self.page.wait_for_timeout(2000)
            
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            detalhes = {}
            descricao = ""
            
            # Extrair descrição do produto
            descricao_elem = soup.find('span', class_='vtex-product-summary-2-x-description')
            if descricao_elem:
                descricao = descricao_elem.get_text(strip=True)
            
            # Extrair especificações técnicas
            specs_section = soup.find('div', class_='vtex-tab-layout-0-x-contentContainer')
            if specs_section:
                specs_text = specs_section.get_text(separator='\n', strip=True)
                if specs_text:
                    detalhes['especificacoes'] = specs_text
            
            # Extrair informações da embalagem
            embalagem_info = soup.find('div', string=re.compile(r'Embalagem|unidade', re.I))
            if embalagem_info:
                detalhes['embalagem'] = embalagem_info.get_text(strip=True)
            
            return detalhes, descricao
            
        except Exception as e:
            print(f"[AVISO]  Erro ao extrair detalhes do produto {url_produto}: {e}")
            return {}, ""

    def extrair_produto_do_card(self, card, categoria_info):
        """Extrai informações de um card de produto"""
        try:
            # URL do produto - tentar múltiplos seletores
            url_seletores = [
                'a.vtex-product-summary-2-x-clearLink',
                'a[href*="/p/"]',
                'a[class*="clearLink"]',
                'a[class*="productLink"]',
                'h3 a',
                'h2 a',
                'a'
            ]
            
            link = None
            for seletor in url_seletores:
                if seletor == 'a':
                    # Para o seletor genérico, procurar apenas links com href válidos
                    links = card.find_all('a', href=True)
                    for l in links:
                        if '/p/' in l.get('href', '') or 'produto' in l.get('href', ''):
                            link = l
                            break
                else:
                    link = card.find('a', class_=seletor.split('.')[1] if '.' in seletor else None) if '.' in seletor else card.select_one(seletor)
                
                if link and link.get('href'):
                    break
            
            if not link or not link.get('href'):
                return None
            
            url_relativa = link.get('href')
            url_completa = urljoin(self.base_url, url_relativa)
            
            # SKU
            sku = self.extrair_sku_da_url(url_relativa)
            
            # Nome do produto - tentar múltiplos seletores e verificar title
            nome_seletores = [
                'span.vtex-product-summary-2-x-productBrand',
                'h3[class*="productName"]',
                'h2[class*="productName"]',
                'span[class*="productBrand"]',
                'a[class*="productName"] span',
                '.vtex-product-summary-2-x-productName'
            ]
            
            nome = None
            for seletor in nome_seletores:
                if '.' in seletor and not '[' in seletor:
                    nome_elem = card.find(seletor.split('.')[0], class_=seletor.split('.')[1])
                else:
                    nome_elem = card.select_one(seletor)
                
                if nome_elem:
                    # Tentar obter nome completo do atributo title
                    nome_completo = nome_elem.get('title', '').strip()
                    if nome_completo:
                        nome = nome_completo
                    else:
                        nome = nome_elem.get_text(strip=True)
                    
                    if nome and len(nome) > 3:
                        break
            
            if not nome:
                nome = "Nome não identificado"
            
            # Preços - tentar múltiplos seletores
            preco_atual = 0.0
            preco_antigo = 0.0
            
            # Preço atual
            preco_seletores = [
                'span.vtex-product-price-1-x-sellingPriceRangeUniqueValue',
                'span.vtex-product-price-1-x-sellingPriceRangeMinValue',
                'span.vtex-product-price-1-x-sellingPriceValue',
                'span[class*="sellingPrice"]',
                'span[class*="currentPrice"]',
                '.vtex-product-price-1-x-currencyContainer'
            ]
            
            for seletor in preco_seletores:
                if '.' in seletor and not '[' in seletor:
                    preco_elem = card.find(seletor.split('.')[0], class_=seletor.split('.')[1])
                else:
                    preco_elem = card.select_one(seletor)
                
                if preco_elem:
                    preco_text = preco_elem.get_text(strip=True)
                    preco_atual = self.extrair_preco(preco_text)
                    if preco_atual > 0:
                        break
            
            # Preço antigo (se houver desconto)
            preco_list = card.find('span', class_='vtex-product-price-1-x-listPriceValue')
            if preco_list:
                preco_antigo_text = preco_list.get_text(strip=True)
                preco_antigo = self.extrair_preco(preco_antigo_text)
            
            # Calcular desconto
            porcentagem_desconto = self.calcular_desconto(preco_atual, preco_antigo)
            
            # Imagem principal
            img_elem = card.find('img', class_='vtex-product-summary-2-x-imageInline')
            if not img_elem:
                img_elem = card.find('img')
            imagem_url = img_elem.get('src') if img_elem else None
            
            # Descrição curta (do card)
            desc_elem = card.find('span', class_='vtex-product-summary-2-x-description')
            descricao_curta = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Status e disponibilidade (assumindo disponível se está na listagem)
            disponivel = True
            status = "Disponível"
            
            # Extrair marca usando função universal
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
            if marca and marca != "Marca não identificada":
                chave_matching = f"{nome_limpo.upper().strip()}_{marca.upper().strip()}"
            else:
                chave_matching = nome.upper().strip()
            
            produto = {
                'sku': sku,
                'nome': nome,
                'nome_limpo': nome_limpo,
                'marca': marca,
                'chave_matching': chave_matching,
                'preco': preco_atual,
                'preco_antigo': preco_antigo,
                'porcentagem_desconto': porcentagem_desconto,
                'url': url_completa,
                'site': self.site_nome,
                'disponivel': disponivel,
                'status': status,
                'categoria_principal': categoria_info['categoria_principal'],
                'subcategoria': categoria_info['subcategoria'],
                'categorias_completas': categoria_info['categorias_completas'],
                'imagem_principal': imagem_url,
                'imagens_extras': None,
                'descricao': descricao_curta,
                'detalhes_produto': "",
            }
            
            return produto
            
        except Exception as e:
            return None

    async def obter_contagem_produtos(self, url_categoria):
        """Obtém o total de produtos em uma categoria"""
        try:
            await self.page.goto(url_categoria, wait_until='networkidle')
            
            # Aguardar carregamento
            await self.page.wait_for_timeout(3000)
            
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar elemento com contagem total
            count_elem = soup.find('span', class_='vtex-search-result-3-x-showingProductsCount')
            if count_elem:
                texto = count_elem.get_text(strip=True)
                # Formato: "52 de 982"
                match = re.search(r'de (\d+)', texto)
                if match:
                    return int(match.group(1))
            
            return 0
        except Exception as e:
            print(f"[AVISO]  Erro ao obter contagem de produtos: {e}")
            return 0

    async def processar_categoria(self, url_categoria):
        """Processa uma categoria específica com paginação usando botão 'Mostrar mais'"""
        print(f"\n� Processando: {url_categoria.split('/')[-1].replace('-', ' ').title()}")
        
        try:
            # Navegar para a categoria
            for tentativa in range(3):
                try:
                    await self.page.goto(url_categoria, wait_until='domcontentloaded', timeout=90000)
                    break
                except Exception as e:
                    if tentativa == 2:
                        raise
                    await asyncio.sleep(5)
            
            # Aguardar carregamento inicial
            await self.page.wait_for_timeout(5000)
            
            # Extrair informações da categoria
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            categoria_info = self.extrair_categorias(soup)
            categoria_dados = {
                'categoria_principal': categoria_info[0],
                'subcategoria': categoria_info[1],
                'categorias_completas': categoria_info[2]
            }
            
            # Obter total de produtos
            total_produtos = await self.obter_contagem_produtos(url_categoria)
            print(f"   [STATS] {total_produtos} produtos encontrados")
            
            produtos_categoria = []
            tentativas_sem_novos_produtos = 0
            max_tentativas_sem_produtos = 3
            
            while tentativas_sem_novos_produtos < max_tentativas_sem_produtos:
                # Aguardar produtos carregarem
                await self.page.wait_for_timeout(3000)
                
                # Obter HTML atual
                html_atual = await self.page.content()
                soup_atual = BeautifulSoup(html_atual, 'html.parser')
                
                # Buscar produtos com múltiplos seletores
                produtos_cards = []
                seletores_produtos = [
                    'div[class*="vtex-search-result"][class*="galleryItem"]',
                    'div.vtex-search-result-3-x-galleryItem',
                    'div[class*="galleryItem"]',
                    'div[class*="vtex-product-summary"]',
                    '.vtex-product-summary-2-x-container'
                ]
                
                for seletor in seletores_produtos:
                    produtos_cards = soup_atual.select(seletor)
                    if produtos_cards:
                        break
                
                if not produtos_cards:
                    tentativas_sem_novos_produtos += 1
                    continue
                
                # Processar produtos encontrados
                produtos_novos = 0
                skus_existentes = {p['sku'] for p in produtos_categoria}
                
                for card in produtos_cards:
                    produto = self.extrair_produto_do_card(card, categoria_dados)
                    if produto and produto['sku'] not in skus_existentes:
                        produtos_categoria.append(produto)
                        produtos_novos += 1
                
                if produtos_novos > 0:
                    print(f"   [OK] {len(produtos_categoria)} produtos coletados", end='\r')
                    tentativas_sem_novos_produtos = 0
                else:
                    tentativas_sem_novos_produtos += 1
                
                # Tentar clicar no botão "Mostrar mais"
                botao_encontrado = False
                seletores_botao = [
                    'button:has-text("Mostrar mais")',
                    'a:has-text("Mostrar mais")',
                    'button[class*="showMore"]',
                    'a[class*="showMore"]',
                    '.vtex-search-result-3-x-buttonShowMore',
                    'button:has-text("Ver mais")',
                    'a[rel="next"]'
                ]
                
                for seletor_botao in seletores_botao:
                    try:
                        botao = await self.page.query_selector(seletor_botao)
                        if botao:
                            is_visible = await botao.is_visible()
                            if is_visible:
                                await botao.click()
                                await self.page.wait_for_timeout(4000)
                                botao_encontrado = True
                                break
                    except Exception:
                        continue
                
                if not botao_encontrado:
                    break
                
                # Scroll para baixo para garantir que novos produtos sejam carregados
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(2000)
            
            print(f"\n   [ALVO] {len(produtos_categoria)} produtos coletados com sucesso!")
            self.categorias_processadas += 1
            self.total_produtos += len(produtos_categoria)
            
            return produtos_categoria
            
        except Exception as e:
            return []

    def ler_categorias_arquivo(self):
        """Lê as categorias do arquivo categorias_dentalshop.txt"""
        try:
            arquivo_categorias = Path(__file__).parent / "categorias_dentalshop.txt"
            
            if not arquivo_categorias.exists():
                print(f"Arquivo de categorias não encontrado: {arquivo_categorias}")
                return []
            
            with open(arquivo_categorias, 'r', encoding='utf-8') as f:
                categorias = [linha.strip() for linha in f if linha.strip() and not linha.startswith('#')]
            
            return categorias
            
        except Exception as e:
            print(f"Erro ao ler arquivo de categorias: {e}")
            return []

    async def enriquecer_produtos_com_detalhes(self, produtos, max_concurrent=5):
        """Enriquece produtos com informações detalhadas (limitado por performance)"""
        print(f"\n[INFO] Enriquecendo {min(100, len(produtos))} produtos com detalhes...")
        
        # Criar semáforo para limitar requisições simultâneas
        semaforo = asyncio.Semaphore(max_concurrent)
        
        async def processar_produto(produto):
            async with semaforo:
                try:
                    detalhes, descricao_completa = await self.extrair_detalhes_produto(produto['url'])
                    
                    if descricao_completa:
                        produto['descricao'] = descricao_completa
                    
                    if detalhes:
                        produto['detalhes_produto'] = json.dumps(detalhes, ensure_ascii=False)
                    
                    await asyncio.sleep(0.5)  # Pausa entre requisições
                    
                except Exception:
                    pass  # Silenciar erros de enriquecimento
        
        # Processar apenas uma amostra para otimizar performance
        amostra_produtos = produtos[:min(100, len(produtos))]
        
        await asyncio.gather(*[processar_produto(produto) for produto in amostra_produtos])
        
        print(f"[OK] {len(amostra_produtos)} produtos enriquecidos")

    async def executar_scraping(self):
        """Executa o scraping completo de todas as categorias"""
        print("[INICIO] Iniciando scraping completo da Dental Shop")
        print(f"[TEMPO] Início: {datetime.now().strftime('%H:%M:%S')}")
        
        await self.inicializar_browser()
        
        try:
            # Ler categorias do arquivo
            categorias = self.ler_categorias_arquivo()
            
            if not categorias:
                print("Nenhuma categoria encontrada. Abortando.")
                return
            
            print(f"[INFO] {len(categorias)} categorias para processar\n")
            
            # Processar cada categoria
            for i, url_categoria in enumerate(categorias, 1):
                print(f"{'='*60}")
                print(f"[{i}/{len(categorias)}] {url_categoria.split('/')[-1].replace('-', ' ').title()}")
                
                produtos_categoria = await self.processar_categoria(url_categoria)
                self.produtos_coletados.extend(produtos_categoria)
                
                # Salvar no banco de dados a cada categoria
                if produtos_categoria:
                    try:
                        stats = salvar_produtos_db(self.produtos_coletados, "Dental Shop", "Dental Shop")
                        print(f"   [SALVANDO] Salvos no banco: {stats['novos']} novos, {stats['atualizados']} atualizados")
                    except Exception as e:
                        print(f"   [AVISO]  Erro ao salvar: {e}")
                
                # Pausa entre categorias
                if i < len(categorias):
                    print(f"   ⏸️  Pausa de 3 segundos...")
                    await asyncio.sleep(3)
            
            print(f"\n{'='*60}")
            print(f"[SUCESSO] SCRAPING CONCLUÍDO!")
            print(f"[STATS] Estatísticas finais:")
            print(f"   • Categorias processadas: {self.categorias_processadas}")
            print(f"   • Total de produtos: {len(self.produtos_coletados)}")
            print(f"   • Produtos únicos: {len(set(p['sku'] for p in self.produtos_coletados if p.get('sku')))}")
            
            # Enriquecer com detalhes (amostra)
            if self.produtos_coletados:
                await self.enriquecer_produtos_com_detalhes(self.produtos_coletados)
                
                # Estatísticas finais do banco
                consulta_db_estatisticas("Dental Shop")
                
                # Salvar JSON para backup
                arquivo_backup = f"dental_shop_produtos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(arquivo_backup, 'w', encoding='utf-8') as f:
                    json.dump(self.produtos_coletados, f, ensure_ascii=False, indent=2)
                print(f"[SALVANDO] Backup salvo em: {arquivo_backup}")
            
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            
        finally:
            await self.fechar_browser()
            print(f"[TEMPO] Finalizado em: {datetime.now().strftime('%H:%M:%S')}")

async def main():
    scraper = DentalShopScraper()
    await scraper.executar_scraping()

if __name__ == "__main__":
    asyncio.run(main())
