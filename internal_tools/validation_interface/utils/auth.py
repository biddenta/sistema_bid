import streamlit as st
from typing import Optional, Dict
import hashlib
import json
from pathlib import Path

# Tipos de usuário
ROLE_ADM = "administrador"
ROLE_AJUDANTE = "dentista"

# Arquivo de usuários (em produção, usar banco de dados)
USERS_FILE = Path(__file__).parent / "users.json"


def hash_password(password: str) -> str:
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()


def carregar_usuarios() -> Dict:
    """Carrega usuários do arquivo JSON"""
    if not USERS_FILE.exists():
        # Criar arquivo com usuários padrão
        usuarios_padrao = {
            "admin": {
                "senha_hash": hash_password("admin123"),
                "nome": "Administrador",
                "role": ROLE_ADM
            },
            "dentista": {
                "senha_hash": hash_password("dentista123"),
                "nome": "Dentista",
                "role": ROLE_AJUDANTE
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(usuarios_padrao, f, indent=2, ensure_ascii=False)
        return usuarios_padrao
    
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validar_login(username: str, password: str) -> Optional[Dict]:
    """
    Valida credenciais do usuário
    
    Returns:
        Dict com dados do usuário se válido, None caso contrário
    """
    usuarios = carregar_usuarios()
    
    if username not in usuarios:
        return None
    
    usuario = usuarios[username]
    senha_hash = hash_password(password)
    
    if senha_hash == usuario["senha_hash"]:
        return {
            "username": username,
            "nome": usuario["nome"],
            "role": usuario["role"]
        }
    
    return None


def fazer_login(username: str, password: str) -> bool:
    """
    Realiza login e armazena no session_state
    
    Returns:
        True se login bem-sucedido, False caso contrário
    """
    usuario = validar_login(username, password)
    
    if usuario:
        st.session_state.logged_in = True
        st.session_state.user_data = usuario
        return True
    
    return False


def fazer_logout():
    """Realiza logout limpando session_state"""
    if 'logged_in' in st.session_state:
        del st.session_state.logged_in
    if 'user_data' in st.session_state:
        del st.session_state.user_data
    
    # Limpar cache também
    if 'cache_produtos' in st.session_state:
        del st.session_state.cache_produtos


def is_logged_in() -> bool:
    """Verifica se usuário está logado"""
    return st.session_state.get('logged_in', False)


def get_user_data() -> Optional[Dict]:
    """Retorna dados do usuário logado"""
    return st.session_state.get('user_data', None)


def is_admin() -> bool:
    """Verifica se usuário logado é administrador"""
    user_data = get_user_data()
    return user_data and user_data.get('role') == ROLE_ADM


def is_ajudante() -> bool:
    """Verifica se usuário logado é dentista"""
    user_data = get_user_data()
    return user_data and user_data.get('role') == ROLE_AJUDANTE


def get_user_role() -> str:
    """Retorna role do usuário logado"""
    user_data = get_user_data()
    return user_data.get('role', '') if user_data else ''


def get_username() -> str:
    """Retorna username do usuário logado"""
    user_data = get_user_data()
    return user_data.get('username', '') if user_data else ''


def get_user_display_name() -> str:
    """Retorna nome de exibição do usuário logado"""
    user_data = get_user_data()
    return user_data.get('nome', 'Usuário') if user_data else 'Usuário'


def mostrar_tela_login():
    """
    Renderiza tela de login
    """
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Centralizar login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1>Sistema de Validação de Matches</h1>
            <p style="color: #666;">Faça login para continuar</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password:
                    st.error("Preencha todos os campos")
                elif fazer_login(username, password):
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")


def adicionar_usuario(username: str, password: str, nome: str, role: str) -> bool:
    usuarios = carregar_usuarios()
    
    if username in usuarios:
        return False
    
    usuarios[username] = {
        "senha_hash": hash_password(password),
        "nome": nome,
        "role": role
    }
    
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    return True


def mostrar_info_usuario():
    """Mostra informações do usuário logado na sidebar"""
    if is_logged_in():
        user_data = get_user_data()
        
        st.sidebar.markdown("---")
        
        role_display = "Administrador" if is_admin() else "Dentista"
        role_color = "#28a745" if is_admin() else "#07c5ff"
        
        st.sidebar.markdown(f"""
        <div style="background: {role_color}; color: white; padding: 5px 10px; 
                    border-radius: 5px; text-align: center; font-size: 0.9em; margin-bottom: 10px;">
            {role_display}
        </div>
        """, unsafe_allow_html=True)
        
        if st.sidebar.button("Sair", use_container_width=True):
            fazer_logout()
            st.rerun()
