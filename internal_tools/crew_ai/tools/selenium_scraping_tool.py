from crewai.tools import BaseTool
from typing import Type, Dict, List, Any, Optional
from pydantic import BaseModel, Field
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from urllib.parse import urljoin, urlparse
import re

# Configurar logger
logger = logging.getLogger(__name__)


class SeleniumScrapingInput(BaseModel):
    """Input schema for SeleniumScrapingTool."""
    urls: List[str] = Field(..., description="Lista de URLs dos produtos para fazer scraping")
    selectors: Dict[str, str] = Field(
        default={
            "nome": ["h1", ".product-title", ".product-name", "[data-testid='product-title']"],
            "marca": [".brand", ".product-brand", "[data-testid='brand']", ".manufacturer"],
            "preco": [".price", ".product-price", "[data-testid='price']", ".price-current"],
            "embalagem": [".specs", ".product-specs", ".specifications", ".package-info"],
            "imagem": ["img.product-image", ".product-photo img", "[data-testid='product-image']"]
        },
        description="Dicionário com seletores CSS para extrair informações específicas"
    )
    wait_time: int = Field(default=10, description="Tempo limite de espera em segundos")
    headless: bool = Field(default=True, description="Executar browser em modo headless")


class SeleniumScrapingTool(BaseTool):
    name: str = "Selenium Dynamic Scraping Tool"
    description: str = (
        "Ferramenta avançada para scraping de sites com conteúdo dinâmico usando Selenium. "
        "Capaz de navegar por sites com JavaScript, aguardar carregamento de elementos dinâmicos "
        "e extrair informações detalhadas de produtos. Ideal para sites que não funcionam com "
        "scraping tradicional devido ao uso intensivo de JavaScript e carregamento assíncrono."
    )
    args_schema: Type[BaseModel] = SeleniumScrapingInput

    def __init__(self):
        super().__init__()

    def _setup_driver(self, headless: bool = True) -> Optional[webdriver.Chrome]:
        """Configura e retorna uma instância do ChromeDriver com webdriver-manager"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # Opções para melhor compatibilidade e performance
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.128 Safari/537.36")
            
            # Desabilitar imagens para performance (opcional)
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Usar webdriver-manager para baixar automaticamente o ChromeDriver correto
            logger.info("🔄 Configurando ChromeDriver automaticamente...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("✅ ChromeDriver inicializado com sucesso via webdriver-manager")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar ChromeDriver: {e}")
            logger.error("💡 Possíveis soluções:")
            logger.error("   1. Verifique se o Google Chrome está instalado")
            logger.error("   2. Execute: pip install webdriver-manager")
            logger.error("   3. Verifique conexão com internet (para download do driver)")
            return None

    def _extract_with_selectors(self, driver: webdriver.Chrome, selectors: List[str]) -> Optional[str]:
        """Tenta extrair texto usando uma lista de seletores CSS"""
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.text.strip():
                    return element.text.strip()
            except NoSuchElementException:
                continue
        return None

    def _extract_price(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrai e padroniza informações de preço"""
        if not text:
            return None
            
        # Regex para encontrar padrões de preço
        price_patterns = [
            r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{2})?)',  # R$ 1.234,56
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',   # $ 1,234.56
            r'(\d+(?:\.\d{3})*(?:,\d{2})?)\s*reais?',  # 1.234,56 reais
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)',        # Qualquer número com separadores
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1)
                # Normalizar formato brasileiro para americano
                if ',' in price_str and '.' in price_str:
                    # Formato brasileiro: 1.234,56
                    price_str = price_str.replace('.', '').replace(',', '.')
                elif ',' in price_str:
                    # Pode ser decimal brasileiro: 1234,56
                    price_str = price_str.replace(',', '.')
                
                try:
                    price_value = float(price_str)
                    return {
                        "valor": price_value,
                        "texto_original": text,
                        "moeda": "BRL" if "R$" in text or "real" in text.lower() else "USD"
                    }
                except ValueError:
                    continue
        
        return {"texto_original": text, "valor": None, "moeda": "unknown"}

    def _extract_package_info(self, text: str) -> Dict[str, Any]:
        """Extrai informações de embalagem do texto"""
        if not text:
            return {}
        
        package_info = {"texto_original": text}
        
        # Padrões para diferentes unidades
        patterns = {
            "volume_ml": r'(\d+(?:\.\d+)?)\s*ml',
            "volume_l": r'(\d+(?:\.\d+)?)\s*l(?:itros?)?',
            "peso_g": r'(\d+(?:\.\d+)?)\s*g(?:ramas?)?',
            "peso_kg": r'(\d+(?:\.\d+)?)\s*kg',
            "unidades": r'(\d+)\s*(?:un|unidades?|peças?)',
            "pack": r'pack\s*(?:com\s*)?(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    package_info[key] = float(match.group(1))
                except ValueError:
                    pass
        
        return package_info

    def _scrape_single_url(self, driver: webdriver.Chrome, url: str, selectors: Dict[str, List[str]], wait_time: int) -> Dict[str, Any]:
        """Faz scraping de uma única URL"""
        result = {
            "url": url,
            "success": False,
            "data": {},
            "errors": [],
            "timestamp": time.time()
        }
        
        try:
            logger.info(f"🔍 Iniciando scraping da URL: {url}")
            driver.get(url)
            
            # Aguardar o carregamento da página
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Aguardar um pouco mais para elementos dinâmicos
            time.sleep(2)
            
            # Extrair informações usando os seletores
            extracted_data = {}
            
            # Nome do produto
            nome = self._extract_with_selectors(driver, selectors.get("nome", ["h1"]))
            if nome:
                extracted_data["nome_produto"] = nome
            
            # Marca
            marca = self._extract_with_selectors(driver, selectors.get("marca", [".brand"]))
            if marca:
                extracted_data["marca"] = marca
            
            # Preço
            preco_text = self._extract_with_selectors(driver, selectors.get("preco", [".price"]))
            if preco_text:
                extracted_data["preco"] = self._extract_price(preco_text)
            
            # Embalagem/Especificações
            embalagem_text = self._extract_with_selectors(driver, selectors.get("embalagem", [".specs"]))
            if embalagem_text:
                extracted_data["embalagem"] = self._extract_package_info(embalagem_text)
            
            # URL da imagem
            try:
                img_selectors = selectors.get("imagem", ["img"])
                for selector in img_selectors:
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, selector)
                        img_src = img_element.get_attribute("src")
                        if img_src:
                            extracted_data["imagem_url"] = urljoin(url, img_src)
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.warning(f"Erro ao extrair imagem de {url}: {e}")
            
            # Extrair domínio para identificação do site
            parsed_url = urlparse(url)
            extracted_data["site_origem"] = parsed_url.netloc
            extracted_data["url_origem"] = url
            
            result["data"] = extracted_data
            result["success"] = True
            
            logger.info(f"Scraping concluído com sucesso para: {url}")
            
        except TimeoutException:
            error_msg = f"Timeout ao carregar a página: {url}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Erro durante scraping de {url}: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result

    def _run(self, urls: List[str], selectors: Dict[str, str] = None, wait_time: int = 10, headless: bool = True) -> str:
        """Executa o scraping das URLs fornecidas"""
        
        # Converter seletores de string para lista se necessário
        if selectors:
            processed_selectors = {}
            for key, value in selectors.items():
                if isinstance(value, str):
                    processed_selectors[key] = [value]
                elif isinstance(value, list):
                    processed_selectors[key] = value
                else:
                    processed_selectors[key] = [str(value)]
        else:
            # Seletores padrão
            processed_selectors = {
                "nome": ["h1", ".product-title", ".product-name", "[data-testid='product-title']"],
                "marca": [".brand", ".product-brand", "[data-testid='brand']", ".manufacturer"],
                "preco": [".price", ".product-price", "[data-testid='price']", ".price-current"],
                "embalagem": [".specs", ".product-specs", ".specifications", ".package-info"],
                "imagem": ["img.product-image", ".product-photo img", "[data-testid='product-image']"]
            }
        
        driver = None
        results = []
        
        try:
            driver = self._setup_driver(headless)
            
            if driver is None:
                # Se não conseguiu configurar o driver, retornar erro claro
                error_result = {
                    "error": "ChromeDriver não disponível. Scraping dinâmico não pode ser executado.",
                    "success": False,
                    "recommendation": "Instale o Google Chrome e execute: pip install webdriver-manager",
                    "urls_attempted": urls
                }
                results.append(error_result)
            else:
                for url in urls:
                    if url and url.strip():
                        result = self._scrape_single_url(driver, url.strip(), processed_selectors, wait_time)
                        results.append(result)
                        
                        # Pequena pausa entre requisições
                        time.sleep(1)
            
        except Exception as e:
            error_result = {
                "error": f"Erro geral na configuração do scraping: {str(e)}",
                "success": False,
                "urls_attempted": urls
            }
            results.append(error_result)
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        # Compilar estatísticas
        successful_scrapes = sum(1 for r in results if r.get("success", False))
        total_scrapes = len([r for r in results if "url" in r])
        
        final_result = {
            "scraping_results": results,
            "statistics": {
                "total_urls": len(urls),
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": total_scrapes - successful_scrapes,
                "success_rate": f"{(successful_scrapes/total_scrapes*100):.1f}%" if total_scrapes > 0 else "0%"
            },
            "timestamp": time.time()
        }
        
        return json.dumps(final_result, indent=2, ensure_ascii=False)