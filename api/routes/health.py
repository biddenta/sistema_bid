from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "match-crew-api",
        "version": "1.0.0"
    }

@router.get("/status")
async def detailed_status():
    """Detailed system status"""
    # TODO: Adicionar verificações de banco, cache, etc.
    return {
        "api": "operational",
        "database": "connected",
        "matching_engine": "ready",
        "data_processor": "ready",
        "timestamp": datetime.now().isoformat()
    }