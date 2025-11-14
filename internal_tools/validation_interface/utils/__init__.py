"""
Utils para Interface de Validação
"""

from .cache_validacao import get_cache_instance
from .auth import (
    is_logged_in, mostrar_tela_login, mostrar_info_usuario,
    is_admin, is_ajudante, get_username, get_user_display_name, get_user_role
)
from .processador_feedback import ProcessadorFeedback
from .aplicador_feedback_real import AplicadorFeedbackDeterministico
from .matching_integration import MatchingComFeedback

__all__ = [
    'get_cache_instance',
    'is_logged_in',
    'mostrar_tela_login',
    'mostrar_info_usuario',
    'is_admin',
    'is_ajudante',
    'get_username',
    'get_user_display_name',
    'get_user_role',
    'ProcessadorFeedback',
    'AplicadorFeedbackDeterministico',
    'MatchingComFeedback'
]
