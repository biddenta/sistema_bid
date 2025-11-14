import sys, os, time, requests, re, json, random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Adicionar pasta pai ao path para importar db_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db_utils_v2 import salvar_produtos_db, consulta_db_estatisticas

# Importar função universal de extração de marca
from utils.marca_utils_final import extrair_marca_universal, processar_produto_completo

# Session global para reutilizar conexões
session = requests.Session()

def configurar_session():
    """Configura session com headers realistas"""
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    })

def extrair_detalhes_produto_anti_bloqueio(url_produto, tentativa=1):
    """Extrai descrição e especificações com medidas anti-bloqueio"""
    try:
        # Pausa aleatória entre 0.5 e 2.0 segundos
        pausa = random.uniform(0.5, 2.0)
        time.sleep(pausa)
        
        # Timeout progressivo baseado na tentativa
        timeout = 10 + (tentativa * 5)
        
        # Fazer requisição
        response = session.get(url_produto, timeout=timeout)
        
        if response.status_code == 429:  # Too Many Requests
            print(f" | RATE_LIMIT - pausando 30s")
            time.sleep(30)
            if tentativa < 3:
                return extrair_detalhes_produto_anti_bloqueio(url_produto, tentativa + 1)
            else:
                return None, None, None
        
        if response.status_code == 403:  # Forbidden
            print(f" | BLOQUEADO - pausando 60s")
            time.sleep(60)
            if tentativa < 2:
                return extrair_detalhes_produto_anti_bloqueio(url_produto, tentativa + 1)
            else:
                return None, None, None
        
        if response.status_code != 200:
            return None, None, None
        
        # Verificar se recebeu conteúdo válido (não uma página de erro)
        if len(response.content) < 1000:
            return None, None, None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Verificar se foi redirecionado para página de erro
        title = soup.find("title")
        if title and ("erro" in title.get_text().lower() or "error" in title.get_text().lower()):
            return None, None, None
        
        descricao = ""
        especificacoes = ""
        
        # Buscar pela estrutura específica
        detalhes_list = soup.select("ul.flex.flex-col.gap-4 li")
        
        for item in detalhes_list:
            titulo_elem = item.find("p", class_=lambda x: x and "text-black" in " ".join(x))
            conteudo_elem = item.find("span", class_=lambda x: x and "text-[#656464]" in " ".join(x))
            
            # Fallback
            if not titulo_elem or not conteudo_elem:
                titulo_elem = item.find("p")
                conteudo_elem = item.find("span")
            
            if titulo_elem and conteudo_elem:
                titulo = titulo_elem.get_text(strip=True)
                conteudo = conteudo_elem.get_text(strip=True)
                
                if "indicação" in titulo.lower():
                    descricao = conteudo
                elif "características" in titulo.lower():
                    especificacoes = conteudo
                
                if descricao and especificacoes:
                    break
        
        return descricao or None, especificacoes or None, None
        
    except requests.exceptions.Timeout:
        if tentativa < 3:
            print(f" | TIMEOUT_T{tentativa} - retry")
            time.sleep(5)
            return extrair_detalhes_produto_anti_bloqueio(url_produto, tentativa + 1)
        return None, None, None
    except requests.exceptions.ConnectionError:
        if tentativa < 2:
            print(f" | CONN_ERROR - retry")
            time.sleep(10)
            return extrair_detalhes_produto_anti_bloqueio(url_produto, tentativa + 1)
        return None, None, None
    except Exception:
        return None, None, None

def extrair_imagens_produto_anti_bloqueio(url_produto):
    """Extrai imagens com medidas anti-bloqueio"""
    try:
        # Pausa menor para imagens
        time.sleep(random.uniform(0.3, 1.0))
        
        response = session.get(url_produto, timeout=10)
        
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        imagem_principal = None
        imagens_extras = []
        
        # Buscar imagens
        img_elements = soup.find_all("img", src=re.compile(r'fbitsstatic'))
        
        if img_elements:
            # Primeira como principal
            src = img_elements[0].get('src', '')
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(url_produto, src)
            imagem_principal = src
            
            # Extras (máximo 3 para ser mais rápido)
            for img in img_elements[1:4]:
                src = img.get('src', '')
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(url_produto, src)
                if src and src != imagem_principal:
                    imagens_extras.append(src)
        
        return imagem_principal, json.dumps(imagens_extras) if imagens_extras else None
        
    except Exception:
        return None, None

def extrair_produtos_pagina_anti_bloqueio(url_pagina, categoria_base):
    """Extrai produtos com medidas anti-bloqueio"""
    
    try:
        # Pausa inicial antes da página
        time.sleep(random.uniform(1.0, 3.0))
        
        response = session.get(url_pagina, timeout=15)
        
        if response.status_code == 429:
            print("Rate limit na listagem - pausando 30s")
            time.sleep(30)
            response = session.get(url_pagina, timeout=15)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, "html.parser")
        produtos_elementos = soup.find_all("div", id=re.compile(r"product-card-\d+"))
        
        if not produtos_elementos:
            return []
        
        produtos = []
        total_produtos = len(produtos_elementos)
        sucessos_desc = 0
        falhas_consecutivas = 0
        
        for i, elemento in enumerate(produtos_elementos, 1):
            try:
                produto = {}
                
                # Dados básicos (sem requisição adicional)
                
                # Nome do produto - Verificar title completo vs texto truncado
                nome_elem = elemento.find("h2") or elemento.find("h3")
                if nome_elem:
                    # Tentar obter nome completo do atributo title
                    nome_completo = nome_elem.get('title', '').strip()
                    if nome_completo:
                        produto['nome'] = nome_completo
                    else:
                        produto['nome'] = nome_elem.get_text(strip=True)
                else:
                    produto['nome'] = f"Produto {i}"
                
                link_elem = elemento.find("a", href=True)
                produto['url'] = urljoin(url_pagina, link_elem.get('href', '')) if link_elem else ""
                
                preco_elem = elemento.find("div", string=re.compile(r'R\$'))
                if preco_elem:
                    preco_texto = preco_elem.get_text(strip=True)
                    preco_match = re.search(r'R\$\s*([\d.,]+)', preco_texto)
                    produto['preco'] = float(preco_match.group(1).replace('.', '').replace(',', '.')) if preco_match else 0
                else:
                    produto['preco'] = 0
                
                element_id = elemento.get('id', '')
                sku_match = re.search(r'product-card-(\d+)', element_id)
                produto['sku'] = f"PROCLIN_{sku_match.group(1)}" if sku_match else f"PROCLIN_{produto['nome'].replace(' ', '-').upper()[:20]}"
                
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
                
                # Extrair descrição diretamente do card do produto
                descricao_card = None
                desc_elem = elemento.find("div", class_="text-xs text-[#A1A1A1] text-start md:text-xs custom-text-line-2")
                if desc_elem:
                    descricao_card = desc_elem.get_text(strip=True)
                    print(f" | DESC_CARD: {descricao_card[:30]}...")
                
                # Print progress
                nome_curto = produto['nome'][:35] + "..." if len(produto['nome']) > 35 else produto['nome']
                print(f"  [{i:2d}/{total_produtos:2d}] {nome_curto:<40} R$ {produto['preco']:<8.2f}", end="")
                
                # EXTRAÇÃO DE DESCRIÇÃO E DETALHES
                if descricao_card:
                    # [OK] Priorizar descrição do card (mais eficiente)
                    produto['descricao'] = descricao_card
                    produto['detalhes_produto'] = None  # Detalhes só pela página individual
                    sucessos_desc += 1
                    falhas_consecutivas = 0
                    
                    # Extrair imagens da página individual apenas se tiver URL
                    if produto['url']:
                        imagem_principal, imagens_extras = extrair_imagens_produto_anti_bloqueio(produto['url'])
                        produto['imagem_principal'] = imagem_principal
                        produto['imagens_extras'] = imagens_extras
                    else:
                        produto['imagem_principal'] = None
                        produto['imagens_extras'] = None
                    
                elif produto['url'] and falhas_consecutivas < 5:
                    # [PROCESSANDO] Fallback: tentar extrair da página individual
                    descricao, especificacoes, _ = extrair_detalhes_produto_anti_bloqueio(produto['url'])
                    produto['descricao'] = descricao
                    produto['detalhes_produto'] = especificacoes
                    
                    # Imagens (apenas se conseguiu descrição/especificação)
                    if descricao or especificacoes:
                        imagem_principal, imagens_extras = extrair_imagens_produto_anti_bloqueio(produto['url'])
                        produto['imagem_principal'] = imagem_principal
                        produto['imagens_extras'] = imagens_extras
                        sucessos_desc += 1
                        falhas_consecutivas = 0
                    else:
                        produto['imagem_principal'] = None
                        produto['imagens_extras'] = None
                        falhas_consecutivas += 1
                else:
                    # [ERRO] Sem descrição disponível
                    produto['descricao'] = None
                    produto['detalhes_produto'] = None
                    produto['imagem_principal'] = None
                    produto['imagens_extras'] = None
                    falhas_consecutivas += 1
                
                # Status para logging
                status_desc = "[OK]" if produto.get('descricao') else "✗"
                status_det = "[OK]" if produto.get('detalhes_produto') else "✗" 
                status_img = "[OK]" if produto.get('imagem_principal') else "✗"
                
                print(f" | D:{status_desc} Det:{status_det} I:{status_img} | F:{falhas_consecutivas}")
                
                # Campos obrigatórios finais
                produto['preco_antigo'] = None
                produto['porcentagem_desconto'] = 0
                produto['disponivel'] = produto['preco'] > 0
                produto['status'] = "Disponível" if produto['preco'] > 0 else "Indisponível"
                produto['categoria_principal'] = categoria_base
                produto['subcategoria'] = None
                produto['categorias_completas'] = categoria_base
                produto['site'] = "Dental Proclin"
                
                produtos.append(produto)
                
                # Se muitas falhas consecutivas, fazer pausa maior
                if falhas_consecutivas >= 3:
                    print(f"AVISO: {falhas_consecutivas} falhas consecutivas - pausando extra")
                    time.sleep(5)
                
            except Exception as e:
                print(f"  [{i:2d}/{total_produtos:2d}] ERRO: {str(e)[:30]}...")
                continue
        
        print(f"Sucessos com descricao: {sucessos_desc}/{total_produtos} ({sucessos_desc/total_produtos*100:.1f}%)")
        return produtos
        
    except Exception as e:
        print(f"Erro na pagina: {e}")
        return []

def executar_scraping_anti_bloqueio():
    """Executa scraping com medidas anti-bloqueio"""
    
    print("SCRAPING ANTI-BLOQUEIO - DENTAL PROCLIN")
    print("=" * 60)
    print(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Medidas anti-bloqueio ativas")
    print("=" * 60)
    
    # Configurar session
    configurar_session()
    
    # Carregar categorias
    try:
        # CORREÇÃO: Buscar arquivo na pasta do script com extensão .txt
        script_dir = os.path.dirname(os.path.abspath(__file__))
        arquivo_categorias = os.path.join(script_dir, 'categorias_dentalproclin.txt')
        with open(arquivo_categorias, 'r', encoding='utf-8') as f:
            categorias = [linha.strip() for linha in f if linha.strip()]
    except FileNotFoundError:
        print("[ERRO] Arquivo 'categorias_dentalproclin.txt' não encontrado na pasta dental_proclin/!")
        return
    
    site_nome = "Dental Proclin"
    todos_produtos = []
    
    # Testar todas as categorias
    for idx_cat, url_categoria in enumerate(categorias, 1):
        try:
            categoria_base = url_categoria.split('/')[-1].replace('-', ' ').title()
            
            print(f"\nCategoria [{idx_cat:2d}/{len(categorias):2d}] {categoria_base}")
            print(f"URL: {url_categoria}")
            print("-" * 60)
            
            produtos_categoria = []
            pagina = 1
            
            while pagina <= 10:  # Máximo 10 páginas por categoria
                if "?" in url_categoria:
                    url_pagina = f"{url_categoria}&page={pagina}"
                else:
                    url_pagina = f"{url_categoria}?page={pagina}"
                
                print(f"Pagina {pagina}:")
                
                produtos_pagina = extrair_produtos_pagina_anti_bloqueio(url_pagina, categoria_base)
                
                if produtos_pagina:
                    produtos_categoria.extend(produtos_pagina)
                    print(f"OK {len(produtos_pagina)} produtos extraidos da pagina {pagina}")
                    pagina += 1
                    
                    # Pausa maior entre páginas
                    time.sleep(random.uniform(2.0, 4.0))
                else:
                    print(f"Pagina {pagina} vazia - finalizando categoria")
                    break
            
            if produtos_categoria:
                todos_produtos.extend(produtos_categoria)
                print(f"Total da categoria: {len(produtos_categoria)} produtos")
                
                # Salvar parcialmente a cada categoria
                print(f"Salvando categoria {categoria_base}...")
                try:
                    salvar_produtos_db(produtos_categoria, site_nome, site_nome)
                    print("Categoria salva!")
                    
                    # Estatísticas parciais
                    total_com_desc = sum(1 for p in produtos_categoria if p.get('descricao'))
                    total_com_det = sum(1 for p in produtos_categoria if p.get('detalhes_produto'))
                    print(f"Descricoes: {total_com_desc}/{len(produtos_categoria)} ({total_com_desc/len(produtos_categoria)*100:.1f}%)")
                    print(f"Especificacoes: {total_com_det}/{len(produtos_categoria)} ({total_com_det/len(produtos_categoria)*100:.1f}%)")
                    
                except Exception as e:
                    print(f"Erro ao salvar categoria: {e}")
            
            # Pausa longa entre categorias
            if idx_cat < len(categorias):
                pausa_categoria = random.uniform(5.0, 10.0)
                print(f"Pausando {pausa_categoria:.1f}s antes da proxima categoria...")
                time.sleep(pausa_categoria)
                
        except Exception as e:
            print(f"Erro na categoria {categoria_base}: {e}")
            continue
    
    print(f"\nSCRAPING COMPLETO FINALIZADO!")
    print(f"Total coletado: {len(todos_produtos)} produtos")
    
    # Estatísticas finais detalhadas
    if todos_produtos:
        total_com_desc = sum(1 for p in todos_produtos if p.get('descricao'))
        total_com_det = sum(1 for p in todos_produtos if p.get('detalhes_produto'))
        total_com_img = sum(1 for p in todos_produtos if p.get('imagem_principal'))
        
        print(f"\nESTATISTICAS FINAIS:")
        print(f"Total de produtos: {len(todos_produtos)}")
        print(f"Com descricao: {total_com_desc} ({total_com_desc/len(todos_produtos)*100:.1f}%)")
        print(f"Com especificacoes: {total_com_det} ({total_com_det/len(todos_produtos)*100:.1f}%)")
        print(f"Com imagens: {total_com_img} ({total_com_img/len(todos_produtos)*100:.1f}%)")
        
        # Consultar estatísticas do banco
        print(f"\nESTATISTICAS DO BANCO:")
        try:
            consulta_db_estatisticas(site_nome)
        except Exception as e:
            print(f"Erro ao consultar estatisticas: {e}")
    
    print(f"Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    executar_scraping_anti_bloqueio()
