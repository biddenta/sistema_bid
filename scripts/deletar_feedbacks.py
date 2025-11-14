"""
Script para deletar todos os feedbacks do banco de dados.
Uso: python scripts/deletar_feedbacks.py

CUIDADO: Este script apaga TODOS os feedbacks permanentemente!
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from api.models import Feedback, Base
from api.database import DATABASE_URL, engine, SessionLocal


def confirmar_exclusao():
    """Solicita confirmação do usuário antes de deletar"""
    print("=" * 60)
    print("⚠️  ATENÇÃO: EXCLUSÃO DE DADOS ⚠️")
    print("=" * 60)
    print("\nEste script irá DELETAR TODOS os feedbacks do banco de dados.")
    print("Esta ação NÃO PODE SER DESFEITA!\n")
    
    resposta = input("Digite 'DELETAR' (em maiúsculas) para confirmar: ")
    return resposta == "DELETAR"


def contar_feedbacks(db):
    """Conta quantos feedbacks existem"""
    return db.query(Feedback).count()


def deletar_todos_feedbacks(db):
    """Deleta todos os feedbacks"""
    try:
        # Deletar todos os registros
        total_deletados = db.query(Feedback).delete()
        db.commit()
        return total_deletados
    except Exception as e:
        db.rollback()
        raise e


def resetar_autoincrement(db):
    """Reseta o contador de auto-increment da tabela (SQLite)"""
    try:
        # Para SQLite
        db.execute(text("DELETE FROM sqlite_sequence WHERE name='feedbacks'"))
        db.commit()
        print("✅ Contador de ID resetado com sucesso!")
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível resetar o contador: {e}")


def main():
    """Função principal"""
    print("\n🗑️  Script de Exclusão de Feedbacks\n")
    print(f"📁 Banco de dados: {DATABASE_URL}\n")
    
    # Criar sessão
    db = SessionLocal()
    
    try:
        # Contar feedbacks existentes
        total_antes = contar_feedbacks(db)
        print(f"📊 Total de feedbacks encontrados: {total_antes}\n")
        
        if total_antes == 0:
            print("✅ Não há feedbacks para deletar. Tabela já está vazia!")
            return
        
        # Solicitar confirmação
        if not confirmar_exclusao():
            print("\n❌ Operação cancelada pelo usuário.")
            return
        
        print("\n🔄 Deletando feedbacks...")
        total_deletados = deletar_todos_feedbacks(db)
        
        print(f"✅ {total_deletados} feedbacks deletados com sucesso!")
        
        # Resetar auto-increment
        print("\n🔄 Resetando contador de IDs...")
        resetar_autoincrement(db)
        
        # Verificar se está vazio
        total_depois = contar_feedbacks(db)
        print(f"\n📊 Feedbacks restantes: {total_depois}")
        
        if total_depois == 0:
            print("\n✅ Tabela feedbacks completamente limpa!")
        else:
            print(f"\n⚠️  Aviso: Ainda restam {total_depois} feedbacks na tabela.")
            
    except Exception as e:
        print(f"\n❌ Erro ao deletar feedbacks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("Operação concluída!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
