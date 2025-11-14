import uvicorn
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 70)
    print(" " * 20 + "MATCH CREW API - SERVIDOR")
    print("=" * 70)
    print("\nIniciando servidor FastAPI...")
    print("\nDocumentação:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc:      http://localhost:8000/redoc")
    print("\nAPI Endpoints:")
    print("   Root:              http://localhost:8000/")
    print("   Health:            http://localhost:8000/api/v1/health")
    print("   Produtos:          http://localhost:8000/api/v1/produtos")
    print("   Produtos Mestre:   http://localhost:8000/api/v1/produtos-mestre")
    print("   Feedbacks:         http://localhost:8000/api/v1/feedbacks")
    print("\nPressione CTRL+C para parar o servidor")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api"],
        log_level="info",
        access_log=True
    )
