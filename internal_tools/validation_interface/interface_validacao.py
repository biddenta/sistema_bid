import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from utils.cache_validacao import get_cache_instance
from utils.auth import (
    is_logged_in, mostrar_tela_login, mostrar_info_usuario,
    is_admin, is_ajudante, get_username, get_user_display_name, get_user_role
)
from utils.matching_integration import MatchingComFeedback

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# URL base da API (ajustar se necessário)
API_BASE_URL = "http://localhost:8000/api/v1"

# Configuração da página
st.set_page_config(
    page_title="Validação de Matches - Match produtos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

st.markdown("""
<style>
    .match-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        margin: 15px 0;
        background: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .produto-item {
        margin: 8px 0;
        padding: 12px;
        background: #f8f9fa;
        border-radius: 6px;
        border-left: 3px solid #007bff;
        font-size: 14px;
    }
    .stats-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin: 5px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .stats-box h3 {
        margin: 0;
        font-size: 2em;
        font-weight: bold;
    }
    .stats-box p {
        margin: 5px 0 0 0;
        font-size: 0.9em;
        opacity: 0.9;
    }
    /* Melhorar aparência dos checkboxes */
    .stCheckbox > label > div:first-child {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
    }
    /* Espaçamento melhor */
    .block-container {
        padding-top: 1rem;
    }
    /* Alertas mais sutis */
    .stAlert > div {
        border-radius: 6px;
        border: none;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES DE API
# ============================================================================

def verificar_api_disponivel() -> bool:
    """Verifica se a API está disponível"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

@st.cache_data(ttl=600, show_spinner=False)  # Cache sem mostrar spinner
def carregar_categorias_disponiveis() -> List[str]:
    """
    Carrega lista de categorias disponíveis
    Filtra apenas categorias válidas (ignora marcas misturadas)
    """
    todas_categorias = []
    max_tentativas = 3
    
    for tentativa in range(max_tentativas):
        try:
            response = requests.get(
                f"{API_BASE_URL}/produtos/categorias/disponiveis",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            todas_categorias = data.get("categorias", [])
            break  # Sucesso, sair do loop
        except requests.exceptions.ConnectionError:
            if tentativa < max_tentativas - 1:
                time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
                continue
            # Última tentativa falhou
            st.warning("API temporariamente indisponível. Tentando novamente...")
        except Exception as e:
            st.error(f"Erro ao carregar categorias: {e}")
            break
    
    if not todas_categorias:
        return []
    
    # Lista de categorias conhecidas/válidas (keywords que indicam categorias reais)
    categorias_validas_keywords = [
        'Anestésico', 'Anestesico', 'Biossegurança', 'Biosseguranca',
        'Cimento', 'Descartáve', 'Descartave', 'Endodontia', 'Ortodontia',
        'Protese', 'Prótese', 'Implantodontia', 'Implante', 'Moldagem',
        'Cirurgia', 'Periodontia', 'Dentística', 'Dentistica', 'Estética', 'Estetica',
        'Instrumental', 'Instrumentos', 'Equipamento', 'Radiologia',
        'Prevenção', 'Prevencao', 'Profilaxia', 'Higiene', 'Pediatria',
        'Brocas', 'Broca', 'Laboratorial', 'Consultório', 'Consultorio',
        'Harmonização', 'Harmonizacao', 'Orofacial', 'Mobiliário', 'Mobiliario',
        'Papelaria', 'Vestuário', 'Vestuario', 'Utilidades', 'Decoração', 'Decoracao',
        'Peças De Mão', 'Pecas De Mao', 'Periférico', 'Periferico',
        'Saneante', 'Limpeza', 'Digital', 'Surya Dental', 'Promocional', 'Promocoes'
    ]
    
    # Filtrar categorias válidas
    categorias_filtradas = []
    for cat in todas_categorias:
        # Verificar se contém alguma keyword de categoria válida
        if any(keyword.lower() in cat.lower() for keyword in categorias_validas_keywords):
            categorias_filtradas.append(cat)
    
    # Se não encontrou nenhuma, retornar as que têm mais de 10 caracteres
    # (marcas geralmente são mais curtas)
    if not categorias_filtradas:
        categorias_filtradas = [c for c in todas_categorias if len(c) > 10]
    
    return sorted(set(categorias_filtradas))


def carregar_grupos_mestre(limite: int = 100, categoria: str = None) -> pd.DataFrame:
    """Carrega grupos mestre da API com filtro opcional de categoria"""
    try:
        params = {"tamanho": limite, "pagina": 1}
        
        # Adicionar filtro de categoria se fornecido
        if categoria and categoria != "Todas":
            params["categoria"] = categoria
        
        response = requests.get(
            f"{API_BASE_URL}/produtos-mestre/",  # Adicionar barra final
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        grupos = data.get("dados", [])
        
        if not grupos:
            return pd.DataFrame()
        
        # Converter para DataFrame
        df = pd.DataFrame(grupos)
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar grupos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)  # Cache sem mostrar spinner
def carregar_produtos_do_grupo(grupo_id: int) -> pd.DataFrame:
    """Carrega produtos de um grupo específico via API com cache"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/produtos-mestre/{grupo_id}/produtos",
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        produtos = data.get("produtos", [])
        
        if not produtos:
            return pd.DataFrame()
        
        return pd.DataFrame(produtos)
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar produtos do grupo: {e}")
        return pd.DataFrame()


def salvar_feedback_api(grupo_id: int, e_valido: bool, observacao: str = "", tipo: str = "validacao", 
                       total_produtos: int = 0, produtos_corretos: int = 0, 
                       falsos_positivos_lista: list = None) -> bool:
    """
    Salva feedback via API com campos melhorados
    
    Args:
        grupo_id: ID do grupo produtos_mestre
        e_valido: True=SIM (todos válidos), False=NÃO/PARCIAL
        observacao: Observações, sinônimos, exclusões
        tipo: Tipo do feedback (validacao, parcial, automatico, manual)
        total_produtos: Total de produtos no grupo
        produtos_corretos: Quantidade de produtos válidos
        falsos_positivos_lista: Lista de dicts com produtos falsos positivos
    """
    try:
        # Preparar dados dos falsos positivos
        falsos_positivos_json = None
        if falsos_positivos_lista and len(falsos_positivos_lista) > 0:
            falsos_positivos_json = json.dumps(falsos_positivos_lista, ensure_ascii=False)
            tipo = "parcial"  # Forçar tipo parcial se houver falsos positivos
        
        # Calcular produtos corretos se não fornecido
        if falsos_positivos_lista and produtos_corretos == 0:
            produtos_corretos = total_produtos - len(falsos_positivos_lista)
        
        # Payload conforme schema melhorado da API: FeedbackCreate
        payload = {
            "match_id": int(grupo_id),
            "tipo_feedback": str(tipo),
            "is_correto": bool(e_valido),
            "observacoes": str(observacao) if observacao else "",
            "total_produtos": int(total_produtos) if total_produtos > 0 else None,
            "produtos_corretos": int(produtos_corretos) if produtos_corretos > 0 else None,
            "falsos_positivos": falsos_positivos_json,
            "usuario": "interface_validacao",
            "origem": "interface_validacao_api",
            "confianca": None,
            "padroes_detectados": None
        }
        
        response = requests.post(
            f"{API_BASE_URL}/feedbacks/",  # Adicionar barra final
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True
        
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP ao salvar feedback: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        st.error(f"Erro ao salvar feedback: {e}")
        return False


@st.cache_data(ttl=30, show_spinner=False)  # Cache sem mostrar spinner
def carregar_feedbacks() -> List[Dict]:
    """Carrega feedbacks salvos via API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/feedbacks/", 
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("dados", [])
        
    except Exception as e:
        st.error(f"Erro ao carregar feedbacks: {e}")
        return []


def obter_estatisticas_api() -> Dict:
    """Obtém estatísticas gerais via API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/produtos-mestre/estatisticas",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        st.error(f"❌ Erro ao obter estatísticas: {e}")
        return {}


# ============================================================================
# FUNÇÕES DE ANÁLISE
# ============================================================================

def produtos_sao_similares(nome1: str, nome2: str) -> bool:
    """Verifica se dois produtos têm nomes similares."""
    # Normaliza os nomes para comparação
    norm1 = nome1.lower().strip()
    norm2 = nome2.lower().strip()
    
    # Calcula a similaridade simples baseada em palavras comuns
    palavras1 = set(norm1.split())
    palavras2 = set(norm2.split())
    
    # Se há muitas palavras em comum, são similares
    palavras_comuns = len(palavras1.intersection(palavras2))
    total_palavras = max(len(palavras1), len(palavras2))
    
    similaridade = palavras_comuns / total_palavras if total_palavras > 0 else 0
    return similaridade > 0.7  # 70% de similaridade


def analisar_produtos_grupo(produtos_df: pd.DataFrame) -> Dict:
    """Analisa produtos de um grupo e identifica similaridades"""
    if produtos_df.empty:
        return {
            "grupos_similares": [],
            "produtos_isolados": [],
            "total_grupos": 0,
            "total_isolados": 0
        }
    
    produtos_similares = {}
    
    for idx, produto in produtos_df.iterrows():
        nome_produto = produto['nome'] if 'nome' in produto else ''
        nome_base = nome_produto.lower()
        
        # Busca produtos similares
        encontrou_similar = False
        for chave, grupo in produtos_similares.items():
            if produtos_sao_similares(nome_base, chave):
                grupo.append((idx, produto))
                encontrou_similar = True
                break
        
        if not encontrou_similar:
            produtos_similares[nome_base] = [(idx, produto)]
    
    # Separa em grupos e isolados
    grupos_similares = [g for g in produtos_similares.values() if len(g) > 1]
    produtos_isolados = [g[0] for g in produtos_similares.values() if len(g) == 1]
    
    return {
        "grupos_similares": grupos_similares,
        "produtos_isolados": produtos_isolados,
        "total_grupos": len(grupos_similares),
        "total_isolados": len(produtos_isolados),
        "produtos_similares_dict": produtos_similares
    }


# ============================================================================
# FUNÇÕES DE INTERFACE
# ============================================================================

def exibir_header():
    """Exibe o header simplificado"""
    st.markdown("""
    <div style='padding: 20px 0 10px 0;'>
        <h1 style='margin: 0; color: #667eea;'>Match produtos</h1>
        <p style='margin: 5px 0 0 0; color: #666; font-size: 1.1em;'>
            Sistema de Validação dos Produtos 
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")


def exibir_estatisticas_feedback(feedbacks: List[Dict]):
    """Exibe estatísticas do feedback"""
    if not feedbacks:
        st.info("Nenhum feedback registrado ainda")
        return
    
    # Contar por tipo de validação (corrigir campos da API)
    total = len(feedbacks)
    validos = sum(1 for f in feedbacks if f.get("is_correto") == True and f.get("tipo_feedback") in ["validacao", "parcial"])
    invalidos = sum(1 for f in feedbacks if f.get("is_correto") == False and f.get("tipo_feedback") in ["validacao", "parcial"])
    
    # Calcular precisão
    precisao = (validos / total * 100) if total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{total}</h3>
            <p>Total Avaliados</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{validos}</h3>
            <p>Válidos</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{invalidos}</h3>
            <p>❌ Falsos Positivos</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{precisao:.1f}%</h3>
            <p>Precisão</p>
        </div>
        """, unsafe_allow_html=True)


def exibir_analise_similaridade(analise: Dict, produtos_df: pd.DataFrame):
    """Exibe análise de similaridade dos produtos"""
    st.markdown("**Análise de Similaridade:**")
    
    grupos_similares = analise["grupos_similares"]
    produtos_isolados = analise["produtos_isolados"]
    
    # Exibe grupos similares
    for grupo_idx, produtos_grupo in enumerate(grupos_similares, 1):
        if len(produtos_grupo) > 1:
            st.markdown(f"**Grupo {grupo_idx} - Produtos Similares ({len(produtos_grupo)} itens):**")
            
            # Verifica embalagens diferentes
            try:
                embalagens = set()
                for _, prod in produtos_grupo:
                    if 'embalagem' in prod:
                        embalagens.add(str(prod['embalagem'] if 'embalagem' in prod else ''))
                
                if len(embalagens) > 1:
                    st.markdown("**Atenção**: Produtos com embalagens diferentes detectadas")
            except:
                pass
            
            for idx, produto in produtos_grupo:
                nome = produto['nome'] if 'nome' in produto else 'N/A'
                site = produto['site'] if 'site' in produto else 'N/A'
                preco = produto['preco'] if 'preco' in produto else 0
                embalagem = produto['embalagem'] if 'embalagem' in produto else 'N/A'
                url = produto['url'] if 'url' in produto else ''
                
                # Criar link clicável
                link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Ver produto</a>' if url else 'Sem link'
                
                st.markdown(f"""
                <div class="produto-item">
                    <strong>{site}</strong>: {nome}<br>
                    <small>R$ {preco:.2f} | EMBALAGEM: {embalagem} | 🔗 {link_html}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # Exibe produtos isolados
    if produtos_isolados:
        st.markdown(f"**❓ Produtos Isolados ({len(produtos_isolados)}):**")
        for idx, produto in produtos_isolados:
            nome = produto['nome'] if 'nome' in produto else 'N/A'
            site = produto['site'] if 'site' in produto else 'N/A'
            preco = produto['preco'] if 'preco' in produto else 0
            embalagem = produto['embalagem'] if 'embalagem' in produto else 'N/A'
            url = produto['url'] if 'url' in produto else ''
            
            # Criar link clicável
            link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">Ver produto</a>' if url else 'Sem link'
            
            st.markdown(f"""
            <div class="produto-item" style="border-left-color: orange;">
                <strong>{site}</strong>: {nome}<br>
                <small> R$ {preco:.2f} | EMBALAGEM: {embalagem} | 🔗 {link_html}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Resumo da análise
    total_grupos = len(grupos_similares)
    total_isolados = len(produtos_isolados)
    
    if total_grupos > 0 and total_isolados > 0:
        st.warning(f"**Match Parcial Detectado:** {total_grupos} grupo(s) de produtos similares + {total_isolados} produto(s) isolado(s)")
    elif total_grupos > 1:
        st.warning(f"**Múltiplos Grupos:** {total_grupos} grupos diferentes de produtos")
    elif total_grupos == 1 and total_isolados == 0:
        st.success(f"**Match Válido:** Todos os produtos são similares")
    else:
        st.error(f"**Match Inválido:** Produtos são muito diferentes")


# ============================================================================
# PÁGINAS DA INTERFACE
# ============================================================================

def pagina_validacao_grupos():
    """Página principal de validação de grupos"""
    st.subheader("Validação de Grupos Existentes")
    
    # Inicializar cache
    cache = get_cache_instance(API_BASE_URL)
    
    # Filtros
    st.sidebar.subheader("Filtros")
    limite_grupos = st.sidebar.slider("Quantidade de grupos", 10, 200, 100)
    min_produtos = st.sidebar.slider("Mínimo de produtos no grupo", 2, 10, 2)
    
    # Filtro de categoria
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Filtrar por Categoria**")
    
    
    # Carregar categorias disponíveis
    categorias = carregar_categorias_disponiveis()
    
    if categorias:
        # Adicionar opção "Todas" no início
        opcoes_categorias = ["Todas"] + sorted(categorias)
        categoria_selecionada = st.sidebar.selectbox(
            "Selecione a categoria:",
            opcoes_categorias,
            index=0,
            help="Filtre grupos por categoria específica"
        )
        
        # Mostrar contador de categorias
        if st.sidebar.checkbox("Ver estatísticas por categoria", value=False):
            with st.sidebar.expander("Grupos por Categoria", expanded=True):
                # Carregar todos os grupos para contar por categoria
                todos_grupos = carregar_grupos_mestre(limite=1000, categoria=None)
                if not todos_grupos.empty and 'categoria' in todos_grupos.columns:
                    contagem = todos_grupos['categoria'].value_counts()
                    for cat, count in contagem.head(10).items():
                        st.sidebar.text(f"• {cat}: {count}")
                    if len(contagem) > 10:
                        st.sidebar.text(f"... e mais {len(contagem) - 10} categorias")
    else:
        categoria_selecionada = "Todas"
        st.sidebar.info("Carregando categorias...")
    
    # Obter estatísticas do cache (sem exibir na sidebar)
    stats = cache.get_estatisticas()
    
    # Botão de sincronização (apenas se houver pendentes)
    if stats['feedbacks_pendentes'] > 0:
        st.sidebar.markdown("---")
        st.sidebar.warning(f"{stats['feedbacks_pendentes']} feedbacks pendentes")
        if st.sidebar.button("Sincronizar Agora", use_container_width=True):
            salvos = cache.sincronizar_agora()
            if salvos > 0:
                st.sidebar.success(f"{salvos} feedbacks sincronizados!")
                st.rerun()
    
    # Botão para carregar novo lote
    st.sidebar.markdown("---")
    if st.sidebar.button("Atualizar Lista", use_container_width=True, help="Carrega novos 50 grupos"):
        with st.spinner("Preparando ambiente de validação..."):
            if cache.carregar_lote(categoria_selecionada, forcar_reload=True):
                st.sidebar.success("Lista atualizada!")
                st.rerun()
            else:
                st.sidebar.error("Não há mais grupos para carregar")
    
    # Carregar lote inicial se necessário
    if not st.session_state.cache_produtos:
        with st.spinner("Preparando ambiente de validação..."):
            if not cache.carregar_lote(categoria_selecionada):
                st.error("Não foi possível carregar grupos!")
                return
    
    # Obter grupo atual do cache
    grupo_dict = cache.get_produto_atual()
    
    if not grupo_dict:
        st.info("Todos os grupos deste lote foram validados!")
        st.info("Clique em 'Atualizar Lista' na barra lateral para continuar")
        return
    
    # Converter dict para Series para manter compatibilidade com código existente
    grupo = pd.Series(grupo_dict)
    grupo_id = grupo['id']
    
    # Carrega feedbacks para estatísticas (mantido do código original)
    # Carrega feedbacks para estatísticas (mantido do código original)
    feedbacks = carregar_feedbacks()
    
    # Mostra progresso usando estatísticas do cache
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Posição no Lote", stats['progresso_cache'])
    with col2:
        st.metric("Total Validados", stats['total_validados'])
    with col3:
        st.metric("Pendentes", stats['feedbacks_pendentes'])
    
    st.markdown("---")
    
    # Pega grupo atual do cache (já definido acima)
    # grupo e grupo_id já estão definidos
    
    # Exibe grupo
    with st.container():
        st.markdown(f'<div class="match-card">', unsafe_allow_html=True)
        
        # Header do grupo
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            nome_produto = grupo['nome_produto'] if 'nome_produto' in grupo else 'N/A'
            st.markdown(f"**ID {grupo_id}**: {nome_produto}")
        with col2:
            categoria_grupo = grupo.get('categoria', 'N/A')
            st.markdown(f"**Categoria:**")
            st.markdown(f"<div style='background: #e3f2fd; padding: 5px; border-radius: 5px; text-align: center;'><strong>{categoria_grupo}</strong></div>", unsafe_allow_html=True)
        with col3:
            total_produtos = grupo['total_produtos'] if 'total_produtos' in grupo else 0
            st.metric("Produtos", total_produtos)
        with col4:
            total_sites = grupo['total_sites'] if 'total_sites' in grupo else 0
            st.metric("Sites", total_sites)
        
        # Categoria e marca
        col1, col2 = st.columns(2)
        with col1:
            categoria = grupo['categoria'] if 'categoria' in grupo else 'N/A'
            st.write(f"**Categoria**: {categoria}")
        with col2:
            marca = grupo['marca'] if 'marca' in grupo else 'N/A'
            st.write(f"**Marca**: {marca}")
        
        # Carrega produtos do grupo
        produtos_df = carregar_produtos_do_grupo(grupo_id)
        
        if not produtos_df.empty:
            st.markdown("**Produtos no Grupo:**")
            
            # Análise de similaridade
            analise = analisar_produtos_grupo(produtos_df)
            exibir_analise_similaridade(analise, produtos_df)
        
        st.markdown("---")
        
        # Seção de avaliação
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("**Avaliação do Grupo:**")
            
            # Radio button para validação
            validacao = st.radio(
                "Este é um grupo válido?",
                ["SIM - Produtos similares", "PARCIAL - Maioria similar", "NÃO - Falso positivo"],
                key=f"radio_{grupo_id}"
            )
            
            # Se selecionou PARCIAL, mostra checkboxes para marcar falsos positivos
            produtos_falsos_positivos = []
            if validacao.startswith("PARCIAL"):
                st.markdown("**Marque os produtos que são FALSOS POSITIVOS:**")
                st.markdown('<div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">'
                           '<small>Selecione apenas os produtos que <strong>NÃO pertencem</strong> ao grupo</small></div>', 
                           unsafe_allow_html=True)
                
                for i, produto in enumerate(produtos_df.to_dict('records')):
                    nome_curto = produto['nome'][:60] + "..." if len(produto['nome']) > 60 else produto['nome']
                    site = produto['site'] if 'site' in produto else 'N/A'
                    
                    if st.checkbox(
                        f"**{site}:** {nome_curto}",
                        key=f"fp_{grupo_id}_{i}"
                    ):
                        produtos_falsos_positivos.append({
                            'id': int(produto['id']),  # Converter para int nativo Python
                            'nome': str(produto['nome']),
                            'site': str(site)
                        })
            
            # Formulário de observações
            with st.form(f"form_{grupo_id}"):
                st.markdown("**Orientações para feedback efetivo:**")
                st.markdown("""
                - **SIM:** Todos os produtos são realmente similares
                - **PARCIAL:** Maioria similar + alguns falsos positivos
                - **NÃO:** Produtos são completamente diferentes
                - **Sinônimos:** `resina = composite`, `anestésico é lidocaína`
                - **Exclusões:** `ortodontia != endodontia`
                """)
                
                observacao = st.text_area(
                    "Observações e sugestões de sinônimos/exclusões:",
                    key=f"obs_{grupo_id}",
                    height=150
                )
                
                submitted = st.form_submit_button("Salvar e Ir para Próximo", type="primary")
                
                if submitted:
                    # Processa validação
                    if validacao.startswith("SIM"):
                        e_valido = True
                        tipo_feedback = "validacao"
                    elif validacao.startswith("PARCIAL"):
                        e_valido = False
                        tipo_feedback = "parcial"
                    else:
                        e_valido = False
                        tipo_feedback = "validacao"
                    
                    # Adicionar informação sobre falsos positivos no texto se houver
                    obs_final = observacao
                    if produtos_falsos_positivos and len(produtos_falsos_positivos) > 0:
                        if obs_final:
                            obs_final += f"\n\n[FALSOS POSITIVOS: {len(produtos_falsos_positivos)} produtos marcados]"
                        else:
                            obs_final = f"[FALSOS POSITIVOS: {len(produtos_falsos_positivos)} produtos marcados]"
                    
                    # Salvar feedback usando cache (com auto-save)
                    total_prods = len(produtos_df)
                    prods_corretos = total_prods - len(produtos_falsos_positivos) if produtos_falsos_positivos else total_prods
                    
                    # Extrair IDs dos falsos positivos
                    ids_falsos_positivos = [p['id'] for p in produtos_falsos_positivos] if produtos_falsos_positivos else []
                    
                    # Adicionar feedback usando cache (salva automaticamente)
                    # Incluir informações do usuário logado
                    cache.adicionar_feedback(
                        grupo_id=grupo_id,
                        e_valido=e_valido,
                        observacao=obs_final,
                        total_produtos=total_prods,
                        produtos_corretos=prods_corretos,
                        falsos_positivos=ids_falsos_positivos,
                        usuario=get_username(),
                        usuario_role=get_user_role()
                    )
                    
                    # Mostrar mensagem apropriada baseada no role
                    if is_ajudante() and not e_valido:
                        st.warning("Validação enviada!")
                    
                    # Avançar para próximo
                    cache.proximo_produto()
                    st.rerun()
            
            # Botões de navegação fora do form (conforme imagem)
            st.markdown("---")
            col_nav1, col_nav2 = st.columns(2)
            
            with col_nav1:
                if st.button("Atualizar Lista", use_container_width=True, help="Recarrega a lista de grupos"):
                    with st.spinner("Preparando ambiente de validação..."):
                        if cache.carregar_lote(categoria_selecionada, forcar_reload=True):
                            st.success("Lista atualizada!")
                            st.rerun()
            
            with col_nav2:
                if st.button("Pular este grupo", use_container_width=True, help="Pula para o próximo sem salvar"):
                    produto = cache.proximo_produto()
                    if produto:
                        st.rerun()
                    else:
                        st.warning("Não há mais grupos!")
        
        with col2:
            st.markdown("**Orientações Detalhadas:**")
            st.markdown("""
            #### Para criar SINÔNIMOS:
            Use quando produtos têm nomes diferentes mas são similares:
            ```
            resina = composite
            anestésico é lidocaína  
            fresa = broca = cortador
            ortodontia mesmo que aparelho
            ```
            
            #### Para criar EXCLUSÕES:
            Use quando produtos foram agrupados incorretamente:
            ```
            anestésico != resina
            ortodontia diferente de endodontia
            broca não é disco
            categorias diferentes
            ```
            
            #### Exemplo prático:
            - **Match correto:** "resina = composite"
            - **Match incorreto:** "anestésico != resina"
            - **Múltiplos nomes:** "fresa = broca = cortador"
            """)
            
            st.info("**Dica:** Escreva seus sinônimos e exclusões no campo de observações à esquerda usando estes padrões!")
        
        st.markdown('</div>', unsafe_allow_html=True)


def pagina_estatisticas():
    """Página de estatísticas do sistema"""
    st.subheader("Estatísticas do Sistema")
    
    # Carrega estatísticas
    stats_response = obter_estatisticas_api()
    feedbacks = carregar_feedbacks()
    
    if not stats_response:
        st.error("Erro ao carregar estatísticas")
        return
    
    # A API retorna {"estatisticas": {...}, "gerado_em": "..."}
    stats = stats_response.get("estatisticas", {})
    
    # Estatísticas gerais
    st.markdown("### Estatísticas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{stats.get('total_grupos', 0)}</h3>
            <p>Grupos Totais</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{stats.get('total_produtos', 0)}</h3>
            <p>Produtos Agrupados</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_produtos = stats.get('media_produtos_por_grupo', 0)
        st.markdown(f"""
        <div class="stats-box">
            <h3>{avg_produtos:.1f}</h3>
            <p>Média por Grupo</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stats-box">
            <h3>{stats.get('total_sites', 0)}</h3>
            <p>Sites Diferentes</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Estatísticas de feedback
    st.markdown("### Estatísticas de Feedback")
    exibir_estatisticas_feedback(feedbacks)
    
    st.markdown("---")
    
    # Histórico de avaliações
    if feedbacks:
        st.markdown("### Histórico de Avaliações")
        
        # Criar DataFrame com os campos corretos
        historico = []
        for f in feedbacks:
            # Formatar data
            data_criacao = f.get("criado_em", "N/A")
            if data_criacao != "N/A" and "T" in data_criacao:
                data_criacao = data_criacao.replace("T", " ")[:19]
            
            # Formatar observação
            obs = f.get("observacoes", "")
            obs_curta = obs[:80] + "..." if len(obs) > 80 else obs
            
            # Determinar status
            is_correto = f.get("is_correto")
            if is_correto:
                status = "Sim"
            else:
                status = "Não"
            
            historico.append({
                "ID": f.get("match_id"),
                "Válido": status,
                "Tipo": f.get("tipo_feedback", "N/A").title(),
                "Produtos": f.get("total_produtos", "?"),
                "Data": data_criacao,
                "Observação": obs_curta
            })
        
        df_feedback = pd.DataFrame(historico)
        st.dataframe(df_feedback, use_container_width=True)
    else:
        st.info("Nenhuma avaliação registrada ainda. Comece validando alguns grupos!")


def pagina_revisar_quarentena():
    """Página para administradores revisarem feedbacks em quarentena"""
    st.subheader("Revisar Validações em Quarentena")
    
    st.info("**Quarentena:** Validações parciais ou negativas feitas por dentistas que precisam de aprovação.")
    
    # Carregar feedbacks em quarentena
    try:
        response = requests.get(f"{API_BASE_URL}/feedbacks/", timeout=10)
        response.raise_for_status()
        data = response.json()
        todos_feedbacks = data.get("dados", [])
        
        # Filtrar apenas os em quarentena
        feedbacks_quarentena = [f for f in todos_feedbacks if f.get("tipo_feedback") == "quarentena"]
        
        if not feedbacks_quarentena:
            st.success("Não há validações pendentes de revisão!")
            return
        
        st.warning(f"{len(feedbacks_quarentena)} validações aguardando revisão")
        
        # Exibir cada feedback em quarentena
        for idx, feedback in enumerate(feedbacks_quarentena):
            grupo_id = feedback.get('match_id')
            
            with st.expander(f"Grupo #{grupo_id} - Por {feedback.get('usuario', 'N/A')}", expanded=(idx == 0)):
                
                # Carregar informações do grupo
                try:
                    grupo_response = requests.get(f"{API_BASE_URL}/produtos-mestre/{grupo_id}", timeout=5)
                    if grupo_response.status_code == 200:
                        grupo_info = grupo_response.json()
                        
                        # Header do grupo
                        col_h1, col_h2, col_h3 = st.columns(3)
                        with col_h1:
                            st.markdown(f"**Produto:** {grupo_info.get('nome_produto', 'N/A')}")
                        with col_h2:
                            st.markdown(f"**Marca:** {grupo_info.get('marca', 'N/A')}")
                        with col_h3:
                            st.markdown(f"**Categoria:** {grupo_info.get('categoria', 'N/A')}")
                except:
                    pass
                
                st.markdown("---")
                
                # Carregar e exibir produtos do grupo
                produtos_df = carregar_produtos_do_grupo(grupo_id)
                
                if not produtos_df.empty:
                    st.markdown("**Produtos no Grupo:**")
                    
                    for idx_prod, row in produtos_df.iterrows():
                        nome = row.get('nome', 'N/A')
                        site = row.get('site', 'N/A')
                        preco = row.get('preco_normal', 0) if 'preco_normal' in row else row.get('preco', 0)
                        marca = row.get('marca', 'N/A')
                        categoria = row.get('categoria', 'N/A')
                        url = row.get('url', '')
                        
                        # Criar link clicável
                        link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: none;">🔗 Ver produto</a>' if url else ''
                        
                        st.markdown(f"""
                        <div class="produto-item">
                            <strong>{site}</strong>: {nome}<br>
                            <small>R$ {preco:.2f} | Marca: {marca} | Categoria: {categoria}</small>
                            {' | ' + link_html if link_html else ''}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("Não foi possível carregar os produtos do grupo")
                
                st.markdown("---")
                
                # Informações da validação do dentista
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Observações do Dentista:**")
                    obs = feedback.get('observacoes', 'Sem observações')
                    st.write(obs if obs else 'Sem observações')
                
                with col2:
                    st.metric("Produtos Totais", feedback.get('total_produtos', 0))
                
                with col3:
                    st.metric("Produtos Corretos", feedback.get('produtos_corretos', 0))
                
                # Falsos positivos marcados
                falsos_positivos = feedback.get('falsos_positivos', '[]')
                if falsos_positivos and falsos_positivos != '[]':
                    try:
                        fps = json.loads(falsos_positivos) if isinstance(falsos_positivos, str) else falsos_positivos
                        if fps:
                            st.warning(f"Dentista marcou {len(fps)} produto(s) como falso positivo")
                    except:
                        pass
                
                # Botões de ação
                st.markdown("---")
                col_btn1, col_btn2, col_btn_spacer = st.columns([1, 1, 1])
                
                with col_btn1:
                    if st.button("Aprovar", key=f"aprovar_{feedback.get('id')}", use_container_width=True, type="primary"):
                        # Atualizar feedback para validacao (aprovar)
                        try:
                            update_response = requests.put(
                                f"{API_BASE_URL}/feedbacks/{feedback.get('id')}",
                                json={"tipo_feedback": "validacao"},
                                timeout=5
                            )
                            if update_response.status_code == 200:
                                st.success("Validação aprovada!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao aprovar: {e}")
                
                with col_btn2:
                    if st.button("Rejeitar", key=f"rejeitar_{feedback.get('id')}", use_container_width=True):
                        # Deletar feedback (rejeitar)
                        try:
                            delete_response = requests.delete(
                                f"{API_BASE_URL}/feedbacks/{feedback.get('id')}",
                                timeout=5
                            )
                            if delete_response.status_code in [200, 204]:
                                st.warning("Validação rejeitada!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao rejeitar: {e}")
        
    except Exception as e:
        st.error(f"Erro ao carregar feedbacks em quarentena: {e}")


# ============================================================================
# PÁGINA: EXECUTAR MATCHING
# ============================================================================

def pagina_executar_matching():
    """Página para executar matching com feedback aplicado"""
    
    st.title("🔄 Executar Matching")
    st.markdown("---")
    
    # Informações
    st.info("""
    **Como funciona:**
    1. O sistema processa os feedbacks salvos na interface
    2. Gera regras determinísticas (filtros e sinônimos)
    3. Re-executa o matching aplicando essas regras
    4. Novos matches são salvos no banco principal
    """)
    
    # Tabs para diferentes ações
    tab1, tab2, tab3 = st.tabs(["⚡ Executar", "📊 Status", "📖 Instruções"])
    
    with tab1:
        st.subheader("Executar Re-matching")
        
        col1, col2 = st.columns(2)
        
        with col1:
            aplicar_feedback = st.checkbox(
                "Aplicar feedback humano",
                value=True,
                help="Se marcado, aplica regras aprendidas dos feedbacks"
            )
        
        with col2:
            modo_execucao = st.selectbox(
                "Modo de execução",
                ["Completo", "Apenas processar feedback", "Comparar antes/depois"],
                help="Escolha o tipo de execução desejado"
            )
        
        st.markdown("---")
        
        # Botão executar
        if st.button("🚀 Executar Matching", type="primary", use_container_width=True):
            
            # Cria instância do sistema
            with st.spinner("Inicializando sistema..."):
                try:
                    sistema = MatchingComFeedback(
                        db_mestre="match_crew.db",
                        db_tratados="match_crew.db"
                    )
                    st.success("✅ Sistema inicializado!")
                except Exception as e:
                    st.error(f"❌ Erro ao inicializar: {e}")
                    st.stop()
            
            # Executa conforme modo selecionado
            if modo_execucao == "Apenas processar feedback":
                with st.spinner("Processando feedback..."):
                    stats = sistema.processar_feedback_existente()
                    
                    st.success("✅ Feedback processado!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Feedbacks", stats.get('feedbacks_processados', 0))
                    with col2:
                        st.metric("Filtros", stats.get('filtros_adicionados', 0))
                    with col3:
                        st.metric("Sinônimos", stats.get('sinonimos_adicionados', 0))
                    with col4:
                        st.metric("Regras Totais", stats.get('regras_geradas', 0))
            
            elif modo_execucao == "Completo":
                # Processa feedback primeiro
                with st.spinner("1/2 - Processando feedback..."):
                    stats_feedback = sistema.processar_feedback_existente()
                    st.success(f"✅ {stats_feedback.get('regras_geradas', 0)} regras geradas")
                
                # Executa matching
                with st.spinner("2/2 - Executando matching... (pode levar alguns segundos)"):
                    resultado = sistema.executar_matching_completo(aplicar_feedback=aplicar_feedback)
                    
                    if resultado.get("sucesso"):
                        st.success("✅ Matching concluído com sucesso!")
                        
                        # Métricas
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Tempo", f"{resultado.get('tempo_execucao', 0):.2f}s")
                        with col2:
                            st.metric("Matches", f"{resultado.get('matches_criados', 0):,}")
                        with col3:
                            st.metric("Adequação", f"{resultado.get('adequacao', 0):.1f}%")
                        with col4:
                            feedback_icon = "✅" if resultado.get('feedback_aplicado') else "⚠️"
                            st.metric("Feedback", f"{feedback_icon} {resultado.get('filtros_usados', 0)} regras")
                        
                        # Detalhes
                        with st.expander("📋 Detalhes da Execução"):
                            st.json(resultado)
                    else:
                        st.error(f"❌ Erro: {resultado.get('erro', 'Erro desconhecido')}")
            
            elif modo_execucao == "Comparar antes/depois":
                st.warning("⚠️ Esta operação executa o matching DUAS vezes e pode levar alguns minutos!")
                
                if st.button("Confirmar comparação", type="secondary"):
                    with st.spinner("Executando comparação... aguarde..."):
                        comparacao = sistema.comparar_antes_depois()
                        
                        if "erro" not in comparacao:
                            st.success("✅ Comparação concluída!")
                            
                            # Métricas de comparação
                            st.subheader("📊 Resultados da Comparação")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric(
                                    "Matches SEM feedback",
                                    f"{comparacao['matches_antes']:,}",
                                    help="Total de matches sem aplicar regras"
                                )
                            with col2:
                                st.metric(
                                    "Matches COM feedback",
                                    f"{comparacao['matches_depois']:,}",
                                    delta=f"{comparacao['diferenca']:+,}",
                                    help="Total de matches aplicando regras aprendidas"
                                )
                            with col3:
                                st.metric(
                                    "Melhoria",
                                    f"{comparacao['percentual_melhoria']:+.1f}%",
                                    help="Percentual de melhoria"
                                )
                            
                            # Gráfico visual (opcional)
                            st.markdown("---")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Adequação ANTES", f"{comparacao['adequacao_antes']:.1f}%")
                            with col2:
                                st.metric("Adequação DEPOIS", f"{comparacao['adequacao_depois']:.1f}%")
                            
                            # Regras aplicadas
                            st.markdown("---")
                            st.subheader("🔧 Regras Aplicadas")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Filtros de Exclusão", comparacao['regras_aplicadas']['filtros'])
                            with col2:
                                st.metric("Sinônimos", comparacao['regras_aplicadas']['sinonimos'])
                        else:
                            st.error(f"❌ Erro na comparação: {comparacao.get('erro')}")
    
    with tab2:
        st.subheader("Status do Sistema")
        
        try:
            # Carrega estatísticas atuais
            sistema_temp = MatchingComFeedback()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔧 Regras Aprendidas**")
                st.metric("Filtros de Exclusão", len(sistema_temp.aplicador_feedback.filtros_exclusao))
                st.metric("Sinônimos", len(sistema_temp.aplicador_feedback.sinonimos_aprendidos))
            
            with col2:
                st.markdown("**📦 Banco de Dados**")
                st.info(f"Principal: `{sistema_temp.db_mestre}`")
                st.info(f"Tratados: `{sistema_temp.db_tratados}`")
            
            # Listar feedbacks pendentes
            st.markdown("---")
            st.subheader("📋 Feedbacks Disponíveis")
            
            feedbacks = carregar_feedbacks()
            if feedbacks:
                st.success(f"✅ {len(feedbacks)} feedbacks salvos")
                
                # Contar por tipo
                tipos = {}
                for fb in feedbacks:
                    tipo = fb.get('tipo_feedback', 'desconhecido')
                    tipos[tipo] = tipos.get(tipo, 0) + 1
                
                st.write("Distribuição por tipo:")
                for tipo, count in tipos.items():
                    st.write(f"- {tipo}: {count}")
            else:
                st.warning("⚠️ Nenhum feedback encontrado")
                st.info("Valide alguns matches primeiro na página 'Validar Grupos'")
        
        except Exception as e:
            st.error(f"Erro ao carregar status: {e}")
    
    with tab3:
        st.subheader("📖 Como Usar")
        
        st.markdown("""
        ### Passo a Passo
        
        1. **Valide Matches**
           - Vá para a página "Validar Grupos"
           - Revise os matches propostos
           - Marque como válidos ou inválidos
           - Adicione observações e sinônimos
        
        2. **Processe Feedback**
           - Volte para esta página
           - Selecione "Apenas processar feedback"
           - Clique em "Executar Matching"
           - O sistema irá gerar regras determinísticas
        
        3. **Execute Re-matching**
           - Selecione "Completo"
           - Marque "Aplicar feedback humano"
           - Clique em "Executar Matching"
           - Aguarde a conclusão
        
        4. **Valide Novos Matches**
           - Vá novamente para "Validar Grupos"
           - Revise os novos matches gerados
           - Repita o ciclo para melhorar continuamente
        
        ### Dicas
        
        - ✅ **Observações específicas** são mais úteis
        - ✅ Use padrões como "X = Y" para sinônimos
        - ✅ Use padrões como "X != Y" para exclusões
        - ✅ Execute comparações periodicamente para ver o progresso
        
        ### Exemplos de Observações
        
        **Para sinônimos:**
        - "resina = composite"
        - "anestésico é lidocaína"
        - "broca igual a fresa"
        
        **Para exclusões:**
        - "ortodontia != endodontia"
        - "resina diferente de anestésico"
        - "categorias incompatíveis"
        """)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal da interface"""
    
    # Verificar se usuário está logado
    if not is_logged_in():
        mostrar_tela_login()
        return
    
    # Header com logo
    exibir_header()
    
    # Verificar API
    if not verificar_api_disponivel():
        st.error("**API não está disponível!**")
        st.info("Certifique-se de que a API está rodando: `python start_api.py`")
        st.code(f"API URL: {API_BASE_URL}")
        st.stop()
    
    st.success("Conectado à API")
    
    # Logo na sidebar com espaçamento
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    logo_path = Path(__file__).parent / "logo_bid.jpg"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
    else:
        st.sidebar.markdown("### Match produtos")
    
    # Mostrar informações do usuário logado
    mostrar_info_usuario()
    
    st.sidebar.markdown("---")
    
    # Menu lateral (dinâmico baseado no role)
    st.sidebar.title("Menu")
    
    # Opções de menu baseadas no tipo de usuário
    opcoes_menu = ["Validar Grupos"]
    
    # Administradores tem acesso a Estatísticas, Matching e Quarentena
    if is_admin():
        opcoes_menu.append("Executar Matching")
        opcoes_menu.append("Revisar Quarentena")
        opcoes_menu.append("Estatísticas")
    
    pagina = st.sidebar.radio(
        "Escolha uma opção:",
        opcoes_menu
    )
    
    st.sidebar.write("---")
    
    # Renderizar página selecionada
    if pagina == "Validar Grupos":
        pagina_validacao_grupos()
    elif pagina == "Executar Matching" and is_admin():
        pagina_executar_matching()
    elif pagina == "Revisar Quarentena" and is_admin():
        pagina_revisar_quarentena()
    elif pagina == "Estatísticas" and is_admin():
        pagina_estatisticas()


if __name__ == "__main__":
    main()
