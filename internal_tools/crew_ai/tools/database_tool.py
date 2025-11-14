from crewai.tools import BaseTool
from typing import Type, Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
import sqlite3
import json
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseQueryInput(BaseModel):
    """Input schema for DatabaseTool queries."""
    query_type: str = Field(..., description="Tipo de consulta: 'select', 'insert', 'update', 'delete', 'search_matches', 'sample'")
    filters: Dict[str, Any] = Field(default={}, description="Filtros para a consulta (WHERE clauses)")
    fields: List[str] = Field(default=[], description="Campos específicos para SELECT (vazio = todos)")
    limit: int = Field(default=1000, description="Limite de resultados (máximo recomendado = 1000 para evitar token overload)")
    data: Dict[str, Any] = Field(default={}, description="Dados para INSERT/UPDATE")
    search_criteria: Dict[str, Any] = Field(default={}, description="Critérios específicos para busca de matches")


class DatabaseTool(BaseTool):
    """Versão corrigida da DatabaseTool com proteção contra token overload"""
    name: str = "Database Products Tool"
    description: str = (
        "Ferramenta OTIMIZADA para interação com banco de dados produtos.db. "
        "PROTEÇÃO ATIVA contra token overload: limita automaticamente consultas grandes. "
        "Use query_type='sample' para análises que não precisam de todos os dados. "
        "Trabalha com tabelas 'produtos' e 'produtos_unificados'. "
        "CAMPOS DISPONÍVEIS: Nome, categoria, descricao_produto, Marca, Site, preco_normal, preco_desconto, SKU_site, url, imagem_principal, id_bid. "
        "ALIASES SUPORTADOS: product_name→Nome, category→categoria, description→descricao_produto, brand→Marca, site→Site, price→preco_normal. "
        "Ideal para análises de agentes com volumes controlados de dados."
    )
    args_schema: Type[BaseModel] = DatabaseQueryInput

    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com o banco de dados"""
        try:
            # Tentar primeiro o banco atual do match_crew
            db_path = Path("match_crew.db")
            if not db_path.exists():
                # Fallback para o caminho legacy se existir
                db_path = Path("data/produtos.db")
                if not db_path.exists():
                    raise FileNotFoundError(f"Banco de dados não encontrado. Procurado em: match_crew.db e data/produtos.db")
            
            logger.info(f"📂 Conectando ao banco: {db_path}")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def _get_sample_data(self, table: str, limit: int = 500, fields: List[str] = None) -> List[Dict]:
        """Retorna amostra representativa dos dados (evita token overload)"""
        conn = self._get_connection()
        try:
            # Mapear campos solicitados para nomes reais da tabela
            field_mapping = {
                'product_name': 'Nome',
                'category': 'categoria', 
                'description': 'descricao_produto',
                'brand': 'Marca',
                'site': 'Site',
                'price': 'preco_normal',
                'discount_price': 'preco_desconto',
                'sku': 'SKU_site',
                'url': 'url',
                'image': 'imagem_principal'
            }
            
            # Se fields especificados, mapear para nomes corretos
            if fields:
                mapped_fields = []
                for field in fields:
                    if field in field_mapping:
                        mapped_fields.append(field_mapping[field])
                    elif field in ['Nome', 'categoria', 'descricao_produto', 'Marca', 'Site', 'preco_normal', 'preco_desconto', 'SKU_site', 'url', 'imagem_principal', 'id_bid']:
                        mapped_fields.append(field)  # Campo já está correto
                    else:
                        logger.warning(f"Campo desconhecido ignorado: {field}")
                
                if mapped_fields:
                    fields_str = ", ".join(mapped_fields)
                else:
                    fields_str = "*"
            else:
                fields_str = "*"
            
            # Query otimizada para amostra representativa  
            query = f"""
            SELECT {fields_str} FROM {table} 
            WHERE rowid IN (
                SELECT rowid FROM {table} 
                ORDER BY RANDOM() 
                LIMIT {limit}
            )
            ORDER BY Site, Marca, Nome
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Adicionar aliases para compatibilidade com agentes
                if 'Nome' in row_dict:
                    row_dict['product_name'] = row_dict['Nome']
                if 'categoria' in row_dict:
                    row_dict['category'] = row_dict['categoria']
                if 'descricao_produto' in row_dict:
                    row_dict['description'] = row_dict['descricao_produto']
                results.append(row_dict)
            
            logger.info(f"📊 Amostra retornada: {len(results)} produtos de {table} (proteção anti-overload)")
            return results
            
        except Exception as e:
            logger.error(f"Erro na consulta de amostra: {e}")
            return []
        finally:
            conn.close()

    def _execute_select_safe(self, table: str, fields: List[str], filters: Dict[str, Any], limit: int) -> List[Dict]:
        """Executa consulta SELECT com proteção contra token overload"""
        
        conn = self._get_connection()
        try:
            # PROTEÇÃO CONFIGURÁVEL: Permitir lotes maiores para processamento total
            # Valores seguros para diferentes cenários:
            # - 2000: Consultas normais de agentes (proteção máxima)
            # - 10000: Processamento em lotes médios (balanceado)
            # - 50000: Processamento em lotes grandes (uso com cuidado)
            
            limite_original = limit
            
            # Se limit = 0, significa "processar todos", definir limite seguro
            if limit == 0:
                # Para processamento total, usar limite de lote seguro
                limit = 10000  # Lote seguro para processar tudo gradualmente
                logger.info(f"📊 PROCESSAMENTO TOTAL: Usando limite de lote seguro de {limit} produtos")
            
            # Proteção apenas para limites excessivamente altos (mais de 50K)
            elif limit > 50000:
                logger.warning(f"⚠️ PROTEÇÃO ATIVADA: Limite {limit} muito alto, reduzindo para 50000 para evitar token overload")
                limit = 50000
            
            # Para limites entre 2K e 50K, permitir com aviso
            elif limit > 2000:
                logger.info(f"📈 LOTE GRANDE: Processando {limit} produtos (limite aumentado para processamento em massa)")
            
            # Construir campos
            if fields:
                fields_str = ", ".join(fields)
            else:
                fields_str = "*"
            
            # Construir WHERE
            where_clause, values = self._build_where_clause(filters)
            
            # Query completa - sempre com limite para proteger contra overload
            query = f"SELECT {fields_str} FROM {table}{where_clause} LIMIT {limit}"
            
            cursor = conn.cursor()
            cursor.execute(query, values)
            
            # Converter para lista de dicionários
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            logger.info(f"✅ Consulta retornou {len(results)} resultados da tabela {table} (limite aplicado: {limit})")
            
            # Aviso se atingiu o limite
            if len(results) == limit:
                logger.warning(f"⚠️ AVISO: Consulta atingiu limite de {limit} resultados. Pode haver mais dados disponíveis.")
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na consulta SELECT: {e}")
            return []
        finally:
            conn.close()

    def _build_where_clause(self, filters: Dict[str, Any]) -> tuple:
        """Constrói cláusula WHERE e valores"""
        if not filters:
            return "", []
        
        conditions = []
        values = []
        
        for key, value in filters.items():
            if key == 'table':  # Skip meta fields
                continue
                
            if isinstance(value, list):
                placeholders = ','.join(['?' for _ in value])
                conditions.append(f"{key} IN ({placeholders})")
                values.extend(value)
            else:
                conditions.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, values

    def _get_database_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do banco de dados"""
        conn = self._get_connection()
        try:
            stats = {}
            
            # Stats da tabela produtos
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM produtos")
            stats['total_produtos'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT Site) as sites FROM produtos")
            stats['total_sites'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT Marca) as marcas FROM produtos WHERE Marca IS NOT NULL")
            stats['total_marcas'] = cursor.fetchone()[0]
            
            # Stats por site
            cursor.execute("SELECT Site, COUNT(*) as count FROM produtos GROUP BY Site ORDER BY count DESC")
            stats['produtos_por_site'] = dict(cursor.fetchall())
            
            # Stats da tabela produtos_unificados (se existir)
            try:
                cursor.execute("SELECT COUNT(*) as total FROM produtos_unificados")
                stats['total_produtos_unificados'] = cursor.fetchone()[0]
            except:
                stats['total_produtos_unificados'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}
        finally:
            conn.close()

    def _run(self, query_type: str, filters: Dict[str, Any] = None, fields: List[str] = None, 
             limit: int = 1000, data: Dict[str, Any] = None, search_criteria: Dict[str, Any] = None) -> str:
        """Executa operação no banco de dados com proteção contra token overload"""
        
        try:
            filters = filters or {}
            fields = fields or []
            data = data or {}
            search_criteria = search_criteria or {}
            
            table = filters.pop('table', 'produtos')
            
            if query_type == "select":
                results = self._execute_select_safe(table, fields, filters, limit)
                result = {
                    "operation": "select",
                    "table": table,
                    "data": results,
                    "count": len(results),
                    "limit_applied": limit if limit <= 2000 else 2000,
                    "protection_active": limit > 2000 or limit == 0
                }
                
            elif query_type == "sample":
                # Nova operação para amostras pequenas e eficientes
                # Se limit é 0, usar amostra padrão de 100
                if limit == 0:
                    sample_limit = 100
                    logger.info("🔧 Limit 0 detectado, usando amostra padrão de 100 registros")
                else:
                    sample_limit = min(limit, 500)  # Máximo 500 para amostras
                
                results = self._get_sample_data(table, sample_limit, fields)
                result = {
                    "operation": "sample",
                    "table": table,
                    "data": results,
                    "count": len(results),
                    "sample_size": sample_limit,
                    "note": "Amostra representativa para análise de agentes",
                    "field_mapping": "Campos mapeados automaticamente (product_name→Nome, category→categoria, description→descricao_produto)",
                    "limit_adjustment": "Limit 0 convertido para amostra padrão" if limit == 0 else "Limit aplicado normalmente"
                }
                
            elif query_type == "stats":
                result = {
                    "operation": "stats",
                    "statistics": self._get_database_stats()
                }
                
            else:
                result = {
                    "error": f"Tipo de query não suportado: {query_type}",
                    "supported_types": ["select", "sample", "stats"],
                    "recommendation": "Use 'sample' para análises de agentes (mais eficiente)"
                }
            
            # Adicionar metadata
            result["timestamp"] = datetime.now().isoformat()
            result["database"] = "produtos.db"
            result["token_protection"] = "ATIVA" if query_type in ["select", "sample"] else "N/A"
            
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
            
        except Exception as e:
            error_result = {
                "error": f"Erro na operação {query_type}: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "recommendation": "Tente usar query_type='sample' para operações mais eficientes"
            }
            logger.error(f"Erro na ferramenta DatabaseTool: {e}")
            return json.dumps(error_result, indent=2, ensure_ascii=False)