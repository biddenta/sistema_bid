from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
import subprocess
import os
from pathlib import Path

router = APIRouter(prefix="/scraping", tags=["Scraping"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ScrapingRequest(BaseModel):
    """Schema para requisição de scraping"""
    sites: List[str] = []  # Lista de sites para scraping. Vazio = todos
    tipo: str = "completo"  # "completo" ou "diario"
    categorias: List[str] = []  # Lista de categorias. Vazio = todas

class ScrapingStatus(BaseModel):
    """Status de um job de scraping"""
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    sites_processados: List[str] = []
    sites_pendentes: List[str] = []
    total_produtos: int = 0
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    errors: List[dict] = []

# ============================================================================
# MAPEAMENTO DE SITES E SCRIPTS
# ============================================================================

SITES_DISPONIVEIS = {
    "dental_cremer": {
        "completo": "internal_tools/scrapers/dental_cremer/scraping_cremer.py",
        "diario": "internal_tools/scrapers/dental_cremer/scraping_cremer.py"
    },
    "dental_speed": {
        "completo": "internal_tools/scrapers/dental_speed/scraping_speed.py",
        "diario": "internal_tools/scrapers/dental_speed/scraping_speed.py"
    },
    "dental_medsul": {
        "completo": "internal_tools/scrapers/dental_medsul/scraping_completo_medsul.py",
        "diario": "internal_tools/scrapers/dental_medsul/scraping_diario_medsul.py"
    },
    "dental_proclin": {
        "completo": "internal_tools/scrapers/dental_proclin/scraping_dentalproclin_completo.py",
        "diario": "internal_tools/scrapers/dental_proclin/scraping_dentalproclin_completo.py"
    },
    "dental_shop": {
        "completo": "internal_tools/scrapers/dental_shop/scraping_dentalshop_completo.py",
        "diario": "internal_tools/scrapers/dental_shop/scraping_dentalshop_completo.py"
    },
    "dental_sorria": {
        "completo": "internal_tools/scrapers/dental_sorria/scraping_sorria_requests.py",
        "diario": "internal_tools/scrapers/dental_sorria/scraping_sorria_diario_requests.py"
    },
    "dental_apoio": {
        "completo": "internal_tools/scrapers/dental_apoio/scraping_apoio_completo.py",
        "diario": "internal_tools/scrapers/dental_apoio/scraping_apoio_diario.py"
    },
    "interdental": {
        "completo": "internal_tools/scrapers/interdental/scraping_interdental_principal.py",
        "diario": "internal_tools/scrapers/interdental/scraping_interdental_principal.py"
    },
    "surya": {
        "completo": "internal_tools/scrapers/surya/scraping_surya.py",
        "diario": "internal_tools/scrapers/surya/scraping_surya.py"
    }
}

# Armazenamento temporário de jobs (em produção, usar Redis ou banco)
scraping_jobs = {}

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def get_project_root() -> Path:
    """Retorna o diretório raiz do projeto"""
    return Path(__file__).parent.parent.parent

async def executar_scraper(site: str, tipo: str, job_id: str):
    """Executa um script de scraping em background"""
    project_root = get_project_root()
    
    if site not in SITES_DISPONIVEIS:
        scraping_jobs[job_id]["errors"].append({
            "site": site,
            "error": f"Site '{site}' não encontrado"
        })
        return
    
    script_path = SITES_DISPONIVEIS[site].get(tipo)
    if not script_path:
        scraping_jobs[job_id]["errors"].append({
            "site": site,
            "error": f"Tipo '{tipo}' não disponível para {site}"
        })
        return
    
    full_script_path = project_root / script_path
    
    if not full_script_path.exists():
        scraping_jobs[job_id]["errors"].append({
            "site": site,
            "error": f"Script não encontrado: {script_path}"
        })
        return
    
    try:
        # Atualizar status
        scraping_jobs[job_id]["status"] = "running"
        scraping_jobs[job_id]["current_site"] = site
        
        # Executar script
        result = subprocess.run(
            ["python", str(full_script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=3600  # 1 hora de timeout
        )
        
        # Processar resultado
        if result.returncode == 0:
            scraping_jobs[job_id]["sites_processados"].append(site)
            scraping_jobs[job_id]["message"] = f"✅ {site} processado com sucesso"
        else:
            scraping_jobs[job_id]["errors"].append({
                "site": site,
                "error": result.stderr[:500] if result.stderr else "Erro desconhecido"
            })
            
    except subprocess.TimeoutExpired:
        scraping_jobs[job_id]["errors"].append({
            "site": site,
            "error": "Timeout: Scraping demorou mais de 1 hora"
        })
    except Exception as e:
        scraping_jobs[job_id]["errors"].append({
            "site": site,
            "error": str(e)
        })

async def executar_scraping_completo(job_id: str, sites: List[str], tipo: str):
    """Executa scraping de múltiplos sites sequencialmente"""
    try:
        for site in sites:
            if site in scraping_jobs[job_id]["sites_pendentes"]:
                scraping_jobs[job_id]["sites_pendentes"].remove(site)
            await executar_scraper(site, tipo, job_id)
        
        # Finalizar job
        scraping_jobs[job_id]["status"] = "completed"
        scraping_jobs[job_id]["completed_at"] = datetime.now()
        scraping_jobs[job_id]["message"] = f"✅ Scraping concluído: {len(scraping_jobs[job_id]['sites_processados'])} sites processados"
        
    except Exception as e:
        scraping_jobs[job_id]["status"] = "failed"
        scraping_jobs[job_id]["completed_at"] = datetime.now()
        scraping_jobs[job_id]["message"] = f"❌ Erro ao executar scraping: {str(e)}"

# ============================================================================
# ROTAS
# ============================================================================

@router.get("/sites", response_model=dict)
async def listar_sites_disponiveis():
    """
    Lista todos os sites disponíveis para scraping.
    
    **Retorna:**
    - Lista de sites configurados
    - Tipos de scraping disponíveis para cada site
    """
    sites_info = {}
    for site, scripts in SITES_DISPONIVEIS.items():
        sites_info[site] = {
            "tipos_disponiveis": list(scripts.keys()),
            "scripts": scripts
        }
    
    return {
        "total_sites": len(SITES_DISPONIVEIS),
        "sites": sites_info
    }

@router.post("/start", response_model=dict)
async def iniciar_scraping(request: ScrapingRequest, background_tasks: BackgroundTasks):
    """
    Iniciar processo de scraping de um ou mais sites.
    
    **Parâmetros:**
    - sites: Lista de sites para scraping. Vazio = todos
    - tipo: "completo" (scraping total) ou "diario" (apenas atualizações)
    - categorias: Lista de categorias específicas. Vazio = todas
    
    **Exemplo:**
    ```json
    {
        "sites": ["dental_cremer", "dental_speed"],
        "tipo": "completo",
        "categorias": []
    }
    ```
    
    **Retorna:**
    - job_id: ID do job para acompanhamento
    - status: Status inicial do job
    """
    # Validar tipo
    if request.tipo not in ["completo", "diario"]:
        raise HTTPException(
            status_code=400,
            detail="Tipo deve ser 'completo' ou 'diario'"
        )
    
    # Determinar sites a processar
    sites_para_processar = request.sites if request.sites else list(SITES_DISPONIVEIS.keys())
    
    # Validar sites
    sites_invalidos = [s for s in sites_para_processar if s not in SITES_DISPONIVEIS]
    if sites_invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Sites inválidos: {', '.join(sites_invalidos)}"
        )
    
    # Criar job
    job_id = f"scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    scraping_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "sites_processados": [],
        "sites_pendentes": sites_para_processar.copy(),
        "total_produtos": 0,
        "message": "Scraping iniciado",
        "started_at": datetime.now(),
        "completed_at": None,
        "errors": [],
        "tipo": request.tipo,
        "current_site": None
    }
    
    # Adicionar tarefa em background
    background_tasks.add_task(
        executar_scraping_completo,
        job_id,
        sites_para_processar,
        request.tipo
    )
    
    return {
        "message": "Scraping iniciado com sucesso",
        "job_id": job_id,
        "status": "pending",
        "sites_total": len(sites_para_processar),
        "sites": sites_para_processar,
        "tipo": request.tipo
    }

@router.get("/status/{job_id}", response_model=ScrapingStatus)
async def obter_status_scraping(job_id: str):
    """
    Obter status de um job de scraping.
    
    **Retorna:**
    - Status atual do job
    - Sites processados e pendentes
    - Erros (se houver)
    """
    if job_id not in scraping_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} não encontrado"
        )
    
    job = scraping_jobs[job_id]
    
    return ScrapingStatus(
        job_id=job["job_id"],
        status=job["status"],
        sites_processados=job["sites_processados"],
        sites_pendentes=job["sites_pendentes"],
        total_produtos=job["total_produtos"],
        message=job["message"],
        started_at=job["started_at"],
        completed_at=job.get("completed_at"),
        errors=job["errors"]
    )

@router.get("/jobs", response_model=dict)
async def listar_jobs():
    """
    Listar todos os jobs de scraping.
    
    **Retorna:**
    - Lista de todos os jobs criados
    - Status de cada job
    """
    return {
        "total_jobs": len(scraping_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "started_at": job["started_at"],
                "sites_total": len(job["sites_processados"]) + len(job["sites_pendentes"]),
                "sites_concluidos": len(job["sites_processados"])
            }
            for job_id, job in scraping_jobs.items()
        ]
    }

@router.delete("/jobs/{job_id}", status_code=204)
async def cancelar_job(job_id: str):
    """
    Cancelar ou remover um job de scraping.
    
    **Atenção:** Não cancela processos em execução, apenas remove do histórico.
    """
    if job_id not in scraping_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} não encontrado"
        )
    
    del scraping_jobs[job_id]
    return None

@router.post("/test/{site}", response_model=dict)
async def testar_scraper(site: str, tipo: str = "completo"):
    """
    Testar scraper de um site específico (modo síncrono para debug).
    
    **Atenção:** Esta rota executa de forma síncrona e pode demorar.
    """
    if site not in SITES_DISPONIVEIS:
        raise HTTPException(
            status_code=404,
            detail=f"Site '{site}' não encontrado"
        )
    
    job_id = f"test_{site}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    scraping_jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "sites_processados": [],
        "sites_pendentes": [site],
        "total_produtos": 0,
        "message": f"Testando {site}",
        "started_at": datetime.now(),
        "completed_at": None,
        "errors": []
    }
    
    await executar_scraper(site, tipo, job_id)
    
    return {
        "message": f"Teste do scraper {site} concluído",
        "job_id": job_id,
        "status": scraping_jobs[job_id]["status"],
        "errors": scraping_jobs[job_id]["errors"]
    }
