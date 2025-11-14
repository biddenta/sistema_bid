import json
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Match, ValidationRequest, Feedback
from ..repositories import MatchRepository, FeedbackRepository, ProductRepository


class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.match_repo = MatchRepository(db)
        self.feedback_repo = FeedbackRepository(db)
        self.product_repo = ProductRepository(db)
    
    async def get_pending_matches(self, limit: int = 10) -> List[Match]:
        """Get matches pending validation."""
        return self.match_repo.get_unvalidated(limit=limit)
    
    async def validate_matches(self, validation_request: ValidationRequest) -> Dict:
        """Validate matches based on user input."""
        validated_count = 0
        feedback_created = 0
        
        for match_id in validation_request.match_ids:
            match = self.match_repo.get_by_id(match_id)
            if not match:
                continue
            
            # Update match based on validation type
            if validation_request.validation_type == "accept":
                update_data = {
                    "is_match": True,
                    "is_validated": True,
                    "feedback_type": "manual_accept",
                    "validation_notes": validation_request.notes,
                    "validated_at": datetime.utcnow()
                }
            elif validation_request.validation_type == "reject":
                update_data = {
                    "is_match": False,
                    "is_validated": True,
                    "feedback_type": "manual_reject", 
                    "validation_notes": validation_request.notes,
                    "validated_at": datetime.utcnow()
                }
            elif validation_request.validation_type == "partial":
                # Handle partial validation with specific selections
                update_data = {
                    "is_match": self._determine_partial_match(validation_request.partial_selections),
                    "is_validated": True,
                    "feedback_type": "partial_validation",
                    "validation_notes": f"Partial: {validation_request.notes}",
                    "validated_at": datetime.utcnow()
                }
            
            # Update match
            self.match_repo.update(match_id, update_data)
            validated_count += 1
            
            # Create feedback record
            feedback_data = {
                "match_id": match_id,
                "feedback_type": validation_request.validation_type,
                "is_correct": update_data["is_match"],
                "user_notes": validation_request.notes,
                "patterns_detected": json.dumps(validation_request.partial_selections) if validation_request.partial_selections else None
            }
            
            self.feedback_repo.create(feedback_data)
            feedback_created += 1
        
        return {
            "status": "success",
            "validated_matches": validated_count,
            "feedback_records": feedback_created,
            "message": f"Successfully validated {validated_count} matches"
        }
    
    def _determine_partial_match(self, partial_selections: Optional[Dict]) -> bool:
        """Determine if partial validation results in a match."""
        if not partial_selections:
            return False
        
        # Count positive selections
        positive_count = sum(1 for selected in partial_selections.values() if selected)
        total_count = len(partial_selections)
        
        # Consider it a match if more than 50% of comparisons are positive
        return positive_count > (total_count / 2)
    
    async def get_match_details(self, match_id: int) -> Optional[Dict]:
        """Get detailed information about a match including products."""
        match = self.match_repo.get_by_id(match_id)
        if not match:
            return None
        
        product1 = self.product_repo.get_by_id(match.produto_id_1)
        product2 = self.product_repo.get_by_id(match.produto_id_2)
        feedbacks = self.feedback_repo.get_by_match(match_id)
        
        return {
            "match": match,
            "product1": product1,
            "product2": product2,
            "feedbacks": feedbacks,
            "comparison": self._generate_comparison(product1, product2)
        }
    
    def _generate_comparison(self, product1, product2) -> Dict:
        """Generate detailed comparison between two products."""
        comparison = {
            "name_similarity": self._calculate_field_similarity(product1.nome, product2.nome),
            "description_similarity": self._calculate_field_similarity(product1.descricao, product2.descricao),
            "brand_match": product1.marca == product2.marca if product1.marca and product2.marca else None,
            "category_match": product1.categoria == product2.categoria if product1.categoria and product2.categoria else None,
            "price_difference": abs(product1.preco - product2.preco) if product1.preco and product2.preco else None
        }
        
        return comparison
    
    def _calculate_field_similarity(self, field1: str, field2: str) -> float:
        """Calculate similarity between two text fields."""
        if not field1 or not field2:
            return 0.0
        
        tokens1 = set(field1.lower().split())
        tokens2 = set(field2.lower().split())
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def get_matching_statistics(self) -> Dict:
        """Get comprehensive matching statistics."""
        stats = self.match_repo.get_statistics()
        
        # Add additional statistics
        recent_feedbacks = self.feedback_repo.get_all(limit=100)
        feedback_by_type = {}
        
        for feedback in recent_feedbacks:
            feedback_type = feedback.feedback_type
            if feedback_type not in feedback_by_type:
                feedback_by_type[feedback_type] = {"correct": 0, "incorrect": 0}
            
            if feedback.is_correct:
                feedback_by_type[feedback_type]["correct"] += 1
            else:
                feedback_by_type[feedback_type]["incorrect"] += 1
        
        return {
            **stats,
            "feedback_statistics": feedback_by_type,
            "validation_accuracy": self._calculate_validation_accuracy(recent_feedbacks)
        }
    
    def _calculate_validation_accuracy(self, feedbacks: List) -> float:
        """Calculate overall validation accuracy."""
        if not feedbacks:
            return 0.0
        
        correct_validations = sum(1 for f in feedbacks if f.is_correct)
        return correct_validations / len(feedbacks)