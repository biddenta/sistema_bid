import sqlite3
import re
from datetime import datetime
import os

# Definir o caminho do banco de forma absoluta baseado na localização deste arquivo
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "produtos.db")

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
    """Conecta ao banco de dados."""
    return sqlite3.connect(DB_PATH)

def get_produto(sku, site_nome):
    """Busca um produto pelo SKU e site."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE sku = ? AND site = ?", (sku, site_nome))
    result = cursor.fetchone()
    conn.close()
    return result

def insert_produto(produto, marca_nome, site_nome):
    """
    Insere um novo produto no banco.
    ATENÇÃO: Se marca_nome for igual ao site_nome, tenta extrair a marca real do nome do produto
    """
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    
    # Verificar se marca_nome é na verdade o nome do site
    if marca_nome == site_nome or marca_nome.upper() in ['SURYA DENTAL', 'DENTAL MEDSUL', 'APOIO DENTAL', 'DENTAL SPEED']:
        marca_real = extrair_marca_do_nome(produto['nome'])
        marca_final = marca_real if marca_real else produto.get('marca', 'Marca não identificada')
        print(f"[AVISO]  Marca corrigida: {marca_nome} → {marca_final} (produto: {produto['nome'][:50]}...)")
    else:
        marca_final = marca_nome
    
    cursor.execute("""
        INSERT INTO produtos 
        (sku, nome, marca, preco, preco_antigo, porcentagem_desconto, url, site, disponivel, status, 
         categoria_principal, subcategoria, categorias_completas, imagem_principal, imagens_extras,
         descricao, detalhes_produto, data_primeira_coleta, data_ultima_atualizacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        produto['sku'], produto['nome'], marca_final, produto['preco'], produto['preco_antigo'],
        produto['porcentagem_desconto'], produto['url'], site_nome, produto['disponivel'],
        produto['status'], produto['categoria_principal'], produto.get('subcategoria', 'N/A'), 
        produto['categorias_completas'], produto.get('imagem_principal'), produto.get('imagens_extras'),
        produto['descricao'], produto['detalhes_produto'], agora, agora
    ))
    conn.commit()
    conn.close()

def update_produto(produto, site_nome, historicos):
    """Atualiza um produto existente no banco."""
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    cursor.execute("""
        UPDATE produtos 
        SET preco = ?, preco_antigo = ?, porcentagem_desconto = ?, disponivel = ?, status = ?, 
            categoria_principal = ?, subcategoria = ?, categorias_completas = ?, 
            imagem_principal = ?, imagens_extras = ?, descricao = ?, detalhes_produto = ?, 
            data_ultima_atualizacao = ?, historico_precos = ?, historico_disponibilidade = ?, historico_descontos = ?
        WHERE sku = ? AND site = ?
    """, (
        produto['preco'], produto['preco_antigo'], produto['porcentagem_desconto'], produto['disponivel'],
        produto['status'], produto['categoria_principal'], produto.get('subcategoria', 'N/A'), 
        produto['categorias_completas'], produto.get('imagem_principal'), produto.get('imagens_extras'),
        produto['descricao'], produto['detalhes_produto'], agora,
        historicos.get('precos', ''), historicos.get('disponibilidade', ''), historicos.get('descontos', ''),
        produto['sku'], site_nome
    ))
    conn.commit()
    conn.close()

def delete_produto(sku, site_nome):
    """Remove um produto do banco."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE sku = ? AND site = ?", (sku, site_nome))
    conn.commit()
    conn.close()

def salvar_produtos_db(produtos, marca_nome, site_nome):
    """
    Salva produtos no banco, detectando alterações e mantendo históricos.
    VERSÃO MELHORADA: Corrige automaticamente marcas que são nomes de sites.
    Retorna estatísticas do processo.
    """
    conn = connect_db()
    cursor = conn.cursor()
    stats_db = {
        "novos": 0,
        "atualizados": 0,
        "sem_alteracao": 0,
        "mudanca_disponibilidade": 0,
        "novos_descontos": 0,
        "perdeu_desconto": 0,
        "marcas_corrigidas": 0
    }
    agora = datetime.now().isoformat()

    for produto in produtos:
        sku = produto['sku']
        preco = produto['preco']
        preco_antigo = produto['preco_antigo']
        porcentagem_desconto = produto['porcentagem_desconto']
        disponivel = produto['disponivel']
        status = produto['status']
        categoria_principal = produto['categoria_principal']
        categorias_completas = produto['categorias_completas']
        descricao = produto['descricao']
        detalhes_produto = produto['detalhes_produto']
        
        # CORREÇÃO AUTOMÁTICA DE MARCA
        # Verificar se marca_nome é na verdade o nome do site
        if marca_nome == site_nome or marca_nome.upper() in ['SURYA DENTAL', 'DENTAL MEDSUL', 'APOIO DENTAL', 'DENTAL SPEED']:
            marca_real = extrair_marca_do_nome(produto['nome'])
            marca_final = marca_real if marca_real else produto.get('marca', 'Marca não identificada')
            if marca_real:
                stats_db["marcas_corrigidas"] += 1
        else:
            marca_final = marca_nome

        cursor.execute("""
            SELECT preco, preco_antigo, porcentagem_desconto, disponivel, historico_precos, 
                   historico_disponibilidade, historico_descontos, data_primeira_coleta 
            FROM produtos WHERE sku = ? AND site = ?
        """, (sku, site_nome))
        resultado = cursor.fetchone()

        if resultado:
            (preco_anterior, preco_antigo_anterior, desconto_anterior, disponivel_anterior, 
             historico_precos, historico_disponibilidade, historico_descontos, data_primeira) = resultado

            alterou_preco = preco != preco_anterior
            alterou_disponibilidade = disponivel != disponivel_anterior
            alterou_desconto = porcentagem_desconto != desconto_anterior

            novo_historico_precos = historico_precos or ""
            novo_historico_disponibilidade = historico_disponibilidade or ""
            novo_historico_descontos = historico_descontos or ""

            if alterou_preco or alterou_disponibilidade or alterou_desconto:
                if alterou_preco:
                    novo_historico_precos = f"{novo_historico_precos}|{agora}:{preco_anterior}" if novo_historico_precos else f"{agora}:{preco_anterior}"
                if alterou_disponibilidade:
                    status_anterior = "Disponível" if disponivel_anterior else "Indisponível"
                    novo_historico_disponibilidade = f"{novo_historico_disponibilidade}|{agora}:{status_anterior}" if novo_historico_disponibilidade else f"{agora}:{status_anterior}"
                    stats_db["mudanca_disponibilidade"] += 1
                if alterou_desconto:
                    if porcentagem_desconto > 0 and desconto_anterior == 0:
                        novo_historico_descontos = f"{novo_historico_descontos}|{agora}:GANHOU_DESCONTO:{porcentagem_desconto}%" if novo_historico_descontos else f"{agora}:GANHOU_DESCONTO:{porcentagem_desconto}%"
                        stats_db["novos_descontos"] += 1
                    elif porcentagem_desconto == 0 and desconto_anterior > 0:
                        novo_historico_descontos = f"{novo_historico_descontos}|{agora}:PERDEU_DESCONTO:{preco}" if novo_historico_descontos else f"{agora}:PERDEU_DESCONTO:{preco}"
                        stats_db["perdeu_desconto"] += 1

                cursor.execute("""
                    UPDATE produtos 
                    SET preco = ?, preco_antigo = ?, porcentagem_desconto = ?, disponivel = ?, status = ?, 
                        categoria_principal = ?, subcategoria = ?, categorias_completas = ?, 
                        imagem_principal = ?, imagens_extras = ?, descricao = ?, detalhes_produto = ?, 
                        marca = ?, data_ultima_atualizacao = ?, historico_precos = ?, historico_disponibilidade = ?, historico_descontos = ?
                    WHERE sku = ? AND site = ?
                """, (preco, preco_antigo, porcentagem_desconto, disponivel, status, categoria_principal, 
                      produto.get('subcategoria', 'N/A'), categorias_completas, produto.get('imagem_principal'), 
                      produto.get('imagens_extras'), descricao, detalhes_produto, marca_final, agora, 
                      novo_historico_precos, novo_historico_disponibilidade, novo_historico_descontos, sku, site_nome))
                stats_db["atualizados"] += 1
            else:
                cursor.execute("""
                    UPDATE produtos 
                    SET data_ultima_atualizacao = ?, status = ?, categoria_principal = ?, 
                        subcategoria = ?, categorias_completas = ?, imagem_principal = ?, 
                        imagens_extras = ?, descricao = ?, detalhes_produto = ?, marca = ?
                    WHERE sku = ? AND site = ?
                """, (agora, status, categoria_principal, produto.get('subcategoria', 'N/A'), 
                      categorias_completas, produto.get('imagem_principal'), produto.get('imagens_extras'), 
                      descricao, detalhes_produto, marca_final, sku, site_nome))
                stats_db["sem_alteracao"] += 1
        else:
            cursor.execute("""
                INSERT INTO produtos 
                (sku, nome, marca, preco, preco_antigo, porcentagem_desconto, url, site, disponivel, status, 
                 categoria_principal, subcategoria, categorias_completas, imagem_principal, imagens_extras,
                 descricao, detalhes_produto, data_primeira_coleta, data_ultima_atualizacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, produto['nome'], marca_final, preco, preco_antigo, porcentagem_desconto, produto['url'], site_nome, 
                  disponivel, status, categoria_principal, produto.get('subcategoria', 'N/A'), categorias_completas, 
                  produto.get('imagem_principal'), produto.get('imagens_extras'), descricao, 
                  detalhes_produto, agora, agora))
            stats_db["novos"] += 1
            if porcentagem_desconto > 0:
                stats_db["novos_descontos"] += 1

    conn.commit()
    conn.close()
    
    # Mostrar estatísticas de correção de marcas
    if stats_db["marcas_corrigidas"] > 0:
        print(f"🔧 {stats_db['marcas_corrigidas']} produtos tiveram suas marcas corrigidas automaticamente")
    
    return stats_db

# Resto das funções permanecem iguais...
def consulta_db_estatisticas(site):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos WHERE site = ?", (site,))
    total_produtos_db = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT marca) FROM produtos WHERE site = ?", (site,))
    total_marcas_db = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM produtos WHERE site = ? AND porcentagem_desconto > 0", (site,))
    produtos_em_desconto = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM produtos WHERE site = ? AND disponivel = 1", (site,))
    produtos_disponiveis = cursor.fetchone()[0]
    conn.close()

    print(f"\n[STATS] TOTAL NO BANCO ({site}): {total_produtos_db} produtos de {total_marcas_db} marcas")
    print(f"[TAG]  Produtos em DESCONTO: {produtos_em_desconto}")
    print(f"[OK] Produtos DISPONÍVEIS: {produtos_disponiveis}")
    print(f"[ERRO] Produtos INDISPONÍVEIS: {total_produtos_db - produtos_disponiveis}")

def atualizar_precos_produtos(produtos, site_nome):
    """Atualiza apenas preços e disponibilidade dos produtos existentes - para atualização diária"""
    conn = connect_db()
    cursor = conn.cursor()
    agora = datetime.now().isoformat()
    
    atualizados = 0
    novos = 0
    erros = 0
    
    print(f"[PRECO] Atualizando preços de {len(produtos)} produtos...")
    
    for produto in produtos:
        try:
            # Verificar se produto já existe
            cursor.execute("SELECT id FROM produtos WHERE sku = ? AND site = ?", 
                         (produto['sku'], site_nome))
            produto_existente = cursor.fetchone()
            
            # Extrair marca real se necessário
            marca_produto = produto.get('marca', 'Marca não identificada')
            if marca_produto == site_nome or marca_produto.upper() in ['SURYA DENTAL', 'DENTAL MEDSUL', 'APOIO DENTAL', 'DENTAL SPEED']:
                marca_real = extrair_marca_do_nome(produto['nome'])
                marca_produto = marca_real if marca_real else 'Marca não identificada'
            
            if produto_existente:
                # Atualizar dados incluindo marca corrigida
                cursor.execute("""
                    UPDATE produtos 
                    SET preco = ?, preco_antigo = ?, porcentagem_desconto = ?, 
                        disponivel = ?, status = ?, url = ?, nome = ?, marca = ?,
                        data_ultima_atualizacao = ?
                    WHERE sku = ? AND site = ?
                """, (
                    produto['preco'], produto.get('preco_antigo'), produto['porcentagem_desconto'],
                    produto['disponivel'], produto['status'], produto['url'], produto['nome'], 
                    marca_produto, agora, produto['sku'], site_nome
                ))
                atualizados += 1
            else:
                # Produto novo - inserir com dados mínimos
                cursor.execute("""
                    INSERT INTO produtos 
                    (sku, nome, marca, preco, preco_antigo, porcentagem_desconto, url, site, 
                     disponivel, status, categoria_principal, subcategoria, categorias_completas,
                     imagem_principal, imagens_extras, descricao, detalhes_produto,
                     data_primeira_coleta, data_ultima_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    produto['sku'], produto['nome'], marca_produto,
                    produto['preco'], produto.get('preco_antigo'), produto['porcentagem_desconto'],
                    produto['url'], site_nome, produto['disponivel'], produto['status'],
                    'A definir', None, 'A definir', None, None, '', '',
                    agora, agora
                ))
                novos += 1
                
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar {produto['sku']}: {e}")
            erros += 1
    
    conn.commit()
    conn.close()
    
    print(f"[STATS] Resultado da atualização:")
    print(f"   [OK] {atualizados} produtos atualizados")
    print(f"   [NOVO] {novos} produtos novos")
    if erros > 0:
        print(f"   [ERRO] {erros} erros")
