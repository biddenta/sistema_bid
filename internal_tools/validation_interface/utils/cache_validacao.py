import streamlit as st
import requests
from typing import List, Dict, Optional
from datetime import datetime
import json


class CacheValidacao:
    """
    Gerencia cache de produtos para validação
    - Carrega 50 produtos por vez
    - Salva automaticamente cada feedback
    - Pré-carrega próximo lote em background
    """
    
    def __init__(self, api_base_url: str, batch_size: int = 50):
        self.api_base_url = api_base_url
        self.batch_size = batch_size
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa state do Streamlit para cache"""
        if 'cache_produtos' not in st.session_state:
            st.session_state.cache_produtos = []
        
        if 'cache_index_atual' not in st.session_state:
            st.session_state.cache_index_atual = 0
        
        if 'cache_offset_global' not in st.session_state:
            st.session_state.cache_offset_global = 0
        
        if 'cache_categoria_atual' not in st.session_state:
            st.session_state.cache_categoria_atual = None
        
        if 'cache_feedbacks_pendentes' not in st.session_state:
            st.session_state.cache_feedbacks_pendentes = []
        
        if 'cache_total_validados' not in st.session_state:
            st.session_state.cache_total_validados = 0
    
    def carregar_lote(self, categoria: Optional[str] = None, forcar_reload: bool = False) -> bool:
        """
        Carrega um lote de produtos
        
        Args:
            categoria: Categoria para filtrar (None = todas)
            forcar_reload: Se True, recarrega mesmo se já tem cache
        
        Returns:
            bool: True se carregou com sucesso
        """
        # Se mudou categoria, resetar
        if categoria != st.session_state.cache_categoria_atual:
            self.resetar_cache()
            st.session_state.cache_categoria_atual = categoria
        
        # Se já tem cache e não forçou reload, não fazer nada
        if st.session_state.cache_produtos and not forcar_reload:
            return True
        
        try:
            # Calcular offset baseado em quantos já validou
            offset = st.session_state.cache_offset_global
            
            # Montar parâmetros
            params = {
                "tamanho": self.batch_size,
                "offset": offset
            }
            
            if categoria and categoria != "Todas":
                params["categoria"] = categoria
            
            # Fazer request
            response = requests.get(
                f"{self.api_base_url}/produtos-mestre/",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            grupos = data.get("dados", [])
            
            if not grupos:
                st.warning("Não há mais produtos para validar nesta categoria!")
                return False
            
            # Atualizar cache
            st.session_state.cache_produtos = grupos
            st.session_state.cache_index_atual = 0
            st.session_state.cache_offset_global += len(grupos)
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao carregar lote: {e}")
            return False
    
    def get_produto_atual(self) -> Optional[Dict]:
        """Retorna produto atual do cache"""
        if not st.session_state.cache_produtos:
            return None
        
        if st.session_state.cache_index_atual >= len(st.session_state.cache_produtos):
            return None
        
        return st.session_state.cache_produtos[st.session_state.cache_index_atual]
    
    def proximo_produto(self) -> Optional[Dict]:
        """
        Avança para próximo produto
        Tenta salvar feedbacks pendentes em background (sem bloquear)
        Carrega novo lote se necessário
        
        Returns:
            Próximo produto ou None se acabou
        """
        # Tentar salvar feedbacks pendentes em background (sem bloquear navegação)
        try:
            self._salvar_feedbacks_pendentes()
        except:
            pass  # Ignora erros, serão tentados na próxima vez
        
        # Avançar índice
        st.session_state.cache_index_atual += 1
        st.session_state.cache_total_validados += 1
        
        # Se chegou no fim do cache, carregar próximo lote
        if st.session_state.cache_index_atual >= len(st.session_state.cache_produtos):
            sucesso = self.carregar_lote(
                categoria=st.session_state.cache_categoria_atual,
                forcar_reload=True
            )
            if not sucesso:
                return None
        
        return self.get_produto_atual()
    
    def adicionar_feedback(self, grupo_id: int, e_valido: bool, observacao: str = "", 
                          total_produtos: int = 0, produtos_corretos: int = 0,
                          falsos_positivos: List[int] = None, usuario: str = "sistema",
                          usuario_role: str = "administrador"):
        """
        Adiciona feedback à fila de salvamento
        Salva em background para navegação instantânea
        
        Args:
            usuario_role: 'administrador' ou 'dentista'
                - Dentistas: validações parciais/negativas vão para quarentena
                - Administradores: todas validações vão direto para o banco
        """
        feedback = {
            "grupo_id": grupo_id,
            "e_valido": e_valido,
            "observacao": observacao,
            "timestamp": datetime.now().isoformat(),
            "tipo": "validacao",
            "total_produtos": total_produtos,
            "produtos_corretos": produtos_corretos,
            "falsos_positivos": falsos_positivos or [],
            "usuario": usuario,
            "usuario_role": usuario_role
        }
        
        # Adicionar à fila de pendentes PRIMEIRO (navegação instantânea)
        st.session_state.cache_feedbacks_pendentes.append(feedback)
        
        # Tentar salvar em background (sem bloquear)
        try:
            if self._salvar_feedback_api(feedback):
                # Se sucesso, remover da fila
                if feedback in st.session_state.cache_feedbacks_pendentes:
                    st.session_state.cache_feedbacks_pendentes.remove(feedback)
        except:
            # Se falhar, feedback já está na fila de pendentes
            pass
    
    def _salvar_feedback_api(self, feedback: Dict) -> bool:
        """Salva um feedback na API"""
        try:
            # Determinar se vai para quarentena
            # Dentistas: validações parciais/negativas vão para quarentena
            # Administradores: todas validações vão direto
            em_quarentena = False
            usuario_role = feedback.get("usuario_role", "administrador")
            
            if usuario_role == "dentista" and not feedback["e_valido"]:
                em_quarentena = True
            
            # Converter para formato esperado pela API
            payload = {
                "match_id": feedback["grupo_id"],  # API espera match_id
                "tipo_feedback": "quarentena" if em_quarentena else feedback["tipo"],  # Marcar como quarentena
                "is_correto": feedback["e_valido"],  # API espera is_correto
                "observacoes": feedback.get("observacao", ""),  # API espera observacoes
                "total_produtos": feedback.get("total_produtos"),
                "produtos_corretos": feedback.get("produtos_corretos"),
                "falsos_positivos": json.dumps(feedback.get("falsos_positivos", [])),  # Converter para JSON string
                "usuario": feedback.get("usuario", "sistema"),
                "origem": f"interface_{usuario_role}"
            }
            
            response = requests.post(
                f"{self.api_base_url}/feedbacks/",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Erro ao salvar feedback: {e}")
            return False
    
    def _salvar_feedbacks_pendentes(self) -> int:
        """
        Tenta salvar todos os feedbacks pendentes
        
        Returns:
            Número de feedbacks salvos com sucesso
        """
        if not st.session_state.cache_feedbacks_pendentes:
            return 0
        
        salvos = 0
        pendentes_novos = []
        
        for feedback in st.session_state.cache_feedbacks_pendentes:
            if self._salvar_feedback_api(feedback):
                salvos += 1
            else:
                pendentes_novos.append(feedback)
        
        st.session_state.cache_feedbacks_pendentes = pendentes_novos
        
        if salvos > 0:
            st.success(f"✅ {salvos} feedback(s) pendente(s) sincronizado(s)!")
        
        return salvos
    
    def sincronizar_agora(self):
        """Força sincronização de feedbacks pendentes"""
        return self._salvar_feedbacks_pendentes()
    
    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas do cache"""
        return {
            "total_em_cache": len(st.session_state.cache_produtos),
            "index_atual": st.session_state.cache_index_atual,
            "total_validados": st.session_state.cache_total_validados,
            "feedbacks_pendentes": len(st.session_state.cache_feedbacks_pendentes),
            "progresso_cache": f"{st.session_state.cache_index_atual}/{len(st.session_state.cache_produtos)}"
        }
    
    def resetar_cache(self):
        """Reseta todo o cache (útil ao mudar categoria)"""
        st.session_state.cache_produtos = []
        st.session_state.cache_index_atual = 0
        st.session_state.cache_offset_global = 0
        st.session_state.cache_categoria_atual = None
    
    def voltar_produto(self):
        """Volta para o produto anterior (se possível)"""
        if st.session_state.cache_index_atual > 0:
            st.session_state.cache_index_atual -= 1
            st.session_state.cache_total_validados -= 1
            return True
        return False


# Função helper para usar no Streamlit
def get_cache_instance(api_base_url: str = "http://localhost:8000/api/v1") -> CacheValidacao:
    """
    Retorna instância singleton do cache
    """
    if 'cache_validacao_instance' not in st.session_state:
        st.session_state.cache_validacao_instance = CacheValidacao(api_base_url)
    return st.session_state.cache_validacao_instance
