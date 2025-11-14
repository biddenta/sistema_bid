import json
import sqlite3
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Produto, ProdutosMestre, StatusProcesso
from ..repositories import ProductRepository, MatchRepository


class DataProcessorService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.match_repo = MatchRepository(db)
    
    async def process_database(self, source_db_path: str) -> ProcessingStatus:
        """Process products from source database and create matches."""
        try:
            start_time = datetime.now()
            
            # Load products from source database
            products = self._load_products_from_db(source_db_path)
            
            # Store products in API database
            stored_products = []
            for product_data in products:
                product = self.product_repo.create(product_data)
                stored_products.append(product)
            
            # Generate matches
            matches_created = await self._generate_matches(stored_products)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return ProcessingStatus(
                status="success",
                message="Database processed successfully",
                processed_count=len(stored_products),
                total_count=len(products),
                created_matches=matches_created,
                processing_time=processing_time
            )
            
        except Exception as e:
            return ProcessingStatus(
                status="error",
                message=f"Error processing database: {str(e)}",
                processed_count=0,
                total_count=0,
                created_matches=0,
                processing_time=0.0
            )
    
    def _load_products_from_db(self, db_path: str) -> List[Dict]:
        """Load products from SQLite database."""
        conn = sqlite3.connect(db_path)
        query = """
        SELECT nome, descricao, marca, categoria, subcategoria, preco
        FROM produtos
        WHERE status = 'active' OR status IS NULL
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert to list of dictionaries
        products = []
        for _, row in df.iterrows():
            product_data = {
                "nome": row.get("nome", ""),
                "descricao": row.get("descricao"),
                "marca": row.get("marca"),
                "categoria": row.get("categoria"),
                "subcategoria": row.get("subcategoria"),
                "preco": row.get("preco")
            }
            products.append(product_data)
        
        return products
    
    async def _generate_matches(self, products: List[Product]) -> int:
        """Generate matches between products using similarity algorithm."""
        matches_created = 0
        
        for i, product1 in enumerate(products):
            for j, product2 in enumerate(products[i+1:], i+1):
                similarity = self._calculate_similarity(product1, product2)
                
                if similarity > 0.7:  # Threshold for potential matches
                    # Check if match already exists
                    existing_match = self.match_repo.get_by_products(product1.id, product2.id)
                    
                    if not existing_match:
                        match_data = {
                            "produto_id_1": product1.id,
                            "produto_id_2": product2.id,
                            "similarity_score": similarity,
                            "is_match": similarity > 0.85  # Auto-approve high similarity
                        }
                        
                        self.match_repo.create(match_data)
                        matches_created += 1
        
        return matches_created
    
    def _calculate_similarity(self, product1: Product, product2: Product) -> float:
        """Calculate similarity between two products."""
        # Simple similarity calculation based on name and description
        # This should be replaced with the actual similarity algorithm from the legacy system
        
        score = 0.0
        weight_total = 0.0
        
        # Name similarity (40% weight)
        if product1.nome and product2.nome:
            name_similarity = self._text_similarity(product1.nome, product2.nome)
            score += name_similarity * 0.4
            weight_total += 0.4
        
        # Description similarity (30% weight)
        if product1.descricao and product2.descricao:
            desc_similarity = self._text_similarity(product1.descricao, product2.descricao)
            score += desc_similarity * 0.3
            weight_total += 0.3
        
        # Brand similarity (20% weight)
        if product1.marca and product2.marca:
            brand_similarity = 1.0 if product1.marca.lower() == product2.marca.lower() else 0.0
            score += brand_similarity * 0.2
            weight_total += 0.2
        
        # Category similarity (10% weight)
        if product1.categoria and product2.categoria:
            cat_similarity = 1.0 if product1.categoria.lower() == product2.categoria.lower() else 0.0
            score += cat_similarity * 0.1
            weight_total += 0.1
        
        return score / weight_total if weight_total > 0 else 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple token overlap."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def get_processing_statistics(self) -> Dict:
        """Get statistics about data processing."""
        total_products = len(self.product_repo.get_all())
        match_stats = self.match_repo.get_statistics()
        
        return {
            "total_products": total_products,
            **match_stats,
            "last_processed": datetime.now().isoformat()
        }