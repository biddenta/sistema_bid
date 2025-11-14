from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Dict, Any, Optional
import json
import logging
from .tools.selenium_scraping_tool import SeleniumScrapingTool
from .tools.database_tool import DatabaseTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@CrewBase
class TinderCrew():
    """Sistema MultiAgente para Tratamento de Dados e Verificação de Match de Produtos"""

    agents: List[BaseAgent]
    tasks: List[Task]
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        super().__init__()
        self.selenium_tool = SeleniumScrapingTool()
        self.database_tool = DatabaseTool()

    # ===== AGENTES DA EQUIPE DE TRATAMENTO DE DADOS =====
    
    @agent
    def coordenador_dados(self) -> Agent:
        return Agent(
            config=self.agents_config['coordenador_dados'],
            tools=[self.database_tool],
            verbose=True,
            allow_delegation=True
        )

    # ===== AGENTES ESPECIALIZADOS DE ANÁLISE (RAMIFICAÇÃO) =====
    
    @agent
    def analista_nomes(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_nomes'],
            tools=[self.database_tool],
            verbose=True
        )
    
    @agent
    def analista_marcas(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_marcas'],
            tools=[self.database_tool],
            verbose=True
        )
    
    @agent
    def analista_precos(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_precos'],
            tools=[self.database_tool],
            verbose=True
        )
    
    @agent
    def analista_embalagens(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_embalagens'],
            tools=[self.database_tool],
            verbose=True
        )
    
    @agent
    def analista_categorias(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_categorias'],
            tools=[self.database_tool],
            verbose=True
        )
    
    @agent
    def analista_urls_qualidade(self) -> Agent:
        return Agent(
            config=self.agents_config['analista_urls_qualidade'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_tratador(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_tratador'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def scraper_selenium(self) -> Agent:
        return Agent(
            config=self.agents_config['scraper_selenium'],
            tools=[self.selenium_tool, self.database_tool],
            verbose=True
        )

    @agent
    def validador_final_dados(self) -> Agent:
        return Agent(
            config=self.agents_config['validador_final_dados'],
            tools=[self.database_tool],
            verbose=True
        )

    # ===== AGENTES DA EQUIPE DE VERIFICAÇÃO DE MATCH =====
    
    @agent
    def coordenador_match(self) -> Agent:
        return Agent(
            config=self.agents_config['coordenador_match'],
            tools=[self.database_tool],
            verbose=True,
            allow_delegation=True
        )

    @agent
    def verificador_nome(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_nome'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_marca(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_marca'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_embalagem(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_embalagem'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_avancado(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_avancado'],
            tools=[self.selenium_tool, self.database_tool],
            verbose=True
        )

    # ===== AGENTES DA EQUIPE DE VERIFICAÇÃO DE IDENTIDADE =====
    
    @agent
    def coordenador_identidade(self) -> Agent:
        return Agent(
            config=self.agents_config['coordenador_identidade'],
            tools=[self.database_tool],
            verbose=True,
            allow_delegation=True
        )

    @agent
    def verificador_identidade_tecnica(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_identidade_tecnica'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_identidade_visual(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_identidade_visual'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_identidade_farmaceutica(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_identidade_farmaceutica'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def verificador_identidade_comercial(self) -> Agent:
        return Agent(
            config=self.agents_config['verificador_identidade_comercial'],
            tools=[self.database_tool],
            verbose=True
        )

    @agent
    def auditoria_identidade_final(self) -> Agent:
        return Agent(
            config=self.agents_config['auditoria_identidade_final'],
            tools=[self.database_tool],
            verbose=True
        )

    # ===== TAREFAS DA EQUIPE DE TRATAMENTO DE DADOS =====
    
    @task
    def coordenacao_inicial(self) -> Task:
        return Task(
            config=self.tasks_config['coordenacao_inicial'],
            agent=self.coordenador_dados()
        )

    # ===== TAREFAS ESPECIALIZADAS DE ANÁLISE (RAMIFICAÇÃO) =====
    
    @task
    def analise_nomes_produtos(self) -> Task:
        return Task(
            config=self.tasks_config['analise_nomes_produtos'],
            agent=self.analista_nomes()
        )
    
    @task
    def analise_marcas_produtos(self) -> Task:
        return Task(
            config=self.tasks_config['analise_marcas_produtos'],
            agent=self.analista_marcas()
        )
    
    @task
    def analise_precos_produtos(self) -> Task:
        return Task(
            config=self.tasks_config['analise_precos_produtos'],
            agent=self.analista_precos()
        )
    
    @task
    def analise_embalagens_produtos(self) -> Task:
        return Task(
            config=self.tasks_config['analise_embalagens_produtos'],
            agent=self.analista_embalagens()
        )
    
    @task
    def analise_categorias_produtos(self) -> Task:
        return Task(
            config=self.tasks_config['analise_categorias_produtos'],
            agent=self.analista_categorias()
        )
    
    @task
    def analise_urls_qualidade(self) -> Task:
        return Task(
            config=self.tasks_config['analise_urls_qualidade'],
            agent=self.analista_urls_qualidade()
        )

    @task
    def verificacao_tratamento(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_tratamento'],
            agent=self.verificador_tratador()
        )

    @task
    def scraping_dinamico(self) -> Task:
        return Task(
            config=self.tasks_config['scraping_dinamico'],
            agent=self.scraper_selenium()
        )

    @task
    def validacao_final_dados(self) -> Task:
        return Task(
            config=self.tasks_config['validacao_final_dados'],
            agent=self.validador_final_dados()
        )

    # ===== TAREFAS DA EQUIPE DE VERIFICAÇÃO DE MATCH =====
    
    @task
    def coordenacao_match(self) -> Task:
        return Task(
            config=self.tasks_config['coordenacao_match'],
            agent=self.coordenador_match()
        )

    @task
    def verificacao_nomes(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_nomes'],
            agent=self.verificador_nome()
        )

    @task
    def verificacao_marcas(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_marcas'],
            agent=self.verificador_marca()
        )

    @task
    def verificacao_embalagens(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_embalagens'],
            agent=self.verificador_embalagem()
        )

    @task
    def verificacao_avancada(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_avancada'],
            agent=self.verificador_avancado()
        )

    @task
    def consolidacao_match_final(self) -> Task:
        return Task(
            config=self.tasks_config['consolidacao_match_final'],
            agent=self.coordenador_match(),
            output_file='match_results.json'
        )

    # ===== TAREFAS DA EQUIPE DE VERIFICAÇÃO DE IDENTIDADE =====
    
    @task
    def coordenacao_verificacao_identidade(self) -> Task:
        return Task(
            config=self.tasks_config['coordenacao_verificacao_identidade'],
            agent=self.coordenador_identidade()
        )

    @task
    def verificacao_identidade_tecnica(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_identidade_tecnica'],
            agent=self.verificador_identidade_tecnica()
        )

    @task
    def verificacao_identidade_visual(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_identidade_visual'],
            agent=self.verificador_identidade_visual()
        )

    @task
    def verificacao_identidade_farmaceutica(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_identidade_farmaceutica'],
            agent=self.verificador_identidade_farmaceutica()
        )

    @task
    def verificacao_identidade_comercial(self) -> Task:
        return Task(
            config=self.tasks_config['verificacao_identidade_comercial'],
            agent=self.verificador_identidade_comercial()
        )

    @task
    def tarefa_auditoria_identidade_final(self) -> Task:
        return Task(
            config=self.tasks_config['auditoria_identidade_final'],
            agent=self.auditoria_identidade_final(),
            output_file='identity_verification_results.json'
        )

    # ===== CREWS ESPECIALIZADAS =====

    @crew
    def equipe_tratamento_dados(self) -> Crew:
        """Cria a equipe especializada em tratamento de dados"""
        
        # Lista de agentes da equipe de tratamento (com especialistas)
        data_agents = [
            self.coordenador_dados(),
            # Agentes especializados de análise (ramificação)
            self.analista_nomes(),
            self.analista_marcas(),
            self.analista_precos(),
            self.analista_embalagens(),
            self.analista_categorias(),
            self.analista_urls_qualidade(),
            # Agentes de tratamento e validação
            self.verificador_tratador(),
            self.scraper_selenium(),
            self.validador_final_dados()
        ]
        
        # Lista de tarefas da equipe de tratamento (com especialistas)
        data_tasks = [
            self.coordenacao_inicial(),
            # Tarefas especializadas de análise (paralelas)
            self.analise_nomes_produtos(),
            self.analise_marcas_produtos(),
            self.analise_precos_produtos(),
            self.analise_embalagens_produtos(),
            self.analise_categorias_produtos(),
            self.analise_urls_qualidade(),
            # Tarefas de tratamento e validação (sequenciais)
            self.verificacao_tratamento(),
            self.scraping_dinamico(),
            self.validacao_final_dados()
        ]

        return Crew(
            agents=data_agents,
            tasks=data_tasks,
            process=Process.sequential,
            verbose=True,
            full_output=True
        )

    @crew
    def equipe_verificacao_match(self) -> Crew:
        """Cria a equipe especializada em verificação de match"""
        
        # Lista de agentes da equipe de match
        match_agents = [
            self.coordenador_match(),
            self.verificador_nome(),
            self.verificador_marca(),
            self.verificador_embalagem(),
            self.verificador_avancado()
        ]
        
        # Lista de tarefas da equipe de match
        match_tasks = [
            self.coordenacao_match(),
            self.verificacao_nomes(),
            self.verificacao_marcas(),
            self.verificacao_embalagens(),
            self.verificacao_avancada(),
            self.consolidacao_match_final()
        ]

        return Crew(
            agents=match_agents,
            tasks=match_tasks,
            process=Process.sequential,
            verbose=True,
            full_output=True
        )

    @crew
    def equipe_verificacao_identidade(self) -> Crew:
        """Cria a equipe especializada em verificação de identidade de produtos"""
        
        # Lista de agentes da equipe de verificação de identidade
        identity_agents = [
            self.coordenador_identidade(),
            self.verificador_identidade_tecnica(),
            self.verificador_identidade_visual(),
            self.verificador_identidade_farmaceutica(),
            self.verificador_identidade_comercial(),
            self.auditoria_identidade_final()
        ]
        
        # Lista de tarefas da equipe de verificação de identidade
        identity_tasks = [
            self.coordenacao_verificacao_identidade(),
            self.verificacao_identidade_tecnica(),
            self.verificacao_identidade_visual(),
            self.verificacao_identidade_farmaceutica(),
            self.verificacao_identidade_comercial(),
            self.tarefa_auditoria_identidade_final()
        ]

        return Crew(
            agents=identity_agents,
            tasks=identity_tasks,
            process=Process.sequential,
            verbose=True,
            full_output=True
        )

    @crew
    def crew(self) -> Crew:
        """Crew principal que combina ambas as equipes (para compatibilidade)"""
        
        # Combina todos os agentes (incluindo especialistas e verificação de identidade)
        all_agents = [
            self.coordenador_dados(),
            # Agentes especializados de análise
            self.analista_nomes(),
            self.analista_marcas(),
            self.analista_precos(),
            self.analista_embalagens(),
            self.analista_categorias(),
            self.analista_urls_qualidade(),
            # Outros agentes de tratamento
            self.verificador_tratador(),
            self.scraper_selenium(),
            self.validador_final_dados(),
            # Agentes de verificação de match
            self.coordenador_match(),
            self.verificador_nome(),
            self.verificador_marca(),
            self.verificador_embalagem(),
            self.verificador_avancado(),
            # Agentes de verificação de identidade
            self.coordenador_identidade(),
            self.verificador_identidade_tecnica(),
            self.verificador_identidade_visual(),
            self.verificador_identidade_farmaceutica(),
            self.verificador_identidade_comercial(),
            self.auditoria_identidade_final()
        ]
        
        # Combina todas as tarefas (incluindo especializadas e verificação de identidade)
        all_tasks = [
            self.coordenacao_inicial(),
            # Tarefas especializadas de análise
            self.analise_nomes_produtos(),
            self.analise_marcas_produtos(),
            self.analise_precos_produtos(),
            self.analise_embalagens_produtos(),
            self.analise_categorias_produtos(),
            self.analise_urls_qualidade(),
            self.verificacao_tratamento(),
            self.scraping_dinamico(),
            self.validacao_final_dados(),
            self.coordenacao_match(),
            self.verificacao_nomes(),
            self.verificacao_marcas(),
            self.verificacao_embalagens(),
            self.verificacao_avancada(),
            self.consolidacao_match_final(),
            # Tarefas de verificação de identidade
            self.coordenacao_verificacao_identidade(),
            self.verificacao_identidade_tecnica(),
            self.verificacao_identidade_visual(),
            self.verificacao_identidade_farmaceutica(),
            self.verificacao_identidade_comercial(),
            self.tarefa_auditoria_identidade_final()
        ]

        return Crew(
            agents=all_agents,
            tasks=all_tasks,
            process=Process.sequential,
            verbose=True,
            full_output=True
        )

    # ===== MÉTODOS DE CONTROLE CONDICIONAL =====

    def should_trigger_selenium_scraping(self, coordination_result: str) -> bool:
        """Determina se deve acionar scraping Selenium baseado no resultado da coordenação"""
        try:
            if isinstance(coordination_result, str):
                # Procura por indicadores de necessidade de scraping
                indicators = [
                    "scraping adicional",
                    "selenium necessário",
                    "javascript detectado",
                    "dados faltantes",
                    "informações incompletas",
                    "campos vazios"
                ]
                
                result_lower = coordination_result.lower()
                return any(indicator in result_lower for indicator in indicators)
                
        except Exception as e:
            logger.error(f"Erro ao avaliar necessidade de scraping: {e}")
        
        return False

    def should_trigger_advanced_verification(self, match_results: str) -> bool:
        """Determina se deve acionar verificação avançada baseado nos resultados de match"""
        try:
            if isinstance(match_results, str):
                # Procura por indicadores de necessidade de verificação avançada
                indicators = [
                    "score baixo",
                    "dúvida",
                    "inconclusivo",
                    "verificação manual",
                    "conflito detectado",
                    "necessita confirmação"
                ]
                
                result_lower = match_results.lower()
                return any(indicator in result_lower for indicator in indicators)
                
        except Exception as e:
            logger.error(f"Erro ao avaliar necessidade de verificação avançada: {e}")
        
        return False

    def execute_data_treatment_pipeline(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o pipeline completo de tratamento de dados com controle condicional"""
        logger.info("🚀 Iniciando Pipeline de Tratamento de Dados")
        
        try:
            # Executar equipe de tratamento de dados
            data_crew = self.equipe_tratamento_dados()
            data_result = data_crew.kickoff(inputs=inputs)
            
            logger.info("✅ Pipeline de Tratamento de Dados concluído")
            return {
                "success": True,
                "data_treatment_result": data_result,
                "next_stage": "match_verification"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Pipeline de Tratamento de Dados: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "data_treatment"
            }

    def execute_match_verification_pipeline(self, treated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o pipeline completo de verificação de match"""
        logger.info("🎯 Iniciando Pipeline de Verificação de Match")
        
        try:
            # Preparar inputs para a equipe de match
            match_inputs = {
                "treated_data": treated_data,
                **treated_data.get("inputs", {})
            }
            
            # Executar equipe de verificação de match
            match_crew = self.equipe_verificacao_match()
            match_result = match_crew.kickoff(inputs=match_inputs)
            
            logger.info("✅ Pipeline de Verificação de Match concluído")
            return {
                "success": True,
                "match_verification_result": match_result,
                "final_stage": True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Pipeline de Verificação de Match: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "match_verification"
            }

    def execute_identity_verification_pipeline(self, matched_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o pipeline de verificação de identidade de produtos"""
        logger.info("🔍 Iniciando Pipeline de Verificação de Identidade")
        
        try:
            # Preparar inputs para a equipe de verificação de identidade
            identity_inputs = {
                "matched_data": matched_data,
                **matched_data.get("inputs", {})
            }
            
            # Executar equipe de verificação de identidade
            identity_crew = self.equipe_verificacao_identidade()
            identity_result = identity_crew.kickoff(inputs=identity_inputs)
            
            logger.info("✅ Pipeline de Verificação de Identidade concluído")
            return {
                "success": True,
                "identity_verification_result": identity_result,
                "verified_products": True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Pipeline de Verificação de Identidade: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "identity_verification"
            }

    def execute_full_pipeline(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Executa todo o pipeline de tratamento, match e verificação de identidade"""
        logger.info("🌟 Iniciando Pipeline Completo - Tratamento + Match + Verificação de Identidade")
        
        # Etapa 1: Tratamento de Dados
        data_result = self.execute_data_treatment_pipeline(inputs)
        
        if not data_result.get("success", False):
            return data_result
        
        # Etapa 2: Verificação de Match
        match_result = self.execute_match_verification_pipeline(data_result)
        
        if not match_result.get("success", False):
            return match_result
        
        # Etapa 3: Verificação de Identidade (NOVA!)
        identity_result = self.execute_identity_verification_pipeline(match_result)
        
        # Consolidar resultados finais
        final_result = {
            "pipeline_success": identity_result.get("success", False),
            "data_treatment": data_result,
            "match_verification": match_result,
            "identity_verification": identity_result,
            "verified_products_ready": identity_result.get("verified_products", False),
            "timestamp": str(json.dumps({"timestamp": "now"}))
        }
        
        if final_result["pipeline_success"]:
            logger.info("� Pipeline Completo com Verificação de Identidade executado com sucesso!")
        else:
            logger.error("💥 Pipeline Completo falhou")
        
        return final_result

    def execute_legacy_pipeline(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Executa pipeline legado (sem verificação de identidade) para compatibilidade"""
        logger.info("🔄 Iniciando Pipeline Legado - Tratamento + Match")
        
        # Etapa 1: Tratamento de Dados
        data_result = self.execute_data_treatment_pipeline(inputs)
        
        if not data_result.get("success", False):
            return data_result
        
        # Etapa 2: Verificação de Match
        match_result = self.execute_match_verification_pipeline(data_result)
        
        # Consolidar resultados finais
        final_result = {
            "pipeline_success": match_result.get("success", False),
            "data_treatment": data_result,
            "match_verification": match_result,
            "timestamp": str(json.dumps({"timestamp": "now"}))
        }
        
        if final_result["pipeline_success"]:
            logger.info("🎉 Pipeline Legado executado com sucesso!")
        else:
            logger.error("💥 Pipeline Legado falhou")
        
        return final_result
