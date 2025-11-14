import asyncio
import time
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

# Configurações e constantes
class Config:
    BASE_URL = "https://www.dentalmedsul.com.br"
    MAX_CLIQUES = 50
    MAX_TENTATIVAS = 3
    TIMEOUT_PADRAO = 15000
    TIMEOUT_CARREGAMENTO = 4000
    TIMEOUT_SCROLL = 1500
    DELAY_ENTRE_CATEGORIAS = 2
    
    # Seletores CSS
    PRODUTO_ITEM = '.vtex-search-result-3-x-galleryItem'
    PRODUTO_NOME = '.vtex-product-summary-2-x-productBrand'
    PRODUTO_NOME_ALT = '.vtex-product-summary-2-x-productNameContainer'
    PRODUTO_LINK = '.vtex-product-summary-2-x-clearLink'
    PRECO_ATUAL = '.vtex-product-price-1-x-sellingPriceValue'
    PRECO_ANTIGO = '.vtex-product-price-1-x-listPriceValue'
    DESCONTO_CONTAINER = '.vtex-store-components-3-x-discountInsideContainer'
    
    # Seletores para botão "Carregar mais"
    SELETORES_CARREGAR_MAIS = [
        'button[data-testid="show-more-button"]',
        'button:has-text("Carregar mais")',
        'button:has-text("Ver mais")', 
        'button:has-text("Mostrar mais")',
        'button:has-text("Exibir mais")',
        'button:has-text("More")',
        '.vtex-search-result-3-x-buttonShowMore',
        '.vtex-search-result-3-x-showMoreButton',
        '[data-testid="show-more"]',
        '.show-more-button',
        '.load-more',
        'button[aria-label*="mais"]',
        'button[title*="mais"]'
    ]
    
    # Configurações do browser
    BROWSER_ARGS = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--disable-background-timer-throttling'
    ]


class DentalMedsulScraperRobusto:
    def __init__(self):
        self.base_url = Config.BASE_URL
        self.todos_produtos = []
        self.estatisticas = {
            'categorias_processadas': 0,
            'produtos_extraidos': 0,
            'tempo_total': 0,
            'erros': 0,
            'reconexoes': 0
        }
        self.stats_db_global = {
            "novos": 0, 
            "atualizados": 0, 
            "sem_alteracao": 0, 
            "mudanca_disponibilidade": 0, 
            "novos_descontos": 0, 
            "perdeu_desconto": 0
        }
        self.playwright = None
        self.browser = None
        self.context = None
        
    async def inicializar_browser(self) -> bool:
        """Inicializa o browser com configurações robustas"""
        try:
            if self.playwright:
                await self.fechar_browser()
                
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=Config.BROWSER_ARGS
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Bloquear recursos desnecessários para melhor performance
            await self.context.route(
                "**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", 
                lambda route: route.abort()
            )
            
            return True
            
        except Exception as e:
            print(f"[ERRO] Erro ao inicializar browser: {e}")
            return False
    
    async def fechar_browser(self) -> None:
        """Fecha o browser de forma segura"""
        componentes = [
            ('context', self.context),
            ('browser', self.browser), 
            ('playwright', self.playwright)
        ]
        
        for nome, componente in componentes:
            if componente:
                try:
                    await componente.close() if nome != 'playwright' else await componente.stop()
                except Exception as e:
                    print(f"[AVISO] Erro ao fechar {nome}: {e}")
        
        self.context = None
        self.browser = None
        self.playwright = None
    
    async def aguardar_produtos(self, page) -> int:
        """Aguarda produtos aparecerem e retorna a quantidade"""
        try:
            await page.wait_for_selector(Config.PRODUTO_ITEM, timeout=Config.TIMEOUT_PADRAO)
            return await page.locator(Config.PRODUTO_ITEM).count()
        except Exception:
            return 0
    
    async def tentar_scroll_carregamento(self, page) -> int:
        """Tenta carregar produtos via scroll"""
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(2000)
        return await page.locator(Config.PRODUTO_ITEM).count()
    
    async def tentar_clique_botao(self, page) -> Tuple[bool, int]:
        """Tenta clicar em botão 'Carregar mais' usando múltiplos seletores"""
        for i, seletor in enumerate(Config.SELETORES_CARREGAR_MAIS):
            try:
                if await page.locator(seletor).count() > 0:
                    botao = page.locator(seletor).first
                    if await botao.is_visible():
                        print(f"   � Usando seletor {i+1}: {seletor}")
                        await botao.scroll_into_view_if_needed()
                        await page.wait_for_timeout(Config.TIMEOUT_SCROLL)
                        await botao.click()
                        await page.wait_for_timeout(Config.TIMEOUT_CARREGAMENTO)
                        return True, 1
            except Exception as e:
                print(f"   [AVISO] Erro no seletor {seletor}: {e}")
                continue
        return False, 0
    
    async def tentar_clique_generico(self, page) -> Tuple[bool, int]:
        """Tenta clicar em botão genérico com texto relacionado"""
        try:
            botao_generico = page.locator('button').filter(
                has_text=re.compile(r'(mais|more|ver|mostrar|carregar)', re.IGNORECASE)
            )
            if await botao_generico.count() > 0:
                await botao_generico.first.click()
                await page.wait_for_timeout(Config.TIMEOUT_CARREGAMENTO)
                return True, 1
        except Exception:
            pass
        return False, 0
    
    async def carregar_mais_produtos_simples(self, page, categoria_nome: str, max_cliques: int = None) -> int:
        """Versão otimizada do carregamento com separação de responsabilidades"""
        max_cliques = max_cliques or Config.MAX_CLIQUES
        print(f"[PROCESSANDO] Carregando produtos de {categoria_nome}")
        
        produtos_carregados = 0
        cliques_realizados = 0
        tentativas_sem_progresso = 0
        
        for tentativa in range(max_cliques):
            try:
                # Aguardar e contar produtos atuais
                produtos_atuais = await self.aguardar_produtos(page)
                
                if produtos_atuais > produtos_carregados:
                    produtos_carregados = produtos_atuais
                    tentativas_sem_progresso = 0
                    print(f"   � {produtos_carregados} produtos carregados")
                else:
                    tentativas_sem_progresso += 1
                
                # Parar se não há progresso
                if tentativas_sem_progresso >= 5:
                    print(f"   🏁 Fim detectado - {produtos_carregados} produtos finais")
                    break
                
                # Tentar scroll primeiro
                produtos_apos_scroll = await self.tentar_scroll_carregamento(page)
                if produtos_apos_scroll > produtos_carregados:
                    produtos_carregados = produtos_apos_scroll
                    print(f"   📜 Scroll carregou mais produtos: {produtos_carregados}")
                    continue
                
                # Tentar clique no botão
                botao_clicado, cliques = await self.tentar_clique_botao(page)
                if botao_clicado:
                    cliques_realizados += cliques
                    print(f"   [OK] Clique {cliques_realizados} realizado com sucesso")
                    continue
                
                # Tentar clique genérico
                botao_generico_clicado, cliques = await self.tentar_clique_generico(page)
                if botao_generico_clicado:
                    cliques_realizados += cliques
                    print(f"   [OK] Clique genérico {cliques_realizados} realizado")
                    continue
                
                # Se nenhum método funcionou, fazer scroll múltiplo
                for scroll in range(3):
                    await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight + {scroll * 500})')
                    await page.wait_for_timeout(Config.TIMEOUT_SCROLL)
                
                novos_produtos = await page.locator(Config.PRODUTO_ITEM).count()
                if novos_produtos == produtos_carregados:
                    print(f"   🔚 Não há mais produtos - {produtos_carregados} produtos finais")
                    break
                
            except Exception as e:
                print(f"   [AVISO] Erro na tentativa {tentativa + 1}: {e}")
                await page.wait_for_timeout(3000)
        
        return produtos_carregados
    
    def extrair_nome_produto(self, produto_elem, index: int) -> str:
        """Extrai nome do produto com fallbacks e verificação de title"""
        nome_elem = produto_elem.select_one(Config.PRODUTO_NOME)
        if not nome_elem:
            nome_elem = produto_elem.select_one(Config.PRODUTO_NOME_ALT)
        
        if nome_elem:
            # Tentar obter nome completo do atributo title
            nome_completo = nome_elem.get('title', '').strip()
            if nome_completo:
                return nome_completo
            else:
                return nome_elem.get_text(strip=True)
        
        return f"Produto {index+1}"
    
    def extrair_marca_produto(self, nome_produto: str) -> tuple:
        """Extrai marca do produto usando função universal"""
        marca_extraida, nome_sem_marca = extrair_marca_universal(nome_produto)
        
        if marca_extraida:
            print(f"   [OK] Marca extraída (universal): {marca_extraida}")
            return marca_extraida, nome_sem_marca
        else:
            print(f"   [ERRO] Marca não identificada: {nome_produto[:50]}...")
            return "Marca não identificada", nome_produto
    
    def extrair_url_produto(self, produto_elem) -> Optional[str]:
        """Extrai URL do produto"""
        link_elem = produto_elem.select_one(Config.PRODUTO_LINK)
        if link_elem and link_elem.get('href'):
            url = link_elem['href']
            return url if url.startswith('http') else self.base_url + url
        return None
    
    def extrair_preco_texto(self, produto_elem) -> str:
        """Extrai texto do preço usando múltiplos seletores"""
        seletores_preco = [
            Config.PRECO_ATUAL,
            '.vtex-product-price-1-x-currencyInteger',
            '.priceDiscountContent'
        ]
        
        for seletor in seletores_preco:
            preco_elem = produto_elem.select_one(seletor)
            if preco_elem:
                return preco_elem.get_text(strip=True)
        
        # Buscar qualquer elemento com R$
        elementos_com_preco = produto_elem.find_all(string=lambda text: text and 'R$' in text)
        return elementos_com_preco[0].strip() if elementos_com_preco else ""
    
    def converter_preco_para_float(self, preco_texto: str) -> float:
        """Converte texto de preço para float"""
        if not preco_texto:
            return 0.0
        
        matches = re.findall(r'R\$?\s*([0-9]+(?:[.,][0-9]+)?)', preco_texto)
        if matches:
            try:
                return float(matches[0].replace(',', '.'))
            except ValueError:
                pass
        return 0.0
    
    def extrair_preco_antigo(self, produto_elem) -> Optional[float]:
        """Extrai preço antigo se disponível"""
        preco_antigo_elem = produto_elem.select_one(Config.PRECO_ANTIGO)
        if preco_antigo_elem:
            preco_antigo_texto = preco_antigo_elem.get_text(strip=True)
            match_antigo = re.search(r'([0-9]+(?:[.,][0-9]+)?)', preco_antigo_texto)
            if match_antigo:
                try:
                    return float(match_antigo.group(1).replace(',', '.'))
                except ValueError:
                    pass
        return None
    
    def calcular_desconto(self, preco_atual: float, preco_antigo: Optional[float], produto_elem) -> float:
        """Calcula porcentagem de desconto"""
        if preco_antigo and preco_antigo > preco_atual > 0:
            return round(((preco_antigo - preco_atual) / preco_antigo) * 100, 2)
        
        # Verificar desconto explícito
        desconto_elem = produto_elem.select_one(Config.DESCONTO_CONTAINER)
        if desconto_elem:
            desconto_texto = desconto_elem.get_text(strip=True)
            match_desconto = re.search(r'(\d+)%', desconto_texto)
            if match_desconto:
                return float(match_desconto.group(1))
        
        return 0.0
    
    def gerar_sku_produto(self, categoria_nome: str, index: int, url: Optional[str]) -> str:
        """Gera SKU único para o produto"""
        base_sku = f"MEDSUL_{categoria_nome.upper().replace(' ', '_')}_{index+1}"
        
        if url:
            url_match = re.search(r'/([^/]+)/p$', url)
            if url_match:
                return f"MEDSUL_{url_match.group(1).upper()}"
        
        return base_sku
    
    def criar_produto_dict(self, nome: str, preco: float, preco_antigo: Optional[float], 
                          desconto: float, url: Optional[str], sku: str, 
                          categoria_nome: str, preco_texto: str, index: int, 
                          descricao: str = None) -> Dict:
        """Cria dicionário com dados do produto"""
        
        # Extrair marca usando função universal
        marca, nome_limpo = self.extrair_marca_produto(nome)
        
        # Gerar chave de matching
        if marca and marca != "Marca não identificada":
            chave_matching = f"{nome_limpo.upper().strip()}_{marca.upper().strip()}"
        else:
            chave_matching = nome.upper().strip()
        
        return {
            'sku': sku,
            'nome': nome,
            'nome_limpo': nome_limpo,
            'marca': marca,
            'chave_matching': chave_matching,
            'preco': preco,
            'preco_antigo': preco_antigo,
            'porcentagem_desconto': desconto,
            'url': url or f"{self.base_url}/categoria/{categoria_nome.lower()}",
            'disponivel': preco > 0,
            'status': 'Disponível' if preco > 0 else 'Indisponível',
            'categoria_principal': categoria_nome,
            'categorias_completas': categoria_nome,
            'descricao': descricao or f"{nome} - Categoria: {categoria_nome}",
            'detalhes_produto': f"Produto encontrado na posição {index+1} da categoria {categoria_nome}",
            'categoria': categoria_nome,
            'preco_texto': preco_texto,
            'posicao': index + 1,
            'data_extracao': datetime.now().isoformat()
        }
    
    async def extrair_produtos_simples(self, page, categoria_nome: str) -> List[Dict]:
        """Extração otimizada e robusta de produtos"""
        print(f"[PACOTE] Extraindo produtos de {categoria_nome}")
        
        try:
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            produtos_elementos = soup.select(Config.PRODUTO_ITEM)
            print(f"   [INFO] {len(produtos_elementos)} produtos encontrados")
            
            produtos = []
            
            for i, produto_elem in enumerate(produtos_elementos):
                try:
                    # Extrair dados do produto usando métodos auxiliares
                    nome = self.extrair_nome_produto(produto_elem, i)
                    url = self.extrair_url_produto(produto_elem)
                    preco_texto = self.extrair_preco_texto(produto_elem)
                    preco = self.converter_preco_para_float(preco_texto)
                    preco_antigo = self.extrair_preco_antigo(produto_elem)
                    desconto = self.calcular_desconto(preco, preco_antigo, produto_elem)
                    sku = self.gerar_sku_produto(categoria_nome, i, url)
                    
                    # Extrair descrição do produto
                    descricao_elem = produto_elem.find("span", class_="tfcvgc-custom-0-x-shortDescriptionText")
                    descricao = descricao_elem.get_text(strip=True) if descricao_elem else f"{nome} - Categoria: {categoria_nome}"
                    
                    # Criar objeto produto
                    produto = self.criar_produto_dict(
                        nome, preco, preco_antigo, desconto, url, sku,
                        categoria_nome, preco_texto, i, descricao
                    )
                    
                    produtos.append(produto)
                    
                    # Log detalhado para os primeiros produtos
                    if i < 3:
                        print(f"   [NOTA] Produto {i+1}: '{nome}' - R$ {preco} - {url}")
                    
                except Exception as e:
                    print(f"   [ERRO] Erro ao extrair produto {i+1}: {e}")
                    continue
            
            print(f"   [OK] {len(produtos)} produtos extraídos com sucesso")
            self._mostrar_estatisticas_produtos(produtos)
            
            return produtos
            
        except Exception as e:
            print(f"   [ERRO] Erro na extração: {e}")
            return []
    
    def _mostrar_estatisticas_produtos(self, produtos: List[Dict]) -> None:
        """Mostra estatísticas dos produtos extraídos"""
        total = len(produtos)
        com_preco = sum(1 for p in produtos if p['preco'] > 0)
        com_url = sum(1 for p in produtos if p['url'] and not p['url'].endswith('/categoria/'))
        com_desconto = sum(1 for p in produtos if p['porcentagem_desconto'] > 0)
        
        print(f"   [STATS] Com preço: {com_preco}/{total}")
        print(f"   [STATS] Com URL: {com_url}/{total}")
        print(f"   [STATS] Com desconto: {com_desconto}/{total}")
    
    def _extrair_nome_categoria(self, url_categoria: str) -> str:
        """Extrai nome da categoria da URL"""
        return url_categoria.split('/')[-1].replace('-', ' ').title()
    
    def _atualizar_estatisticas_db(self, stats_db: Dict) -> None:
        """Atualiza estatísticas globais do banco de dados"""
        for key in self.stats_db_global:
            self.stats_db_global[key] += stats_db[key]
    
    def _mostrar_estatisticas_db_categoria(self, stats_db: Dict) -> None:
        """Mostra estatísticas do banco para a categoria"""
        mudancas_relevantes = (
            stats_db["novos"] > 0 or stats_db["atualizados"] > 0 or 
            stats_db["mudanca_disponibilidade"] > 0 or stats_db["novos_descontos"] > 0 or 
            stats_db["perdeu_desconto"] > 0
        )
        
        if mudancas_relevantes:
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
            print(f"   [STATS] DB: {', '.join(info_db)}")
    
    async def _processar_categoria_tentativa(self, url_categoria: str, categoria_nome: str) -> Optional[List[Dict]]:
        """Processa uma única tentativa de categoria"""
        if not self.browser or not self.context:
            print("[PROCESSANDO] Reconectando browser...")
            if await self.inicializar_browser():
                self.estatisticas['reconexoes'] += 1
            else:
                return None
        
        page = await self.context.new_page()
        
        try:
            # Navegar para a categoria
            await page.goto(url_categoria, timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Carregar todos os produtos
            produtos_carregados = await self.carregar_mais_produtos_simples(page, categoria_nome)
            
            # Extrair produtos
            produtos = await self.extrair_produtos_simples(page, categoria_nome)
            
            return produtos if produtos else None
            
        finally:
            await page.close()
    
    async def processar_categoria_robusta(self, url_categoria: str, max_tentativas: int = None) -> bool:
        """Processa uma categoria com múltiplas tentativas e reconexão"""
        max_tentativas = max_tentativas or Config.MAX_TENTATIVAS
        categoria_nome = self._extrair_nome_categoria(url_categoria)
        
        for tentativa in range(max_tentativas):
            try:
                print(f"[TAG] CATEGORIA: {categoria_nome} (Tentativa {tentativa + 1})")
                
                produtos = await self._processar_categoria_tentativa(url_categoria, categoria_nome)
                
                if produtos:
                    # Salvar produtos no banco de dados
                    print(f"[SALVANDO] Salvando {len(produtos)} produtos no banco de dados...")
                    stats_db = salvar_produtos_db(produtos, "Dental Medsul", "Dental Medsul")
                    
                    # Atualizar estatísticas
                    self._atualizar_estatisticas_db(stats_db)
                    self._mostrar_estatisticas_db_categoria(stats_db)
                    
                    # Atualizar estatísticas gerais
                    self.todos_produtos.extend(produtos)
                    self.estatisticas['produtos_extraidos'] += len(produtos)
                    
                    print(f"[OK] {categoria_nome}: {len(produtos)} produtos salvos no banco")
                    return True
                else:
                    print(f"[AVISO] {categoria_nome}: Nenhum produto extraído")
                
            except Exception as e:
                print(f"[ERRO] Erro tentativa {tentativa + 1} - {categoria_nome}: {e}")
                
                # Se falhou todas as tentativas, tentar reconectar
                if tentativa == max_tentativas - 1:
                    await self.fechar_browser()
                    await asyncio.sleep(5)
        
        self.estatisticas['erros'] += 1
        return False
    
    def _carregar_urls_categorias(self) -> List[str]:
        """Carrega URLs das categorias do arquivo"""
        try:
            # CORREÇÃO: Buscar arquivo na pasta do script, não na raiz
            script_dir = os.path.dirname(os.path.abspath(__file__))
            arquivo_links = os.path.join(script_dir, 'links_categorias_medsul.txt')
            with open(arquivo_links, 'r', encoding='utf-8') as f:
                return [linha.strip() for linha in f if linha.strip()]
        except FileNotFoundError:
            print("[ERRO] Arquivo 'links_categorias_medsul.txt' não encontrado na pasta dental_medsul/")
            return []
        except Exception as e:
            print(f"[ERRO] Erro ao carregar categorias: {e}")
            return []
    
    def _mostrar_estatisticas_finais(self, tempo_total: float, total_categorias: int) -> None:
        """Mostra estatísticas finais do scraping"""
        print("\n[ALVO] SCRAPING CONCLUÍDO!")
        print("="*60)
        print(f"[STATS] Categorias processadas: {self.estatisticas['categorias_processadas']}/{total_categorias}")
        print(f"[PACOTE] Total de produtos: {self.estatisticas['produtos_extraidos']}")
        print(f"[TEMPO] Tempo total: {tempo_total:.1f}s")
        print(f"[PROCESSANDO] Reconexões: {self.estatisticas['reconexoes']}")
        print(f"[ERRO] Erros: {self.estatisticas['erros']}")
    
    def _mostrar_estatisticas_banco(self) -> None:
        """Mostra estatísticas do banco de dados"""
        print("\n[SALVANDO] ESTATÍSTICAS DO BANCO DE DADOS:")
        print("="*60)
        print(f"[NOVO] Produtos NOVOS no banco: {self.stats_db_global['novos']}")
        print(f"[PROCESSANDO] Produtos ATUALIZADOS: {self.stats_db_global['atualizados']}")
        print(f"[STATS] Mudanças de DISPONIBILIDADE: {self.stats_db_global['mudanca_disponibilidade']}")
        print(f"[TAG] Produtos com NOVOS DESCONTOS: {self.stats_db_global['novos_descontos']}")
        print(f"💸 Produtos que PERDERAM desconto: {self.stats_db_global['perdeu_desconto']}")
        print(f"⚪ Produtos sem alteração: {self.stats_db_global['sem_alteracao']}")
    
    def _verificar_meta_produtos(self) -> None:
        """Verifica se a meta de produtos foi atingida"""
        meta = 4000
        if self.estatisticas['produtos_extraidos'] >= meta:
            print(f"\n[ALVO] [OK] META {meta}+ PRODUTOS ATINGIDA!")
        else:
            faltam = meta - self.estatisticas['produtos_extraidos']
            print(f"\n[ALVO] [AVISO] FALTAM {faltam} produtos para atingir {meta}+")
    
    def _mostrar_estatisticas_finais_banco(self) -> None:
        """Mostra estatísticas finais do banco de dados"""
        print("\n[CRESCIMENTO] ESTATÍSTICAS FINAIS DO BANCO:")
        print("="*60)
        try:
            consulta_db_estatisticas('Dental Medsul')
        except Exception as e:
            print(f"[ERRO] Erro ao consultar estatísticas do banco: {e}")
    
    async def executar_scraping_robusto(self) -> None:
        """Executa o scraping completo de forma robusta"""
        inicio = time.time()
        
        # Carregar URLs das categorias
        urls_categorias = self._carregar_urls_categorias()
        if not urls_categorias:
            print("[ERRO] Nenhuma categoria encontrada para processar")
            return
        
        try:
            # Processar cada categoria
            for i, url in enumerate(urls_categorias, 1):
                print(f"\n🔸 Processando categoria {i}/{len(urls_categorias)}: {url}")
                sucesso = await self.processar_categoria_robusta(url)
                
                if sucesso:
                    self.estatisticas['categorias_processadas'] += 1
                
                # Pausa entre categorias para evitar sobrecarga
                await asyncio.sleep(Config.DELAY_ENTRE_CATEGORIAS)
            
            # Calcular e mostrar estatísticas finais
            tempo_total = time.time() - inicio
            self.estatisticas['tempo_total'] = tempo_total
            
            self._mostrar_estatisticas_finais(tempo_total, len(urls_categorias))
            self._mostrar_estatisticas_banco()
            self._verificar_meta_produtos()
            self._mostrar_estatisticas_finais_banco()
            
        finally:
            await self.fechar_browser()

async def main() -> None:
    """
    Função principal que executa o scraping completo do site Dental Medsul.
    
    O scraper irá:
    1. Carregar as URLs das categorias do arquivo 'links_categorias_medsul.txt'
    2. Processar cada categoria extraindo todos os produtos disponíveis
    3. Salvar os produtos no banco de dados
    4. Mostrar estatísticas completas do processo
    """
    print("[INICIO] Iniciando Dental Medsul Scraper Robusto v2.0")
    print("="*60)
    
    scraper = DentalMedsulScraperRobusto()
    
    try:
        await scraper.executar_scraping_robusto()
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro fatal no scraping: {e}")
    finally:
        print("\n👋 Scraping finalizado")

if __name__ == "__main__":
    """
    Ponto de entrada do script.
    
    Executa o scraping de forma assíncrona usando asyncio.
    Certifique-se de que o arquivo 'links_categorias_medsul.txt' existe
    no mesmo diretório do script.
    """
    asyncio.run(main())
