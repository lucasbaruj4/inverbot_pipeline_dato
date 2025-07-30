from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import requests
from inverbot_pipeline_dato.data import data_source 
from crewai_tools import (
    # SerperDevTool,
    FirecrawlScrapeWebsiteTool,
    FirecrawlCrawlWebsiteTool
)
from crewai.tools import tool

# serper_dev_tool = SerperDevTool()



@CrewBase
class InverbotPipelineDato():
    """InverbotPipelineDato crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    model_llm = os.environ['MODEL']
    model_embedder = os.environ['EMBEDDER']
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    
    from crewai_tools import tool
import requests
import os

@tool("Firecrawl Web Scraper")
def firecrawl_scrape(url_and_description: str) -> str:
    """Base Firecrawl scraper. Input format: 'URL|Description'
    Example: 'https://example.com|Website description'"""
    
    parts = url_and_description.split("|", 1)
    if len(parts) != 2:
        return "Error: Invalid format. Use: URL|Description"
    
    url, description = parts
    api_key = os.getenv("FIRECRAWL_API_KEY")
    
    if not api_key:
        return "Error: Please set FIRECRAWL_API_KEY environment variable"
    
    try:
        response = requests.post(
            "https://api.firecrawl.dev/v0/scrape",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": url}
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("data", {}).get("markdown", "No content found")
            return f"{description}\n\nScraped content:\n{content}"
        else:
            return f"Error: Firecrawl returned status {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

# 1. Balances de Empresas
@tool("BVA Emisores Scraper")
def scrape_bva_emisores() -> str:
    """Scrapes BVA emisores listing page. Contains list of issuers, balances, prospectuses, risk analysis and relevant facts. Content types: EXCEL, PDF, TEXT"""
    return firecrawl_scrape(
        "https://www.bolsadevalores.com.py/listado-de-emisores/|Página de listado de emisores de la BVA, contiene un listado de emisores, cuando se selecciona un emisor en específico, se pueden encontrar balances, prospectos, análisis de riesgo y hechos relevantes del emisor en cuestión."
    )

# 2. Movimientos Diarios
@tool("BVA Daily Reports Scraper")
def scrape_bva_daily() -> str:
    """Scrapes BVA daily market movements reports. Content type: JSON"""
    return firecrawl_scrape(
        "https://www.bolsadevalores.com.py/informes-diarios/|Informes diarios de la BVA con movimientos del mercado."
    )

# 3. Volumen Mensual
@tool("BVA Monthly Reports Scraper")
def scrape_bva_monthly() -> str:
    """Scrapes BVA monthly reports including PDFs and structured data. Content types: TEXT, PDF, JSON"""
    return firecrawl_scrape(
        "https://www.bolsadevalores.com.py/informes-mensuales/|Informes mensuales de la BVA, incluyendo PDFs y datos estructurados."
    )

# 4. Resumen Anual
@tool("BVA Annual Reports Scraper")
def scrape_bva_annual() -> str:
    """Scrapes BVA annual reports in PDF format. Content types: TEXT, PDF"""
    return firecrawl_scrape(
        "https://www.bolsadevalores.com.py/informes-anuales/|Informes anuales de la BVA en formato PDF."
    )

# 5. Contexto Macroeconómico
@tool("Paraguay Open Data Scraper")
def scrape_datos_gov() -> str:
    """Scrapes Paraguay's official open data portal with macroeconomic data from BCP and other institutions. Content types: TEXT, PDF, EXCEL, JSON"""
    return firecrawl_scrape(
        "https://www.datos.gov.py/|Portal oficial de datos abiertos de Paraguay que incluye datos macroeconómicos del BCP y otras instituciones."
    )

# 6. Estadísticas Macroeconómicas (INE)
@tool("INE Statistics Scraper")
def scrape_ine_main() -> str:
    """Scrapes National Statistics Institute with macroeconomic data and official statistics. Content types: TEXT, PDF, EXCEL, JSON"""
    return firecrawl_scrape(
        "https://www.ine.gov.py/|Instituto Nacional de Estadística con datos macroeconómicos y estadísticas oficiales."
    )

# 7. Estadísticas Sociales
@tool("INE Social Publications Scraper")
def scrape_ine_social() -> str:
    """Scrapes INE portal for social statistics publications and data. Content types: PDF, EXCEL, PPT, TEXT"""
    return firecrawl_scrape(
        "https://www.ine.gov.py/vt/publicacion.php/|Portal del Instituto Nacional de Estadística (INE) para publicaciones y datos sociales."
    )

# 8. Contratos Públicos
@tool("Public Contracts Scraper")
def scrape_contrataciones() -> str:
    """Scrapes DNCP portal for public procurement and contracts data. Content type: TEXT"""
    return firecrawl_scrape(
        "https://www.contrataciones.gov.py/|Portal de la Dirección Nacional de Contrataciones Públicas (DNCP) para datos de licitaciones y contratos."
    )

# 9. Datos de Inversión
@tool("DNIT Investment Data Scraper")
def scrape_dnit_investment() -> str:
    """Scrapes DNIT portal section with information for investing in Paraguay. Content types: TEXT, PNG, PDF"""
    return firecrawl_scrape(
        "https://www.dnit.gov.py/web/portal-institucional/invertir-en-py|Sección del portal del DNIT con información para invertir en Paraguay."
    )

# 10. Informes Financieros (DNIT)
@tool("DNIT Financial Reports Scraper")
def scrape_dnit_financial() -> str:
    """Scrapes DNIT portal section with financial reports. Content types: TEXT, PDF"""
    return firecrawl_scrape(
        "https://www.dnit.gov.py/web/portal-institucional/informes-financieros|Sección del portal del DNIT con informes financieros."
    )
    
    
    @agent
    def extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['extractor'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                # serper_dev_tool,
                self.scrape_bolsa_valores
            ]
        )

    @agent
    def processor(self) -> Agent:
        return Agent(
            config=self.agents_config['processor'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )
        
    @agent
    def vector(self) -> Agent:
        return Agent(
            config=self.agents_config['vector'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )

    @agent
    def loader(self) -> Agent:
        return Agent(
            config=self.agents_config['loader'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )

    @task
    def extract_task(self) -> Task:
        return Task(
            config=self.tasks_config['extract_task'], 
            
        )

    @task
    def process_task(self) -> Task:
        return Task(
            config=self.tasks_config['process_task'], 
            context=[self.extract_task()]
        )
        
    @task
    def vectorize_task(self) -> Task:
        return Task(
            config=self.tasks_config['vectorize_task'], 
            context=[self.process_task(), self.extract_task()]
            
        )
        
    @task
    def load_task(self) -> Task:
        return Task(
            config=self.tasks_config['load_task'], 
            context=[self.process_task(), self.vectorize_task()]
        )
        
    @crew
    def crew(self) -> Crew:
        """Creates the InverbotPipelineDato crew"""

        return Crew(
            agents=self.agents, 
            tasks=self.tasks, 
            process=Process.sequential,
            verbose=True,
            max_rpm=5
        )
