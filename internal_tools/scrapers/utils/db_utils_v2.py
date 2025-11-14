import sqlite3
import re
from datetime import datetime
import os

# Definir o caminho do banco de forma absoluta baseado na localização deste arquivo
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "produtos.db") 

def extrair_marca_do_nome(nome_produto):
    """
    Extrai a marca real do nome do produto usando padrões comuns
    Versão melhorada para evitar usar nomes de sites como marcas
    """
    if not nome_produto:
        return None
    
    nome = nome_produto.strip()
    
    # Marcas conhecidas para buscar primeiro (mais específicas)
    marcas_conhecidas = [
        'SS WHITE', 'ULTRADENT', 'DENTSPLY', 'BIODINÂMICA', 'MAQUIRA', 'VOCO', 'KERR',
        'FGM', 'VIGODENT', 'GOLGRAN', 'MORELLI', 'ORTHOMETRIC', 'ANGELUS', 'WILCOS',
        '3M ESPE', '3M', 'IVOCLAR', 'CURADEN', 'BIOTEC', 'GNATUS', 'DENTAL VILLE',
        'DUFLEX', 'PROMEDICA', 'INDUSBELLO', 'HERPO', 'TECHNEW', 'FAVA', 'PRISMA',
        'BRUMABA', 'IODONTOSUL', 'ALLPRIME', 'INTRA-LOCK', 'CONEXÃO', 'NEODENT',
        'STRAUMANN', 'NOBEL', 'DENTOFLEX', 'DENTAL CREMER', 'BIONNOVATION',
        'AMERICAN BURRS', 'MICRODONT', 'LABORDENTAL', 'POLIDENTAL', 'MACRO',
        'CENTRIX', 'DMC', 'COLTENE', 'KULZER', 'GC', 'SHOFU', 'KURARAY',
        'TOKUYAMA', 'BEYOND', 'CAVEX', 'MARK3', 'SULTAN', 'PATTERSON',
        'HENRY SCHEIN', 'YOUNG', 'HOUSE BRAND', 'PREMIER', 'BISCO',
        'COSMEDENT', 'PARKELL', 'SUNSTAR', 'CROSSTEX', 'PALMERO',
        'GENDEX', 'DANAHER', 'PLANMECA', 'SIRONA', 'KAVO', 'NSK',
        'BIEN-AIR', 'W&H', 'DREVE', 'SCHEU', 'ERKODENT', 'KEYPRINT',
        'VERTEX', 'BREDENT', 'CANDULOR', 'RUTHINIUM', 'RENFERT',
        'AMANN GIRRBACH', 'ZIRKONZAHN', 'DENTAL WINGS', '3SHAPE',
        'BRUXZIR', 'LAVA', 'CEREC', 'EMAX', 'ZIRCONIA', 'CERAMCO',
        'SOLVENTUM', 'ICE', 'ODONTOMEGA'
    ]
    
    # Lista de nomes de sites que NÃO devem ser usados como marcas
    nomes_sites = [
        'SURYA DENTAL', 'DENTAL MEDSUL', 'APOIO DENTAL', 'DENTAL SPEED',
        'DENTAL SORRIA', 'DENTAL CREMER', 'DENTAL APOIO', 'CREMER DENTAL'
    ]
    
    # Tentar encontrar marcas conhecidas no nome (case insensitive)
    nome_upper = nome.upper()
    for marca in marcas_conhecidas:
        if marca in nome_upper:
            return marca.title()
    
    # Padrões de extração de marca
    padroes_marca = [
        # Padrão "Nome - Marca" (mais comum)
        r'[-–]\s*([A-Z][A-Za-z\s&\.]+?)(?:\s*[-–]|$)',
        # Padrão "Marca Nome do Produto"
        r'^([A-Z][A-Z\s&\.]{2,20}?)\s+[a-z]',
        # Padrão com parênteses "(Marca)"
        r'\(([A-Z][A-Za-z\s&\.]+?)\)',
        # Padrão "Nome / Marca"
        r'/\s*([A-Z][A-Za-z\s&\.]+?)(?:\s*/|$)',
        # Padrão com dois pontos "Nome: Marca"
        r':\s*([A-Z][A-Za-z\s&\.]+?)(?:\s*:|$)',
    ]
    
    for padrao in padroes_marca:
        matches = re.findall(padrao, nome)
        for match in matches:
            marca_candidata = match.strip()
            # Filtrar marcas válidas (mínimo 2 caracteres, máximo 30)
            if 2 <= len(marca_candidata) <= 30 and not marca_candidata.isdigit():
                # Verificar se não é um nome de site
                if marca_candidata.upper() not in nomes_sites:
                    # Remover palavras comuns que não são marcas
                    palavras_nao_marca = [
                        'UNIDADE', 'UNIDADES', 'CONJUNTO', 'CAIXA', 'PACOTE', 'KIT',
                        'SISTEMA', 'MODELO', 'TIPO', 'TAMANHO', 'COR', 'MEDIDA',
                        'BRANCO', 'AZUL', 'VERDE', 'VERMELHO', 'PRETO', 'CLARO',
                        'ESCURO', 'GRANDE', 'PEQUENO', 'MEDIO', 'ESPECIAL'
                    ]
                    if marca_candidata.upper() not in palavras_nao_marca:
                        return marca_candidata.title()
    
    # Se não encontrou nada, tentar primeira palavra se for maiúscula
    palavras = nome.split()
    if palavras and len(palavras[0]) > 2 and palavras[0].isupper():
        marca_candidata = palavras[0]
        # Verificar se não é um nome de site
        if marca_candidata.upper() not in nomes_sites:
            return marca_candidata.title()
    
    return None

def connect_db():
    """Conecta ao banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # Habilitar chaves estrangeiras
    return conn

def obter_proximo_id_bid():
    """Obtém o próximo ID_BID disponível"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Obter e incrementar contador
        cursor.execute("SELECT ultimo_id FROM contador_id_bid WHERE id = 1")
        resultado = cursor.fetchone()
        
        if resultado:
            proximo_id = resultado[0] + 1
        else:
            # Primeira vez, inserir contador
            cursor.execute("INSERT INTO contador_id_bid (id, ultimo_id) VALUES (1, 1)")
            proximo_id = 1
        
        # Atualizar contador
        cursor.execute("UPDATE contador_id_bid SET ultimo_id = ?, data_atualizacao = CURRENT_TIMESTAMP WHERE id = 1", (proximo_id,))
        conn.commit()
        conn.close()
        
        return proximo_id
    except Exception as e:
        print(f"[ERRO] Erro ao obter proximo ID_BID: {e}")
        return None

def determinar_status_produto(produto):
    """
    Determina o status do produto baseado nos campos disponíveis
    Prioriza o campo 'disponivel' (boolean) sobre 'status' (string)
    """
    # Se tem campo 'disponivel' (boolean), usar ele
    if 'disponivel' in produto:
        return 'Disponível' if produto['disponivel'] else 'Indisponível'
    
    # Se não tem 'disponivel', verificar o campo 'status'
    status_original = produto.get('status', '').upper()
    
    # Mapear valores comuns de status para formato padronizado
    if status_original in ['AVAILABLE', 'ATIVO', 'DISPONÍVEL']:
        return 'Disponível'
    elif status_original in ['UNAVAILABLE', 'INATIVO', 'INDISPONÍVEL']:
        return 'Indisponível'
    
    # Padrão quando não consegue determinar
    return 'Disponível'  # Assume disponível por padrão

def mapear_produto_para_nova_estrutura(produto_antigo, marca_nome, site_nome):
    """
    Mapeia um produto da estrutura antiga para a nova estrutura
    
    MAPEAMENTO DE CAMPOS:
    - sku → SKU_site
    - nome → Nome  
    - marca → Marca (corrigida se necessário)
    - preco → preco_normal
    - site → Site
    - categoria_principal → categoria
    - data_primeira_coleta → data_criacao
    - imagens_extras → imagem_extra
    - descricao → descricao_produto
    
    NOVOS CAMPOS:
    - id_bid: gerado automaticamente
    - preco_desconto: baseado em preco_antigo se houver desconto
    - info_embalagem: extraído da descrição se possível  
    - ultima_coleta: timestamp atual
    """
    
    # CORREÇÃO AUTOMÁTICA DE MARCA
    if marca_nome == site_nome or marca_nome.upper() in ['SURYA DENTAL', 'DENTAL MEDSUL', 'APOIO DENTAL', 'DENTAL SPEED']:
        marca_real = extrair_marca_do_nome(produto_antigo['nome'])
        marca_final = marca_real if marca_real else produto_antigo.get('marca', 'Marca não identificada')
    else:
        marca_final = marca_nome
    
    # Verificar se marca_final não é vazia ou None
    if not marca_final or marca_final.strip() == '':
        marca_final = 'Marca não identificada'
    
    # Calcular preço com desconto
    preco_normal = produto_antigo.get('preco', 0.0) or 0.0
    preco_antigo_valor = produto_antigo.get('preco_antigo', 0.0) or 0.0
    porcentagem_desconto = produto_antigo.get('porcentagem_desconto', 0.0) or 0.0
    
    # Se há desconto, o preco_desconto é o preço atual, senão é 0
    if porcentagem_desconto > 0 and preco_antigo_valor > preco_normal:
        preco_desconto = preco_normal
    else:
        preco_desconto = 0.0
        
    # Se preco_antigo existe e é maior que preco atual, usar preco_antigo como preco_normal
    if preco_antigo_valor > 0 and preco_antigo_valor > preco_normal:
        preco_normal = preco_antigo_valor
    
    # Garantir que categoria não seja vazia
    categoria = produto_antigo.get('categoria_principal', '').strip()
    if not categoria:
        categoria = 'Categoria não definida'
        
    # Extrair informações da embalagem da descrição (simplificado)
    info_embalagem = None
    descricao = produto_antigo.get('descricao', '') or produto_antigo.get('detalhes_produto', '')
    if descricao:
        # Buscar padrões comuns de embalagem
        padroes_embalagem = [
            r'(\d+\s*unidades?)', r'(\d+\s*ml)', r'(\d+\s*g)', r'(\d+\s*mg)',
            r'(caixa com \d+)', r'(kit com \d+)', r'(conjunto de \d+)',
            r'(unidade)', r'(frasco)', r'(tubo)', r'(sachê)', r'(ampola)'
        ]
        for padrao in padroes_embalagem:
            match = re.search(padrao, descricao.lower())
            if match:
                info_embalagem = match.group(1).title()
                break
    
    # Produto mapeado para nova estrutura
    produto_novo = {
        'SKU_site': produto_antigo.get('sku', ''),
        'Site': site_nome,
        'Nome': produto_antigo.get('nome', ''),
        'categoria': categoria,
        'subcategoria': produto_antigo.get('subcategoria'),
        'Marca': marca_final,
        'preco_normal': float(preco_normal),
        'preco_desconto': float(preco_desconto),
        'url': produto_antigo.get('url'),
        'status': determinar_status_produto(produto_antigo),
        'info_embalagem': info_embalagem,
        'descricao_produto': descricao,
        'imagem_principal': produto_antigo.get('imagem_principal'),
        'imagem_extra': produto_antigo.get('imagens_extras'),  # Renomeado
        'data_criacao': produto_antigo.get('data_primeira_coleta'),
        'data_atualizacao': produto_antigo.get('data_ultima_atualizacao'),
        'ultima_coleta': datetime.now().isoformat()
    }
    
    return produto_novo

def get_produto(sku, site_nome):
    """Busca um produto pelo SKU e site na nova estrutura."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE SKU_site = ? AND Site = ?", (sku, site_nome))
    result = cursor.fetchone()
    conn.close()
    return result

def get_produto_por_id_bid(id_bid):
    """Busca um produto pelo ID_BID (chave primária)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id_bid = ?", (id_bid,))
    result = cursor.fetchone()
    conn.close()
    return result

def insert_produto_v2(produto_novo):
    """
    Insere um novo produto na nova estrutura do banco
    """
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    
    # Obter próximo ID_BID se não especificado
    id_bid = obter_proximo_id_bid()
    if id_bid is None:
        print("[ERRO] Erro ao obter ID_BID")
        conn.close()
        return False
    
    try:
        cursor.execute("""
            INSERT INTO produtos (
                id_bid, SKU_site, Site, Nome, categoria, subcategoria, Marca,
                preco_normal, preco_desconto, url, status, info_embalagem,
                descricao_produto, imagem_principal, imagem_extra,
                data_criacao, data_atualizacao, ultima_coleta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_bid, produto_novo['SKU_site'], produto_novo['Site'], produto_novo['Nome'],
            produto_novo['categoria'], produto_novo['subcategoria'], produto_novo['Marca'],
            produto_novo['preco_normal'], produto_novo['preco_desconto'], produto_novo['url'],
            produto_novo['status'], produto_novo['info_embalagem'], produto_novo['descricao_produto'],
            produto_novo['imagem_principal'], produto_novo['imagem_extra'],
            produto_novo['data_criacao'] or agora, produto_novo['data_atualizacao'] or agora, 
            produto_novo['ultima_coleta'] or agora
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao inserir produto: {e}")
        conn.close()
        return False

def update_produto_v2(produto_novo, sku, site_nome):
    """Atualiza um produto existente na nova estrutura."""
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    
    try:
        cursor.execute("""
            UPDATE produtos 
            SET Nome = ?, categoria = ?, subcategoria = ?, Marca = ?,
                preco_normal = ?, preco_desconto = ?, url = ?, status = ?,
                info_embalagem = ?, descricao_produto = ?, imagem_principal = ?,
                imagem_extra = ?, data_atualizacao = ?, ultima_coleta = ?
            WHERE SKU_site = ? AND Site = ?
        """, (
            produto_novo['Nome'], produto_novo['categoria'], produto_novo['subcategoria'],
            produto_novo['Marca'], produto_novo['preco_normal'], produto_novo['preco_desconto'],
            produto_novo['url'], produto_novo['status'], produto_novo['info_embalagem'],
            produto_novo['descricao_produto'], produto_novo['imagem_principal'],
            produto_novo['imagem_extra'], agora, agora, sku, site_nome
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar produto: {e}")
        conn.close()
        return False

def update_produto_por_id_bid(produto_novo, id_bid):
    """Atualiza um produto existente pelo ID_BID (chave primária)."""
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    
    try:
        cursor.execute("""
            UPDATE produtos 
            SET SKU_site = ?, Site = ?, Nome = ?, categoria = ?, subcategoria = ?, Marca = ?,
                preco_normal = ?, preco_desconto = ?, url = ?, status = ?,
                info_embalagem = ?, descricao_produto = ?, imagem_principal = ?,
                imagem_extra = ?, data_atualizacao = ?, ultima_coleta = ?
            WHERE id_bid = ?
        """, (
            produto_novo['SKU_site'], produto_novo['Site'], produto_novo['Nome'], 
            produto_novo['categoria'], produto_novo['subcategoria'], produto_novo['Marca'],
            produto_novo['preco_normal'], produto_novo['preco_desconto'],
            produto_novo['url'], produto_novo['status'], produto_novo['info_embalagem'],
            produto_novo['descricao_produto'], produto_novo['imagem_principal'],
            produto_novo['imagem_extra'], agora, agora, id_bid
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar produto por ID_BID: {e}")
        conn.close()
        return False

def salvar_produtos_db(produtos, marca_nome, site_nome):
    """
    FUNÇÃO PRINCIPAL - Mantém compatibilidade com scripts existentes
    
    Esta função recebe produtos no formato antigo e os converte automaticamente
    para a nova estrutura antes de salvar no banco.
    
    Args:
        produtos: Lista de produtos no formato antigo
        marca_nome: Nome da marca (pode ser corrigido automaticamente)
        site_nome: Nome do site
        
    Returns:
        dict: Estatísticas do processo de salvamento
    """
    print(f"\n[SALVANDO] {len(produtos)} PRODUTOS - {site_nome}")
    print("[CONVERTENDO] Para nova estrutura...")
    
    stats_db = {
        "novos": 0,
        "atualizados": 0,
        "sem_alteracao": 0,
        "mudanca_disponibilidade": 0,
        "novos_descontos": 0,
        "perdeu_desconto": 0,
        "marcas_corrigidas": 0,
        "erros": 0
    }
    
    for produto in produtos:
        try:
            # Mapear produto para nova estrutura
            produto_novo = mapear_produto_para_nova_estrutura(produto, marca_nome, site_nome)
            
            # Verificar se produto já existe
            produto_existente = get_produto(produto_novo['SKU_site'], produto_novo['Site'])
            
            if produto_existente:
                # Produto existe - atualizar
                if update_produto_v2(produto_novo, produto_novo['SKU_site'], produto_novo['Site']):
                    stats_db["atualizados"] += 1
                else:
                    stats_db["erros"] += 1
            else:
                # Produto novo - inserir
                if insert_produto_v2(produto_novo):
                    stats_db["novos"] += 1
                    # Verificar se houve correção de marca
                    if marca_nome != produto_novo['Marca']:
                        stats_db["marcas_corrigidas"] += 1
                else:
                    stats_db["erros"] += 1
                    
        except Exception as e:
            print(f"[ERRO] Erro ao processar produto {produto.get('sku', 'N/A')}: {e}")
            stats_db["erros"] += 1
    
    # Exibir estatísticas
    print(f"[OK] PROCESSAMENTO CONCLUIDO:")
    print(f"   [NOVOS] Novos produtos: {stats_db['novos']}")
    print(f"   [ATUALIZADOS] Atualizados: {stats_db['atualizados']}")
    print(f"   [CORRIGIDOS] Marcas corrigidas: {stats_db['marcas_corrigidas']}")
    if stats_db["erros"] > 0:
        print(f"   [ERROS] Erros: {stats_db['erros']}")
    
    return stats_db

def consulta_db_estatisticas(site):
    """Consulta estatísticas do banco para um site específico"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Usar novos nomes de campos
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE Site = ?", (site,))
        total_produtos_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT Marca) FROM produtos WHERE Site = ?", (site,))
        total_marcas_db = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE Site = ? AND preco_desconto > 0", (site,))
        produtos_em_desconto = cursor.fetchone()[0]
        
        # Buscar produtos ativos considerando diferentes padrões de status
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE Site = ? AND (status = 'ativo' OR status = 'Disponível' OR status = 'AVAILABLE')", (site,))
        produtos_ativos = cursor.fetchone()[0]
        
        conn.close()

        print(f"\n[STATS] TOTAL NO BANCO ({site}): {total_produtos_db} produtos de {total_marcas_db} marcas")
        print(f"[DESCONTO] Produtos em DESCONTO: {produtos_em_desconto}")
        print(f"[ATIVOS] Produtos ATIVOS: {produtos_ativos}")
        print(f"[INATIVOS] Produtos INATIVOS: {total_produtos_db - produtos_ativos}")
        
    except Exception as e:
        print(f"[ERRO] Erro ao consultar estatisticas: {e}")
        conn.close()

# Funções de compatibilidade para manter scripts antigos funcionando
def atualizar_precos_produtos(produtos, site_nome):
    """Função de compatibilidade - redireciona para salvar_produtos_db"""
    return salvar_produtos_db(produtos, site_nome, site_nome)

def insert_produto(produto, marca_nome, site_nome):
    """Função de compatibilidade"""
    produto_novo = mapear_produto_para_nova_estrutura(produto, marca_nome, site_nome)
    return insert_produto_v2(produto_novo)

def update_produto(produto, site_nome, historicos=None):
    """Função de compatibilidade"""
    produto_novo = mapear_produto_para_nova_estrutura(produto, site_nome, site_nome)
    return update_produto_v2(produto_novo, produto['sku'], site_nome)

def delete_produto(sku, site_nome):
    """Remove um produto do banco usando novos nomes de campos."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE SKU_site = ? AND Site = ?", (sku, site_nome))
    conn.commit()
    conn.close()

print("[OK] DB_UTILS_V2 carregado - Suporte a nova estrutura ativo!")