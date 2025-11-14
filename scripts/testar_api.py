#!/usr/bin/env python3
"""
Script de Testes da API Match Crew
Testa todos os endpoints antes de fazer deploy no Azure

Uso:
    python scripts/testar_api.py
    python scripts/testar_api.py --host http://localhost:8000
"""

import requests
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# ANSI color codes para output colorido
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class APITester:
    """Classe para testar todos os endpoints da API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def print_header(self, text: str):
        """Imprime cabeçalho formatado"""
        print(f"\n{'=' * 70}")
        print(f"{text:^70}")
        print(f"{'=' * 70}\n")
    
    def print_success(self, text: str):
        """Imprime mensagem de sucesso"""
        print(f"{GREEN}✓{RESET} {text}")
    
    def print_error(self, text: str):
        """Imprime mensagem de erro"""
        print(f"{RED}✗{RESET} {text}")
    
    def print_warning(self, text: str):
        """Imprime mensagem de aviso"""
        print(f"{YELLOW}⚠{RESET} {text}")
    
    def print_info(self, text: str):
        """Imprime mensagem informativa"""
        print(f"{BLUE}ℹ{RESET} {text}")
    
    def test_endpoint(
        self, 
        method: str, 
        endpoint: str, 
        description: str,
        expected_status: int = 200,
        data: dict = None,
        params: dict = None,
        check_keys: list = None
    ) -> bool:
        """
        Testa um endpoint da API
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Caminho do endpoint (ex: /api/v1/health)
            description: Descrição do teste
            expected_status: Status HTTP esperado
            data: Dados para enviar (POST/PUT)
            params: Query parameters (GET)
            check_keys: Lista de chaves que devem existir na resposta
            
        Returns:
            bool: True se teste passou, False caso contrário
        """
        self.total_tests += 1
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            # Fazer requisição
            if method == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Método HTTP inválido: {method}")
            
            elapsed_time = time.time() - start_time
            
            # Verificar status code
            if response.status_code != expected_status:
                self.print_error(
                    f"{description}\n"
                    f"  URL: {url}\n"
                    f"  Status esperado: {expected_status}, recebido: {response.status_code}\n"
                    f"  Resposta: {response.text[:200]}"
                )
                self.failed_tests += 1
                self.results.append({
                    'teste': description,
                    'status': 'FALHOU',
                    'erro': f"Status {response.status_code} != {expected_status}"
                })
                return False
            
            # Verificar se resposta é JSON
            try:
                response_data = response.json()
            except:
                if expected_status == 200:  # Só é problema se esperávamos dados
                    self.print_error(f"{description}\n  Resposta não é JSON válido")
                    self.failed_tests += 1
                    self.results.append({
                        'teste': description,
                        'status': 'FALHOU',
                        'erro': 'Resposta não é JSON'
                    })
                    return False
                response_data = {}
            
            # Verificar chaves esperadas
            if check_keys:
                missing_keys = [key for key in check_keys if key not in response_data]
                if missing_keys:
                    self.print_error(
                        f"{description}\n"
                        f"  Chaves faltando na resposta: {missing_keys}"
                    )
                    self.failed_tests += 1
                    self.results.append({
                        'teste': description,
                        'status': 'FALHOU',
                        'erro': f"Chaves faltando: {missing_keys}"
                    })
                    return False
            
            # Teste passou!
            self.print_success(
                f"{description} ({elapsed_time:.2f}s)"
            )
            self.passed_tests += 1
            self.results.append({
                'teste': description,
                'status': 'PASSOU',
                'tempo': f"{elapsed_time:.2f}s"
            })
            return True
            
        except requests.exceptions.ConnectionError:
            self.print_error(
                f"{description}\n"
                f"  Erro: Não foi possível conectar à API em {self.base_url}\n"
                f"  Verifique se o servidor está rodando!"
            )
            self.failed_tests += 1
            self.results.append({
                'teste': description,
                'status': 'FALHOU',
                'erro': 'Erro de conexão - servidor não está rodando?'
            })
            return False
            
        except requests.exceptions.Timeout:
            self.print_error(f"{description}\n  Erro: Timeout após 30s")
            self.failed_tests += 1
            self.results.append({
                'teste': description,
                'status': 'FALHOU',
                'erro': 'Timeout'
            })
            return False
            
        except Exception as e:
            self.print_error(f"{description}\n  Erro: {str(e)}")
            self.failed_tests += 1
            self.results.append({
                'teste': description,
                'status': 'FALHOU',
                'erro': str(e)
            })
            return False
    
    def run_all_tests(self):
        """Executa todos os testes da API"""
        
        self.print_header("TESTANDO MATCH CREW API")
        self.print_info(f"URL Base: {self.base_url}")
        self.print_info(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # ==================== TESTE 1: ROOT ====================
        self.print_header("1. ENDPOINT ROOT")
        self.test_endpoint(
            "GET", "/", 
            "Root endpoint",
            check_keys=["nome", "versao", "status", "endpoints"]
        )
        
        # ==================== TESTE 2: HEALTH ====================
        self.print_header("2. ENDPOINT HEALTH")
        self.test_endpoint(
            "GET", "/api/v1/health", 
            "Health check",
            check_keys=["status", "timestamp", "service"]
        )
        
        self.test_endpoint(
            "GET", "/api/v1/status", 
            "Status detalhado",
            check_keys=["api", "database", "timestamp"]
        )
        
        # ==================== TESTE 3: PRODUTOS ====================
        self.print_header("3. ENDPOINTS DE PRODUTOS")
        
        # Listar produtos (paginado)
        self.test_endpoint(
            "GET", "/api/v1/produtos",
            "Listar produtos (primeira página)",
            params={"pagina": 1, "tamanho": 10},
            check_keys=["dados", "paginacao"]
        )
        
        # Buscar produto por ID
        self.test_endpoint(
            "GET", "/api/v1/produtos/1",
            "Buscar produto por ID"
        )
        
        # Listar sites disponíveis
        self.test_endpoint(
            "GET", "/api/v1/produtos/sites/disponiveis",
            "Listar sites disponíveis",
            check_keys=["total", "sites"]
        )
        
        # Listar categorias disponíveis
        self.test_endpoint(
            "GET", "/api/v1/produtos/categorias/disponiveis",
            "Listar categorias disponíveis",
            check_keys=["total", "categorias"]
        )
        
        # Listar marcas disponíveis
        self.test_endpoint(
            "GET", "/api/v1/produtos/marcas/disponiveis",
            "Listar marcas disponíveis",
            check_keys=["total", "marcas"]
        )
        
        # Buscar produtos com filtros
        self.test_endpoint(
            "GET", "/api/v1/produtos",
            "Buscar produtos por site (filtro)",
            params={"pagina": 1, "tamanho": 5, "site": "Dental Cremer"},
            check_keys=["dados", "paginacao"]
        )
        
        self.test_endpoint(
            "GET", "/api/v1/produtos",
            "Buscar produtos por categoria (filtro)",
            params={"pagina": 1, "tamanho": 5, "categoria": "Ortodontia"},
            check_keys=["dados", "paginacao"]
        )
        
        # ==================== TESTE 4: PRODUTOS MESTRE ====================
        self.print_header("4. ENDPOINTS DE PRODUTOS MESTRE (MATCHES)")
        
        # Listar produtos mestre
        self.test_endpoint(
            "GET", "/api/v1/produtos-mestre",
            "Listar produtos mestre (primeira página)",
            params={"pagina": 1, "tamanho": 10},
            check_keys=["dados", "paginacao"]
        )
        
        # Buscar produto mestre por ID
        self.test_endpoint(
            "GET", "/api/v1/produtos-mestre/1",
            "Buscar produto mestre por ID"
        )
        
        # Estatísticas
        self.test_endpoint(
            "GET", "/api/v1/produtos-mestre/estatisticas",
            "Estatísticas de produtos mestre",
            check_keys=["estatisticas"]
        )
        
        # Buscar por categoria (filtro)
        self.test_endpoint(
            "GET", "/api/v1/produtos-mestre",
            "Buscar produtos mestre por categoria (filtro)",
            params={"pagina": 1, "tamanho": 5, "categoria": "Ortodontia"},
            check_keys=["dados", "paginacao"]
        )
        
        # Buscar com filtro de sites mínimos
        self.test_endpoint(
            "GET", "/api/v1/produtos-mestre",
            "Filtrar por mínimo de 3 sites",
            params={"pagina": 1, "tamanho": 5, "total_sites_min": 3},
            check_keys=["dados", "paginacao"]
        )
        
        # ==================== TESTE 5: MATCHING ENGINE ====================
        self.print_header("5. ENDPOINTS DE MATCHING ENGINE")
        
        # Estatísticas do matching
        self.test_endpoint(
            "GET", "/api/v1/matching/estatisticas",
            "Estatísticas do matching engine",
            check_keys=["produtos", "grupos"]
        )
        
        # ==================== TESTE 6: FEEDBACKS ====================
        self.print_header("6. ENDPOINTS DE FEEDBACKS")
        
        # Listar feedbacks
        self.test_endpoint(
            "GET", "/api/v1/feedbacks",
            "Listar feedbacks",
            params={"pagina": 1, "tamanho": 10},
            check_keys=["dados", "paginacao"]
        )
        
        # Estatísticas de feedbacks
        self.test_endpoint(
            "GET", "/api/v1/feedbacks/estatisticas",
            "Estatísticas de feedbacks",
            check_keys=["estatisticas"]
        )
        
        # ==================== TESTE 7: DATA PROCESSING ====================
        self.print_header("7. ENDPOINTS DE DATA PROCESSING")
        
        # Estatísticas de processamento
        self.test_endpoint(
            "GET", "/api/v1/data/stats",
            "Estatísticas do data processing"
        )
        
        # ==================== TESTE 8: SCRAPING ====================
        self.print_header("8. ENDPOINTS DE SCRAPING")
        
        # Listar sites disponíveis
        self.test_endpoint(
            "GET", "/api/v1/scraping/sites",
            "Listar sites disponíveis para scraping",
            check_keys=["total_sites", "sites"]
        )
        
        # Listar jobs de scraping
        self.test_endpoint(
            "GET", "/api/v1/scraping/jobs",
            "Listar jobs de scraping",
            check_keys=["total_jobs", "jobs"]
        )
        
        # ==================== RESULTADOS FINAIS ====================
        self.print_results()
    
    def print_results(self):
        """Imprime resumo dos resultados"""
        
        self.print_header("RESUMO DOS TESTES")
        
        print(f"Total de testes:  {self.total_tests}")
        print(f"{GREEN}Testes passados: {self.passed_tests}{RESET}")
        print(f"{RED}Testes falhados: {self.failed_tests}{RESET}")
        
        if self.failed_tests == 0:
            percentage = 100.0
        else:
            percentage = (self.passed_tests / self.total_tests) * 100
        
        print(f"\nTaxa de sucesso: {percentage:.1f}%")
        
        if self.failed_tests == 0:
            self.print_success("\n🎉 TODOS OS TESTES PASSARAM!")
            self.print_info("✅ API está pronta para deploy no Azure!")
        else:
            self.print_error(f"\n⚠️ {self.failed_tests} teste(s) falharam!")
            self.print_warning("Corrija os erros antes de fazer deploy no Azure.")
        
        # Salvar relatório
        self.save_report()
    
    def save_report(self):
        """Salva relatório de testes em JSON"""
        report = {
            "data_teste": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_testes": self.total_tests,
            "testes_passados": self.passed_tests,
            "testes_falhados": self.failed_tests,
            "taxa_sucesso": f"{(self.passed_tests / self.total_tests * 100):.1f}%",
            "resultados": self.results
        }
        
        report_file = f"exports/teste_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            from pathlib import Path
            Path("exports").mkdir(exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.print_info(f"\n📄 Relatório salvo em: {report_file}")
        except Exception as e:
            self.print_warning(f"Não foi possível salvar relatório: {e}")


def main():
    """Função principal"""
    
    parser = argparse.ArgumentParser(
        description='Testa todos os endpoints da API Match Crew',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python scripts/testar_api.py
  python scripts/testar_api.py --host http://localhost:8000
  python scripts/testar_api.py --host https://minha-api.azurewebsites.net
        """
    )
    
    parser.add_argument(
        '--host',
        default='http://localhost:8000',
        help='URL base da API (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    # Criar tester e executar testes
    tester = APITester(base_url=args.host)
    
    try:
        tester.run_all_tests()
        
        # Retornar código de saída baseado nos resultados
        return 0 if tester.failed_tests == 0 else 1
        
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Testes interrompidos pelo usuário{RESET}")
        return 1
    except Exception as e:
        print(f"\n\n{RED}❌ Erro fatal: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
