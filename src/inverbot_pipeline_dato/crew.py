import datetime
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import json
import requests
from supabase import create_client, Client
from pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
elif os.path.exists(".env"):
    load_dotenv(".env")
from inverbot_pipeline_dato.data import data_source 
from crewai_tools import (
    # SerperDevTool,
    FirecrawlScrapeWebsiteTool,
    FirecrawlCrawlWebsiteTool
)
from crewai.tools import tool
import requests
import os

# serper_dev_tool = SerperDevTool()


def firecrawl_scrape(url, prompt, schema, test_mode=True):
    """Base Firecrawl scraper with  JSON schema support"""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    
    if not api_key:
        return "Error: Please set FIRECRAWL_API_KEY environment variable"
    
    try:
        # Create a copy of schema first to avoid modifying original
        if test_mode and schema and "properties" in schema:
            import copy
            schema = copy.deepcopy(schema)
            for prop_name, prop_value in schema["properties"].items():
                if "items" in prop_value and prop_value["type"] == "array":
                    prop_value["maxItems"] = 3
        
        payload = {
            "url": url,
            "formats": ["json"],
            "jsonOptions": {
                "prompt": prompt,
                "systemPrompt": "You're a specialized web scraper extracting structured data with raw content. For each structured item, extract required fields according to the schema and include long versions of structured data, like a whole report from where a singular data has been extracted, where available.",
                "schema": schema
            }
        }
        if test_mode:
            payload["onlyMainContent"] = True
            payload["timeout"] = 10000
            payload["removeBase64Images"] = True
            payload["blockAds"] = True
            
            
            
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return json.dumps(data.get('data'), indent=2, ensure_ascii=False)
            else:
                return f"No se encontraron datos en {url}"
        else:
            return f"Error: Firecrawl returned status {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def firecrawl_crawl(url, prompt, schema, test_mode=True):
    '''Firecrawl crawler with JSON schema support"'''
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return f"Please set up your environmental API under 'FIRECRAWL_API_KEY'"
    
    try:
        # Create a copy of schema first to avoid modifying original
        if test_mode and schema and "properties" in schema:
            import copy
            schema = copy.deepcopy(schema)
            for prop_name, prop_value in schema["properties"].items():
                if "items" in prop_value and prop_value["type"] == "array":
                    prop_value["maxItems"] = 3
        
        payload = {
            "url": url,
            "scrapeOptions":{
                "formats":["json"],
                "jsonOptions":{
                "prompt": prompt,
                "systemPrompt": "You're a specialized web crawler extracting structured data with raw content. For each structured item, extract required fields according to the schema and include long versions of structured data, like a whole report from where a singular data has been extracted, where available.",
                "schema": schema
            }
            }
        }
        if test_mode:
            payload["maxDepth"] = 1
            payload["maxDiscoveryDepth"] = 1
            payload["limit"] = 3
            payload["allowExternalLinks"] = False
            payload["allowBackwardLinks"] = False
            payload["scrapeOptions"]["onlyMainContent"] = True
            payload["scrapeOptions"]["timeout"] = 10000
            payload["scrapeOptions"]["removeBase64Images"] = True
            payload["scrapeOptions"]["blockAds"] = True
            
            
            
        response = requests.post(
            "https://api.firecrawl.dev/v1/crawl",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return json.dumps(data.get('data'), indent=2, ensure_ascii=False)
            else:
                return f"No se encontraron datos en {url}"
        else:
            return f"Error: Firecrawl returned status {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error {str(e)}"        
    

@CrewBase
class InverbotPipelineDato():
    """InverbotPipelineDato crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    model_llm = os.environ['MODEL']
    model_embedder = os.environ['EMBEDDER']
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    test_mode = True # Modo de prueba para extractos chicos
    
    # Performance tracking variables
    def __init__(self):
        super().__init__()
        self.performance_metrics = {
            "pipeline_start_time": None,
            "pipeline_end_time": None,
            "agents_performance": {},
            "tasks_performance": {},
            "token_usage": {
                "total_tokens": 0,
                "firecrawl_credits": 0,
                "embedding_calls": 0
            },
            "component_status": {
                "extractor": {"status": "pending", "tools_used": [], "records_extracted": 0},
                "processor": {"status": "pending", "tools_used": [], "records_processed": 0},
                "vector": {"status": "pending", "tools_used": [], "vectors_created": 0},
                "loader": {"status": "pending", "tools_used": [], "records_loaded": 0}
            },
            "errors": [],
            "warnings": []
        }
    
    def log_performance(self, message: str, level: str = "INFO"):
        """Log performance message with timestamp"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
        if level == "ERROR":
            self.performance_metrics["errors"].append(f"[{timestamp}] {message}")
        elif level == "WARNING":
            self.performance_metrics["warnings"].append(f"[{timestamp}] {message}")
    
    def track_agent_performance(self, agent_name: str, task_name: str, start_time: float, end_time: float, records_count: int = 0):
        """Track individual agent performance"""
        duration = end_time - start_time
        
        if agent_name not in self.performance_metrics["agents_performance"]:
            self.performance_metrics["agents_performance"][agent_name] = []
            
        self.performance_metrics["agents_performance"][agent_name].append({
            "task": task_name,
            "duration_seconds": round(duration, 2),
            "records_processed": records_count,
            "timestamp": datetime.datetime.fromtimestamp(start_time).isoformat()
        })
        
        # Update component status
        if agent_name in self.performance_metrics["component_status"]:
            self.performance_metrics["component_status"][agent_name]["status"] = "completed"
            if agent_name == "extractor":
                self.performance_metrics["component_status"][agent_name]["records_extracted"] += records_count
            elif agent_name == "processor":
                self.performance_metrics["component_status"][agent_name]["records_processed"] += records_count
            elif agent_name == "vector":
                self.performance_metrics["component_status"][agent_name]["vectors_created"] += records_count
            elif agent_name == "loader":
                self.performance_metrics["component_status"][agent_name]["records_loaded"] += records_count
        
        self.log_performance(f"Agent '{agent_name}' completed '{task_name}' in {duration:.2f}s, processed {records_count} records")
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        if self.performance_metrics["pipeline_start_time"] and self.performance_metrics["pipeline_end_time"]:
            total_duration = self.performance_metrics["pipeline_end_time"] - self.performance_metrics["pipeline_start_time"]
        else:
            total_duration = 0
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"output/test_results/performance_report_{timestamp}.md"
        
        os.makedirs("output/test_results", exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# InverBot Pipeline Performance Report\n\n")
            f.write(f"**Generated**: {datetime.datetime.now().isoformat()}\n")
            f.write(f"**Test Mode**: {'ENABLED' if self.test_mode else 'DISABLED'}\n")
            f.write(f"**Total Pipeline Duration**: {total_duration:.2f} seconds\n\n")
            
            # Component Status Overview
            f.write("## Component Status Overview\n\n")
            for component, status in self.performance_metrics["component_status"].items():
                status_icon = "[COMPLETED]" if status["status"] == "completed" else "[PENDING]" if status["status"] == "pending" else "[FAILED]"
                f.write(f"- **{component.title()}**: {status_icon} {status['status'].title()}\n")
                if component == "extractor":
                    f.write(f"  - Records Extracted: {status['records_extracted']}\n")
                elif component == "processor":
                    f.write(f"  - Records Processed: {status['records_processed']}\n")
                elif component == "vector":
                    f.write(f"  - Vectors Created: {status['vectors_created']}\n")
                elif component == "loader":
                    f.write(f"  - Records Loaded: {status['records_loaded']}\n")
            f.write("\n")
            
            # Agent Performance Details
            f.write("## Agent Performance Details\n\n")
            for agent, tasks in self.performance_metrics["agents_performance"].items():
                f.write(f"### {agent.title()} Agent\n\n")
                total_agent_time = sum(task["duration_seconds"] for task in tasks)
                total_agent_records = sum(task["records_processed"] for task in tasks)
                f.write(f"**Total Time**: {total_agent_time:.2f}s | **Total Records**: {total_agent_records}\n\n")
                
                for task in tasks:
                    f.write(f"- **{task['task']}**: {task['duration_seconds']}s ({task['records_processed']} records)\n")
                f.write("\n")
            
            # Token Usage
            f.write("## Resource Usage\n\n")
            f.write(f"- **Total Tokens**: {self.performance_metrics['token_usage']['total_tokens']}\n")
            f.write(f"- **Firecrawl Credits**: {self.performance_metrics['token_usage']['firecrawl_credits']}\n")
            f.write(f"- **Embedding API Calls**: {self.performance_metrics['token_usage']['embedding_calls']}\n\n")
            
            # Errors and Warnings
            if self.performance_metrics["errors"]:
                f.write("## Errors\n\n")
                for error in self.performance_metrics["errors"]:
                    f.write(f"- {error}\n")
                f.write("\n")
                
            if self.performance_metrics["warnings"]:
                f.write("## Warnings\n\n")
                for warning in self.performance_metrics["warnings"]:
                    f.write(f"- {warning}\n")
                f.write("\n")
                
            # Quick Verification Checklist
            f.write("## Quick Verification Checklist\n\n")
            f.write("### Data Flow Verification\n")
            f.write("- [ ] Extractor: Check raw extraction output files\n")
            f.write("- [ ] Processor: Verify structured data output\n")
            f.write("- [ ] Vector: Confirm chunking and metadata preparation\n")
            f.write("- [ ] Loader: Review test mode output files\n\n")
            
            f.write("### Quality Checks\n")
            f.write("- [ ] No critical errors in the pipeline\n")
            f.write("- [ ] Record counts make sense across stages\n")
            f.write("- [ ] Output files are properly formatted\n")
            f.write("- [ ] Performance metrics within acceptable ranges\n\n")
            
            f.write("### Next Steps\n")
            if self.test_mode:
                f.write("- [ ] Review all test output files in `output/test_results/`\n")
                f.write("- [ ] Verify data quality and completeness\n")
                f.write("- [ ] Set `test_mode = False` for production run\n")
            else:
                f.write("- [ ] Verify data loaded correctly in Supabase\n")
                f.write("- [ ] Check vector embeddings in Pinecone\n")
                f.write("- [ ] Run data integrity checks\n")
        
        self.log_performance(f"Performance report saved to: {report_file}")
        return report_file


    # 1. Balances de Empresas
    @tool("BVA Emisores Scraper")
    def scrape_bva_emisores(test_mode=True) -> str:
        """Scrapes BVA emisores listing page. Extracts raw content for processor agent to structure."""
        # Simple content-focused schema for raw extraction
        schema = {
            "type": "object",
            "properties": {
                "page_content": {"type": "string", "description": "All text content from the page"},
                "links": {"type": "array", "items": {"type": "string"}, "description": "All URLs found on the page"},
                "documents": {"type": "array", "items": {"type": "string"}, "description": "PDF or document URLs"},
                "metadata": {"type": "object", "additionalProperties": True, "description": "Page metadata and structure info"}
            },
            "required": ["page_content"]
        }
        
        url = "https://www.bolsadevalores.com.py/listado-de-emisores/"
        prompt = """Extract all content from the BVA emisores listing page for later processing:

        CONTENT TO CAPTURE:
        - All text content from the main page
        - All links (URLs) found on the page, especially those leading to individual emisor pages
        - Document URLs (PDFs, Excel files, etc.) for reports, balances, prospectuses
        - Any metadata about page structure and navigation elements

        CRAWLING INSTRUCTIONS:
        - Navigate through the full page including clicking 'Cargar Mas' buttons to load more emisors
        - Enter individual emisor pages to capture their content
        - Look for documents under sections like 'Balances', 'Prospectos', 'Calificaciones', 'Hechos de Relevancia'
        - Capture both the text content and document download links
        
        Focus on comprehensive content extraction rather than structured data formatting. The processor agent will handle structuring this raw content later."""
        
        return firecrawl_crawl(url, prompt, schema, test_mode)


    # 2. Movimientos Diarios
    @tool("BVA Daily Reports Scraper")
    def scrape_bva_daily(test_mode=True) -> str:
        """Scrapes BVA daily market movements reports. Extracts raw content for processor agent to structure."""
        # Simple content-focused schema for raw extraction
        schema = {
            "type": "object",
            "properties": {
                "page_content": {"type": "string", "description": "All text content from the page"},
                "links": {"type": "array", "items": {"type": "string"}, "description": "All URLs found on the page"},
                "documents": {"type": "array", "items": {"type": "string"}, "description": "PDF or document URLs"},
                "metadata": {"type": "object", "additionalProperties": True, "description": "Page metadata and structure info"}
            },
            "required": ["page_content"]
        }
                "Moneda": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_moneda": {"type": "integer"},
                            "codigo_moneda": {"type": "string"},
                            "nombre_moneda": {"type": "string"}
                        },
                        "required": ["codigo_moneda"]
                    }
                }
            },
            "required": ["Movimiento_Diario_Bolsa"]
        }
        
        url = "https://www.bolsadevalores.com.py/informes-diarios/"
        prompt = """Extrae la siguiente información de la página de informes diarios de la Bolsa de Valores de Asunción:

        1. Todos los movimientos diarios del mercado (Movimiento_Diario_Bolsa) con:
        - fecha_operacion: fecha de la operación
        - cantidad_operacion: volumen de la operación
        - información del instrumento (simbolo_instrumento, nombre_instrumento)
        - información del emisor (nombre_emisor)
        - información de la moneda (codigo_moneda, nombre_moneda)
        - precio_operacion: precio de la operación
        - precio_anterior_instrumento: precio anterior del instrumento
        - tasa_interes_nominal: tasa de interés (si aplica)
        - tipo_cambio: tipo de cambio (si aplica)
        - variacion_operacion: variación porcentual
        - volumen_gs_operacion: volumen en guaraníes

        2. Información de los instrumentos mencionados (Instrumento):
        - simbolo_instrumento: código del instrumento
        - nombre_instrumento: nombre completo
        - fecha_vencimiento_instrumento: fecha de vencimiento (si aplica)

        3. Información de las monedas utilizadas (Moneda):
        - codigo_moneda: código de la moneda
        - nombre_moneda: nombre completo de la moneda

        GUÍA DE SCRAPING:
        La página muestra una tabla con movimientos diarios del mercado bursátil. Navega por la tabla completa, extrayendo cada fila como un movimiento individual. La tabla probablemente tenga columnas para fecha, instrumento, emisor, cantidad, precio, variación, etc. Si hay paginación o botones para cargar más datos, asegúrate de extraer todos los movimientos disponibles.

        Para cada instrumento y moneda encontrados, extrae también sus detalles completos, manteniendo la relación con los movimientos correspondientes mediante IDs consistentes. Busca información adicional que pueda estar en tooltips o enlaces expandibles.

        No busques un informe general o título separado, ya que esta página contiene directamente la tabla de movimientos diarios. Concéntrate en extraer todos los datos estructurados de la tabla principal y cualquier información complementaria visible en la página.
        """
        
        return firecrawl_scrape(url, prompt, schema, test_mode)
    # 3. Volumen Mensual
    @tool("BVA Monthly Reports Scraper")
    def scrape_bva_monthly(test_mode=True) -> str:
        """Scrapes BVA monthly reports including PDFs and structured data."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "id_periodo": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {
                                "type": "object",
                                "properties": {
                                    "volumen_total": {"type": "number"},
                                    "variaciones": {"type": "array", "items": {"type": "object"}},
                                    "emisiones": {"type": "array", "items": {"type": "object"}}
                                }
                            },
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "fecha_publicacion", "url_descarga_original"]
                    }
                },
                "Periodo_Informe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_periodo": {"type": "integer"},
                            "nombre_periodo": {"type": "string"}
                        },
                        "required": ["nombre_periodo"]
                    }
                },
                "Dato_Macroeconomico": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_dato_macro": {"type": "integer"},
                            "id_informe": {"type": "integer"},
                            "indicador_nombre": {"type": "string"},
                            "fecha_dato": {"type": "string", "format": "date"},
                            "valor_numerico": {"type": "number"},
                            "unidad_medida": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "link_fuente_especifico": {"type": "string"},
                            "otras_propiedades_jsonb": {"type": "object", "additionalProperties": True},
                            "id_moneda": {"type": "integer"}
                        },
                        "required": ["indicador_nombre", "fecha_dato", "valor_numerico"]
                    }
                }
            },
            "required": ["Informe_General"]
        }
        
        url = "https://www.bolsadevalores.com.py/informes-mensuales/"
        prompt = """Extrae la siguiente información de la página de informes mensuales de la Bolsa de Valores de Asunción:

        1. Todos los informes mensuales disponibles (Informe_General) con:
        - titulo_informe: título completo del informe
        - id_tipo_informe: identificador del tipo de informe
        - id_frecuencia: identificador de frecuencia mensual
        - id_periodo: identificador del período (mes/año)
        - fecha_publicacion: fecha de publicación del informe
        - resumen_informe: resumen o descripción del informe
        - url_descarga_original: enlace de descarga del informe (PDF u otro formato)
        - detalles_informe_jsonb: datos estructurados del informe
        - contenido_raw: texto completo o resumen detallado del informe

        2. Información sobre los períodos mencionados (Periodo_Informe):
        - id_periodo: identificador único del período
        - nombre_periodo: nombre del período (ej. "Agosto 2025")

        3. Datos macroeconómicos específicos (Dato_Macroeconomico) que aparecen en los informes:
        - id_dato_macro: identificador único del dato
        - id_informe: referencia al informe donde aparece
        - indicador_nombre: nombre del indicador económico
        - fecha_dato: fecha a la que corresponde el dato
        - valor_numerico: valor del indicador
        - unidad_medida: unidad de medida utilizada
        - id_frecuencia: frecuencia del indicador
        - otras_propiedades_jsonb: propiedades adicionales del dato

        GUÍA DE CRAWLING:
        La página tiene una estructura compleja con múltiples secciones y tipos de informes. Sigue estos pasos:

        1. Primero, navega el menú lateral izquierdo "MENÚ DE INFORMES" que contiene diferentes categorías:
        - COMPARATIVAS
        - VARIACIONES
        - VOLUMEN NEGOCIADO
        - POR OPERACIONES
        - POR INSTRUMENTOS
        - EMISIONES REGISTRADAS
        - TOP 10 EMISORES

        2. Para cada categoría del menú, accede y extrae:
        - El título de la sección
        - El selector de mes (busca el dropdown "SELECCIONAR MES")
        - El botón "DESCARGAR PDF" para obtener la URL del informe completo
        - Los datos numéricos y estadísticos mostrados (como "VOLUMEN MENSUAL NEGOCIADO EN GS")
        - Las comparativas porcentuales (como "VS MES ANTERIOR: -100%")

        3. Explora las visualizaciones por categorías como:
        - "Por moneda" (USD, GS)
        - "Por mercado" (Mercado Primario, Mercado Secundario)
        - "Por instrumento" (Bonos, Acciones, Fondos de Inversión)

        4. Para cada mes disponible en el selector, repite el proceso para obtener datos históricos.

        5. Presta atención a los PDF descargables, ya que contienen información más detallada y estructurada que deberá ser extraída.

        Mantén la relación entre las tablas asignando IDs consistentes. Por ejemplo, si extraes datos de "Agosto 2025", asegúrate que todos los datos de ese período tengan el mismo id_periodo.
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)
    # 4. Resumen Anual
    @tool("BVA Annual Reports Scraper")
    def scrape_bva_annual(test_mode=True) -> str:
        """Scrapes BVA annual reports in PDF format."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "id_periodo": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "fecha_publicacion", "url_descarga_original"]
                    }
                },
                "Periodo_Informe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_periodo": {"type": "integer"},
                            "nombre_periodo": {"type": "string"}
                        },
                        "required": ["nombre_periodo"]
                    }
                }
            },
            "required": ["Informe_General"]
        }
        
        url = "https://www.bolsadevalores.com.py/informes-anuales/"
        prompt = """Extrae la siguiente información de la página de informes anuales de la Bolsa de Valores de Asunción:

        1. Todos los informes anuales disponibles (Informe_General) con:
        - titulo_informe: título del informe (ej. "Informe 2024", "Informe 2023", etc.)
        - id_tipo_informe: identificador del tipo de informe (para informes anuales)
        - id_frecuencia: identificador de frecuencia anual
        - id_periodo: identificador del período (año)
        - fecha_publicacion: año del informe como fecha
        - url_descarga_original: URL completa del enlace de descarga del PDF
        - contenido_raw: deja este campo vacío inicialmente, se llenará al procesar el PDF

        2. Información sobre los períodos anuales (Periodo_Informe):
        - id_periodo: identificador único del período
        - nombre_periodo: año del informe (ej. "2024", "2023", etc.)

        GUÍA DE SCRAPING:
        La página muestra una lista simple de enlaces de descarga para informes anuales, cada uno con un icono de descarga y el texto "Descargar Informe [AÑO]". Para cada informe visible:

        1. Extrae el título exacto del enlace (ej. "Descargar Informe 2024")
        2. Extrae el año del informe del título
        3. Captura la URL completa del enlace de descarga
        4. Asigna un id_tipo_informe consistente para todos los informes anuales
        5. Asigna un id_frecuencia consistente para frecuencia anual
        6. Genera un id_periodo único para cada año
        7. Formatea el año como fecha de publicación (ej. "2024" como "2024-01-01")

        Importante: 
        - Haz clic en el botón "Cargar más" al final de la página para obtener informes de años anteriores
        - No intentes extraer el contenido de los PDFs en esta fase, solo captura las URLs
        - La página muestra "MERCADO CERRADO: No hay datos para mostrar" en la parte superior, pero esto no afecta a los enlaces de informes

        No hay datos macroeconómicos visibles directamente en esta página, solo enlaces a los PDFs. Los datos macroeconómicos deberán extraerse al procesar los PDFs descargados en una fase posterior.

        Mantén la relación entre Informe_General y Periodo_Informe usando los mismos id_periodo.
        """
        
        return firecrawl_scrape(url, prompt, schema, test_mode)

    # 5. Contexto Macroeconómico
    @tool("Paraguay Open Data Scraper")
    def scrape_datos_gov(test_mode=True) -> str:
        """Scrapes Paraguay's official open data portal with macroeconomic data."""
        schema = {
            "type": "object",
            "properties": {
                "Dato_Macroeconomico": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_dato_macro": {"type": "integer"},
                            "id_informe": {"type": "integer"},
                            "indicador_nombre": {"type": "string"},
                            "fecha_dato": {"type": "string", "format": "date"},
                            "valor_numerico": {"type": "number"},
                            "unidad_medida": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "link_fuente_especifico": {"type": "string"},
                            "otras_propiedades_jsonb": {"type": "object", "additionalProperties": True},
                            "id_moneda": {"type": "integer"},
                            "id_emisor": {"type": "integer"},
                            "contexto_raw": {"type": "string"}
                        },
                        "required": ["indicador_nombre", "fecha_dato", "valor_numerico"]
                    }
                },
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "fecha_publicacion"]
                    }
                },
                "Unidad_Medida": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_unidad_medida": {"type": "integer"},
                            "simbolo": {"type": "string"},
                            "nombre_unidad": {"type": "string"}
                        },
                        "required": ["simbolo", "nombre_unidad"]
                    }
                },
                "Frecuencia": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_frecuencia": {"type": "integer"},
                            "nombre_frecuencia": {"type": "string"}
                        },
                        "required": ["nombre_frecuencia"]
                    }
                }
            },
            "required": ["Dato_Macroeconomico"]
        }
        
        url = "https://www.datos.gov.py/"
        prompt = """Extrae la siguiente información del portal de datos abiertos de Paraguay (datos.gov.py):

        1. Datos macroeconómicos (Dato_Macroeconomico) disponibles en las diferentes categorías, especialmente en:
        - Agricultura y Ganadería
        - Desarrollo Social
        - Industria, Comercio y Turismo
        - Trabajo y Empleo
        - Pobreza
        - Economía e identificación
        Incluye para cada dato:
        - indicador_nombre: nombre del indicador económico
        - fecha_dato: fecha a la que corresponde el dato
        - valor_numerico: valor del indicador
        - unidad_medida: unidad de medida utilizada
        - id_frecuencia: frecuencia del indicador
        - link_fuente_especifico: enlace directo a la fuente del dato
        - contexto_raw: descripción o contexto del indicador

        2. Informes y documentos (Informe_General) disponibles para descarga:
        - titulo_informe: título completo del documento
        - id_tipo_informe: tipo de informe o documento
        - fecha_publicacion: fecha de publicación
        - url_descarga_original: enlace de descarga
        - resumen_informe: descripción o resumen del contenido

        3. Unidades de medida (Unidad_Medida) utilizadas en los conjuntos de datos:
        - simbolo: símbolo de la unidad (ej. %, Gs., USD)
        - nombre_unidad: nombre completo de la unidad

        4. Frecuencias (Frecuencia) mencionadas para los datos:
        - nombre_frecuencia: tipo de frecuencia (ej. mensual, trimestral, anual)

        GUÍA DE CRAWLING:
        La página es un portal de datos abiertos del gobierno paraguayo con múltiples categorías temáticas. Para extraer la información:

        1. Navega por cada una de las categorías temáticas (iconos centrales):
        - Haz clic en cada icono/categoría (Agricultura, Desarrollo Social, etc.)
        - Dentro de cada categoría, explora los conjuntos de datos disponibles
        - Busca tablas, gráficos o documentos con datos macroeconómicos

        2. Presta especial atención a la sección "Historias y Noticias" que muestra eventos de capacitación sobre datos abiertos:
        - Estos eventos pueden contener enlaces a documentos e informes importantes
        - Explora cada noticia para encontrar enlaces a recursos adicionales

        3. Utiliza el menú superior "Conjuntos de datos" para acceder al catálogo completo de datos:
        - Filtra por términos económicos relevantes (inflación, PIB, tasas, etc.)
        - Examina metadatos de cada conjunto para identificar unidades y frecuencias

        4. Para cada conjunto de datos encontrado:
        - Registra los metadatos (título, fecha, descripción)
        - Extrae una muestra de los datos si están en formato tabular
        - Captura las unidades de medida y frecuencias mencionadas
        - Guarda enlaces a descargas disponibles (CSV, Excel, PDF)

        5. Busca informes analíticos o explicativos que acompañen a los datos:
        - Pueden estar en formatos PDF o como páginas web
        - Extrae resúmenes o descripciones para proporcionar contexto

        Asegúrate de explorar tanto la página principal como las secciones internas, ya que los datos más valiosos suelen estar varios niveles por debajo de la página de inicio.
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)
    # 6. Estadísticas Macroeconómicas (INE)
    @tool("INE Statistics Scraper")
    def scrape_ine_main(test_mode=True) -> str:
        """Scrapes National Statistics Institute with macroeconomic data and official statistics."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "fecha_publicacion"]
                    }
                },
                "Unidad_Medida": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_unidad_medida": {"type": "integer"},
                            "simbolo": {"type": "string"},
                            "nombre_unidad": {"type": "string"}
                        },
                        "required": ["simbolo"]
                    }
                },
                "Frecuencia": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_frecuencia": {"type": "integer"},
                            "nombre_frecuencia": {"type": "string"}
                        },
                        "required": ["nombre_frecuencia"]
                    }
                },
                "Tipo_Informe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_tipo_informe": {"type": "integer"},
                            "nombre_tipo_informe": {"type": "string"}
                        },
                        "required": ["nombre_tipo_informe"]
                    }
                }
            },
            "required": ["Informe_General"]
        }
        
        url = "https://www.ine.gov.py/"
        prompt = """Extrae la siguiente información del sitio web del Instituto Nacional de Estadística de Paraguay (INE):

        1. Informes y publicaciones estadísticas disponibles (Informe_General):
        - id_informe: identificador único del informe
        - id_tipo_informe: tipo de publicación (compendio, censo, informe especializado)
        - titulo_informe: título completo del documento
        - fecha_publicacion: fecha de publicación
        - resumen_informe: breve descripción o resumen visible
        - url_descarga_original: enlace de descarga del documento
        - detalles_informe_jsonb: información adicional relevante

        2. Tipos de informes disponibles (Tipo_Informe):
        - id_tipo_informe: identificador único del tipo
        - nombre_tipo_informe: nombre del tipo de informe (ej. "Compendio Estadístico", "Censo", "Atlas")

        3. Unidades de medida mencionadas (Unidad_Medida):
        - id_unidad_medida: identificador único de la unidad
        - simbolo: símbolo de la unidad (%, Gs., USD, etc.)
        - nombre_unidad: nombre completo de la unidad

        4. Frecuencias de publicación (Frecuencia):
        - id_frecuencia: identificador único de la frecuencia
        - nombre_frecuencia: tipo de frecuencia (ej. mensual, trimestral, anual)

        GUÍA DE CRAWLING:
        El sitio del INE tiene una estructura organizada con varias secciones clave para explorar:

        1. Sección de Publicaciones:
        - Explora la sección "Publicaciones" visible en la página principal
        - El "COMPENDIO ESTADÍSTICO 2023" es un documento clave que aparece destacado
        - Captura todos los enlaces "Ver documento" y botones de descarga
        - Registra los metadatos de cada publicación (título, fecha, descripción)

        2. Menús de navegación:
        - Explora las secciones "Estadística por Tema" y "Estadística por Fuente" 
        - Cada categoría temática contiene diferentes publicaciones y conjuntos de datos
        - Navega a través de todas las categorías y subcategorías disponibles

        3. Sección "Destacados":
        - Revisa todos los elementos en la sección "Destacados" del sitio
        - Incluye informes especiales como "Atlas sobre la Discapacidad" y "Censo Transparente"
        - Captura los enlaces a estos documentos especiales

        4. Datos Abiertos:
        - Explora la sección "Datos Abiertos" del menú principal
        - Registra los conjuntos de datos disponibles y sus metadatos
        - Captura enlaces a portales especializados como "Portal GEO Estadístico" y "Plataforma ODS"

        5. Para cada publicación encontrada:
        - Registra el título exacto, fecha y tipo de documento
        - Captura cualquier descripción o resumen visible
        - Guarda la URL de descarga del documento completo
        - Observa la periodicidad o frecuencia mencionada

        No intentes extraer directamente los datos macroeconómicos del contenido de los documentos en esta fase, solo los metadatos y enlaces de las publicaciones. El procesamiento de los datos dentro de los documentos se realizará en una fase posterior.
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)

    # 7. Estadísticas Sociales
    @tool("INE Social Publications Scraper")
    def scrape_ine_social(test_mode=True) -> str:
        """Scrapes INE portal for social statistics publications and data."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "id_periodo": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "url_descarga_original"]
                    }
                },
                "Tipo_Informe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_tipo_informe": {"type": "integer"},
                            "nombre_tipo_informe": {"type": "string"}
                        },
                        "required": ["nombre_tipo_informe"]
                    }
                },
                "Periodo_Informe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_periodo": {"type": "integer"},
                            "nombre_periodo": {"type": "string"}
                        },
                        "required": ["nombre_periodo"]
                    }
                }
            },
            "required": ["Informe_General"]
        }
        
        url = "https://www.ine.gov.py/vt/publicacion.php/"
        prompt = """Extrae la siguiente información del portal de publicaciones del INE Paraguay:

        1. Publicaciones estadísticas sociales disponibles (Informe_General):
        - id_informe: identificador único del informe
        - id_tipo_informe: categoría del informe según la estructura del sitio
        - titulo_informe: título completo de la publicación
        - fecha_publicacion: fecha de publicación si está disponible
        - url_descarga_original: enlace completo para descargar el documento
        - resumen_informe: breve descripción o resumen si está disponible
        - id_periodo: referencia al período que cubre la publicación

        2. Tipos de informes disponibles (Tipo_Informe):
        - id_tipo_informe: identificador único del tipo
        - nombre_tipo_informe: nombre de la categoría (ej. "Estadística Sociodemográfica", "Encuestas", "Censos")

        3. Períodos cubiertos por las publicaciones (Periodo_Informe):
        - id_periodo: identificador único del período
        - nombre_periodo: descripción del período (ej. "2017-2023", "2022", "Trimestral")

        GUÍA DE CRAWLING:
        El sitio del INE tiene una estructura de navegación jerárquica muy detallada con múltiples categorías y subcategorías:

        1. Enfócate en las secciones de estadísticas sociales que se ven en el menú:
        - "Estadística Sociodemográfica" y todas sus subcategorías:
            * Empleo
            * Educación
            * Pobreza
            * Vivienda y Hogar
            * Otros temas sociales
            * Ingresos
            * Tics
            * Salud
            * Población Indígena
            * Género
            * Niñez
            * Población Juvenil
            * Población

        2. Explora también estas secciones relacionadas:
        - "Encuestas" (especialmente la "Encuesta Permanente de Hogares")
        - "Censos" (especialmente el "Censo Nacional de Población y Viviendas 2012")
        - "Compendios Estadísticos" y "Anuario" bajo "Ambientes y otras estadísticas"

        3. Para cada enlace en estas secciones:
        - Haz clic y navega a la página de la publicación
        - Captura el título exacto del documento
        - Registra la fecha de publicación si está visible
        - Guarda la URL de descarga del documento
        - Extrae cualquier resumen o descripción disponible
        - Identifica el período que cubre (año, trimestre, etc.)
        - Asigna un tipo de informe basado en la categoría del menú

        4. Presta especial atención a:
        - "Encuesta Permanente de Hogares Continua (EPHC) Trimestral 2017-2023"
        - "Serie Comparable de Encuestas Permanentes de Hogares (EPH)"
        - "Encuesta Continua de Empleo (ECE)"
        - "Caracterización de las viviendas y los hogares CNPV2022"

        No intentes extraer los datos estadísticos específicos del contenido de los documentos en esta fase. Concéntrate en identificar y catalogar todas las publicaciones disponibles con sus metadatos.

        Mantén la relación entre Informe_General, Tipo_Informe y Periodo_Informe usando IDs consistentes.
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)

    # 8. Contratos Públicos
    @tool("Public Contracts Scraper")
    def scrape_contrataciones(test_mode=True) -> str:
        """Scrapes DNCP portal for public procurement and contracts data."""
        schema = {
            "type": "object",
            "properties": {
                "Licitacion_Contrato": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_licitacion_contrato": {"type": "integer"},
                            "id_emisor_adjudicado": {"type": "integer"},
                            "titulo": {"type": "string"},
                            "entidad_convocante": {"type": "string"},
                            "monto_adjudicado": {"type": "number"},
                            "id_moneda": {"type": "integer"},
                            "fecha_adjudicacion": {"type": "string", "format": "date"},
                            "detalles_contrato": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo"]
                    }
                },
                "Emisores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_emisor": {"type": "integer"},
                            "nombre_emisor": {"type": "string"},
                            "id_categoria_emisor": {"type": "integer"}
                        },
                        "required": ["nombre_emisor"]
                    }
                },
                "Moneda": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_moneda": {"type": "integer"},
                            "codigo_moneda": {"type": "string"},
                            "nombre_moneda": {"type": "string"}
                        },
                        "required": ["codigo_moneda"]
                    }
                }
            },
            "required": ["Licitacion_Contrato"]
        }
        
        url = "https://www.contrataciones.gov.py/"
        prompt = """Extrae la siguiente información del portal de Contrataciones Públicas de Paraguay:

        1. Licitaciones y contratos públicos (Licitacion_Contrato):
        - id_licitacion_contrato: identificador único de la licitación o contrato
        - titulo: título o descripción de la licitación/contrato
        - entidad_convocante: nombre de la entidad gubernamental que convoca
        - id_emisor_adjudicado: referencia al emisor adjudicado (cuando esté disponible)
        - monto_adjudicado: valor económico del contrato
        - id_moneda: referencia a la moneda utilizada
        - fecha_adjudicacion: fecha de adjudicación del contrato
        - detalles_contrato: información adicional relevante en formato JSON
        - contenido_raw: texto descriptivo o resumen del contrato si está disponible

        2. Empresas/Entidades adjudicadas (Emisores):
        - id_emisor: identificador único del emisor
        - nombre_emisor: nombre completo de la empresa o entidad
        - id_categoria_emisor: categoría del emisor si está disponible

        3. Monedas utilizadas (Moneda):
        - id_moneda: identificador único de la moneda
        - codigo_moneda: código de la moneda (ej. "USD", "PYG", "GS")
        - nombre_moneda: nombre completo de la moneda

        GUÍA DE CRAWLING:
        El portal de la DNCP tiene una estructura organizada con varias secciones clave para explorar:

        1. Sección de Licitaciones:
        - Accede a través del botón naranja "Licitaciones" en la página principal
        - Busca listados de licitaciones activas y adjudicadas
        - Captura detalles de cada licitación (título, entidad convocante, montos, fechas)
        - Registra las URLs a los documentos completos de las licitaciones

        2. Sección de Contratos:
        - Accede a través del botón naranja "Contratos" en la página principal
        - Explora los contratos adjudicados y en ejecución
        - Captura información detallada de cada contrato
        - Presta atención a los montos que aparecen en USD (como se ve en la estadística "USD 3.246")

        3. Sección de Proveedores:
        - Accede a través del botón "Proveedores" en la página principal
        - Recopila información sobre empresas y entidades adjudicadas
        - Captura detalles como nombre, categoría y otra información relevante
        - Verifica si hay información sobre sanciones a proveedores ("Sanciones a proveedores")
        
        Asegúrate de mantener las relaciones entre las tablas usando IDs consistentes. Por ejemplo, si un contrato menciona una empresa y una moneda específica, asigna el mismo id_emisor y id_moneda en las tablas correspondientes.
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)

    # 9. Datos de Inversión
    @tool("DNIT Investment Data Scraper")
    def scrape_dnit_investment(test_mode=True) -> str:
        """Scrapes DNIT portal section with information for investing in Paraguay."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe"]
                    }
                },
                "Dato_Macroeconomico": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_dato_macro": {"type": "integer"},
                            "id_informe": {"type": "integer"},
                            "indicador_nombre": {"type": "string"},
                            "fecha_dato": {"type": "string", "format": "date"},
                            "valor_numerico": {"type": "number"},
                            "unidad_medida": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "link_fuente_especifico": {"type": "string"},
                            "otras_propiedades_jsonb": {
                                "type": "object",
                                "properties": {
                                    "sector": {"type": "string"},
                                    "tipo_inversion": {"type": "string"},
                                    "region": {"type": "string"}
                                },
                                "additionalProperties": True
                            },
                            "id_moneda": {"type": "integer"},
                            "contexto_raw": {"type": "string"}
                        },
                        "required": ["indicador_nombre", "valor_numerico"]
                    }
                }
            },
            "required": ["Informe_General", "Dato_Macroeconomico"]
        }
        
        url = "https://www.dnit.gov.py/web/portal-institucional/invertir-en-py"
        prompt = """Extrae la siguiente información del portal de inversiones de la DNIT Paraguay:

        1. Informes y documentos sobre inversión en Paraguay (Informe_General):
        - id_informe: identificador único del informe
        - id_tipo_informe: tipo de informe (ej. reporte, guía, análisis)
        - titulo_informe: título completo del documento (ej. "Euromoney Paraguay Report")
        - resumen_informe: breve descripción del informe
        - fecha_publicacion: fecha de publicación si está disponible
        - url_descarga_original: enlace de descarga del documento
        - detalles_informe_jsonb: metadatos adicionales en formato JSON
        - contenido_raw: texto completo o resumen del informe

        2. Datos macroeconómicos y tasas impositivas (Dato_Macroeconomico):
        - id_dato_macro: identificador único del dato
        - id_informe: referencia al informe relacionado (si aplica)
        - indicador_nombre: nombre del indicador (ej. "Impuesto a la Renta Empresarial")
        - fecha_dato: fecha de vigencia o publicación del dato
        - valor_numerico: valor porcentual o numérico (ej. 10, 5, 15)
        - unidad_medida: referencia a la unidad (ej. porcentaje)
        - id_frecuencia: frecuencia de actualización del dato (si aplica)
        - link_fuente_especifico: URL de la fuente específica
        - otras_propiedades_jsonb: {
            "sector": sector económico relacionado,
            "tipo_inversion": tipo de inversión aplicable,
            "region": área geográfica si es específica
            }
        - id_moneda: referencia a la moneda (si aplica)
        - contexto_raw: texto explicativo completo que acompaña al dato

        GUÍA DE CRAWLING:
        El portal presenta información clave en forma de infografías interactivas y documentos descargables:

        1. Infografía principal de "Tasas mínimas impositivas":
        Extrae cada impuesto como un dato macroeconómico separado:
        
        a) IRE (Impuesto a la Renta Empresarial):
            - indicador_nombre: "Impuesto a la Renta Empresarial (IRE)"
            - valor_numerico: 10
            - unidad_medida: porcentaje
            - contexto_raw: Texto completo que explica este impuesto
        
        b) IDU (Impuesto a los Dividendos y las Utilidades):
            - indicador_nombre: "Impuesto a los Dividendos y las Utilidades (IDU) - Residentes"
            - valor_numerico: 5
            - unidad_medida: porcentaje
            - contexto_raw: Incluir la explicación completa
            
            - indicador_nombre: "Impuesto a los Dividendos y las Utilidades (IDU) - No Residentes"
            - valor_numerico: 15
            - unidad_medida: porcentaje
        
        c) IRP (Impuesto a la Renta Personal):
            - indicador_nombre: "Impuesto a la Renta Personal (IRP)"
            - valor_numerico: [tasas variables]
            - contexto_raw: "Rentas del Trabajo: Tasas progresivas sobre la Renta Neta: (8%, 9% y 10%). Amplía deducibilidad para Contribuyentes desde G. 80.000.000 de ingresos anuales (aprox. US$ 11.000). Rentas y Ganancias de Capital: 8%."
        
        [Continuar con el resto de impuestos: INR, IVA, ISC]

        2. Secciones adicionales para explorar:
        
        a) "Ventajas" / "Advantages":
            - Navega haciendo clic en "Ver más"
            - Captura cada ventaja como un dato macroeconómico:
                * indicador_nombre: Nombre de la ventaja
                * contexto_raw: Descripción completa
                * otras_propiedades_jsonb: {"tipo_inversion": "Ventaja general"}
        
        b) "Regímenes Especiales" / "Special Tax Regimes":
            - Navega haciendo clic en "Ver más"
            - Para cada régimen especial:
                * indicador_nombre: Nombre del régimen
                * contexto_raw: Descripción completa
                * otras_propiedades_jsonb: {"tipo_inversion": "Régimen especial"}

        3. Informes y documentos para capturar:
        
        a) "Euromoney Paraguay Report, March 2020":
            - titulo_informe: "Euromoney Paraguay Report, March 2020"
            - fecha_publicacion: "2020-03-01"
            - url_descarga_original: [URL del botón "Ver documento"]
            - id_tipo_informe: [asignar ID para tipo "Reporte externo"]
        
        b) Busca otros documentos disponibles:
            - En secciones como "Informes Económicos", "Informes Periódicos"
            - En la sección "Biblioteca" del menú superior
            - Cualquier enlace a PDF o documento descargable

        4. Procesamiento de imágenes:
        - Captura la URL de cada infografía
        - Transcribe todo el texto visible en las imágenes
        - Extrae cada valor numérico, porcentaje o tasa como un dato separado
        - Incluye el contexto completo como texto explicativo

        Nota importante: 
        1. Mantén la relación entre datos e informes usando id_informe consistentes
        2. Para datos extraídos de imágenes, usa el link_fuente_especifico para registrar la URL de la imagen
        3. Distingue entre datos que son tasas impositivas, ventajas comparativas y regímenes especiales
        4. Intenta capturar las fechas de vigencia de los datos cuando estén disponibles (ej. "En el año 2020...")
        """
        
        return firecrawl_scrape(url, prompt, schema, test_mode)

    # 10. Informes Financieros (DNIT)
    @tool("DNIT Financial Reports Scraper")
    def scrape_dnit_financial(test_mode=True) -> str:
        """Scrapes DNIT portal section with financial reports."""
        schema = {
            "type": "object",
            "properties": {
                "Informe_General": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_informe": {"type": "integer"},
                            "id_emisor": {"type": "integer"},
                            "id_tipo_informe": {"type": "integer"},
                            "id_frecuencia": {"type": "integer"},
                            "id_periodo": {"type": "integer"},
                            "titulo_informe": {"type": "string"},
                            "resumen_informe": {"type": "string"},
                            "fecha_publicacion": {"type": "string"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string"}
                        },
                        "required": ["titulo_informe", "url_descarga_original"]
                    }
                },
                "Emisores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_emisor": {"type": "integer"},
                            "nombre_emisor": {"type": "string"},
                            "id_categoria_emisor": {"type": "integer"}
                        },
                        "required": ["nombre_emisor"]
                    }
                }
            },
            "required": ["Informe_General"]
        }
        
        url = "https://www.dnit.gov.py/web/portal-institucional/informes-financieros"
        prompt = """Extrae la siguiente información del portal de informes financieros de la DNIT Paraguay:

        1. Informes financieros disponibles (Informe_General):
        - id_informe: identificador único del informe
        - id_emisor: referencia a la entidad emisora (DNIT, BNF, ITAU, etc.)
        - id_tipo_informe: tipo de informe (conciliación bancaria, informe de bienes, etc.)
        - titulo_informe: título completo del informe como aparece en la página (ej. "Conciliación Bancaria BNF - Cta.Cte.8212752-14")
        - fecha_publicacion: fecha de publicación si está disponible
        - url_descarga_original: enlace completo del botón "Descargar"
        - contenido_raw: deja este campo vacío inicialmente, se llenará al procesar el informe

        2. Entidades emisoras (Emisores):
        - id_emisor: identificador único del emisor
        - nombre_emisor: nombre completo de la entidad (ej. "DNIT", "BNF", "ITAU")
        - id_categoria_emisor: categoría de la entidad si está disponible

        GUÍA DE CRAWLING:
        La página de informes financieros de la DNIT muestra una lista de documentos financieros descargables:

        1. Lista principal de informes:
        - La página muestra múltiples informes financieros con título, botones de "Descargar" y "Ver"
        - Captura cada informe listado, incluyendo:
            * "Movimiento de Bienes de Uso - F.C.04 - UAF"
            * "Conciliación Bancaria ITAU - Cta.Cte.219712-04"
            * "Constancia de Presentación de Informes Financieros"
            * Múltiples "Conciliación Bancaria BNF" con diferentes números de cuenta

        2. Para cada informe en la lista:
        - Registra el título exacto como aparece en la página
        - Captura la URL completa del botón "Descargar"
        - Identifica la entidad bancaria o emisora mencionada (BNF, ITAU, etc.)
        - Extrae cualquier número de identificación o referencia (números de cuenta)
        - NO es necesario hacer clic en "Ver" o intentar acceder al contenido completo

        3. Navegación por páginas:
        - La página muestra "Mostrando 1 a 10 de 723 resultados"
        - Utiliza los botones de paginación ("Siguiente", "»") para acceder a más informes
        - Asegúrate de explorar todas las páginas de resultados

        4. Filtros disponibles:
        - Utiliza el desplegable "Seleccione categorías" para explorar diferentes tipos de informes
        - Usa la barra de búsqueda "Buscar aquí" si necesitas encontrar informes específicos

        Importante:
        - No intentes descargar o procesar el contenido de los informes en esta fase
        - Concéntrate solo en catalogar todos los informes disponibles y sus URLs de descarga
        - Mantén la relación entre informes y entidades emisoras usando IDs consistentes
        - Observa que hay 723 resultados en total, por lo que deberás navegar por múltiples páginas
        """
        
        return firecrawl_crawl(url, prompt, schema, test_mode)
    
    @tool("Normalize Data Tool")
    def normalize_data(raw_data: dict) -> dict:
        """Normalize and clean raw extracted data from scrapers.
        
        Args:
            raw_data: Dictionary with raw extracted data from scrapers
            
        Returns:
            Dictionary with normalized and cleaned data
        """
        import re
        from datetime import datetime
        
        try:
            normalized_data = {
                "normalized": {},
                "report": {
                    "total_records": 0,
                    "normalized_records": 0,
                    "errors": [],
                    "tables_processed": []
                }
            }
            
            for source_name, source_data in raw_data.items():
                if not isinstance(source_data, dict):
                    continue
                    
                for table_name, records in source_data.items():
                    if not isinstance(records, list):
                        continue
                        
                    if table_name not in normalized_data["normalized"]:
                        normalized_data["normalized"][table_name] = []
                    
                    table_report = {
                        "table": table_name,
                        "source": source_name,
                        "total": len(records),
                        "normalized": 0,
                        "errors": 0
                    }
                    
                    for i, record in enumerate(records):
                        normalized_data["report"]["total_records"] += 1
                        
                        try:
                            normalized_record = {}
                            
                            # Normalize each field in the record
                            for field, value in record.items():
                                if value is None or value == "":
                                    normalized_record[field] = None
                                    continue
                                
                                # Clean string fields
                                if isinstance(value, str):
                                    # Remove HTML tags and artifacts
                                    cleaned_value = re.sub(r'<[^>]+>', '', value)
                                    # Remove extra whitespace
                                    cleaned_value = re.sub(r'\s+', ' ', cleaned_value).strip()
                                    # Remove special characters except basic punctuation
                                    cleaned_value = re.sub(r'[^\w\s\-\.\,\:\;\(\)\/\%\$]', '', cleaned_value)
                                    
                                    # Handle date fields
                                    if 'fecha' in field.lower() or 'date' in field.lower():
                                        try:
                                            # Try to parse and standardize date format
                                            if len(cleaned_value) >= 4 and cleaned_value.isdigit():
                                                # Year only - convert to date
                                                normalized_record[field] = f"{cleaned_value}-01-01"
                                            elif '/' in cleaned_value:
                                                # DD/MM/YYYY or MM/DD/YYYY format
                                                parts = cleaned_value.split('/')
                                                if len(parts) == 3:
                                                    if len(parts[2]) == 4:  # YYYY
                                                        normalized_record[field] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                                                    else:
                                                        normalized_record[field] = cleaned_value
                                                else:
                                                    normalized_record[field] = cleaned_value
                                            elif '-' in cleaned_value and len(cleaned_value) >= 8:
                                                # Already in YYYY-MM-DD format or similar
                                                normalized_record[field] = cleaned_value
                                            else:
                                                normalized_record[field] = cleaned_value
                                        except:
                                            normalized_record[field] = cleaned_value
                                    else:
                                        normalized_record[field] = cleaned_value
                                
                                # Handle numeric fields
                                elif isinstance(value, (int, float)):
                                    normalized_record[field] = value
                                elif isinstance(value, str) and value.replace('.', '').replace(',', '').replace('-', '').isdigit():
                                    try:
                                        # Handle number strings with commas/periods
                                        numeric_value = value.replace(',', '')
                                        if '.' in numeric_value:
                                            normalized_record[field] = float(numeric_value)
                                        else:
                                            normalized_record[field] = int(numeric_value)
                                    except:
                                        normalized_record[field] = value
                                
                                # Handle objects/dictionaries
                                elif isinstance(value, dict):
                                    normalized_record[field] = value
                                
                                # Handle arrays
                                elif isinstance(value, list):
                                    normalized_record[field] = value
                                
                                else:
                                    normalized_record[field] = value
                            
                            normalized_data["normalized"][table_name].append(normalized_record)
                            normalized_data["report"]["normalized_records"] += 1
                            table_report["normalized"] += 1
                            
                        except Exception as e:
                            normalized_data["report"]["errors"].append({
                                "table": table_name,
                                "source": source_name,
                                "record_index": i,
                                "error": str(e)
                            })
                            table_report["errors"] += 1
                    
                    normalized_data["report"]["tables_processed"].append(table_report)
            
            return normalized_data
            
        except Exception as e:
            return {"error": f"Error normalizing data: {str(e)}", "raw_data": raw_data}

    @tool("Validate Data Tool")
    def validate_data(normalized_data: dict) -> dict:
        """Validate normalized data against Supabase schemas.
        
        Args:
            normalized_data: Dictionary with normalized data from normalize_data tool
            
        Returns:
            Dictionary with validation results and filtered valid data
        """
        try:
            validation_report = {
                "valid_data": {},
                "invalid_data": {},
                "report": {
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": [],
                    "tables_validated": []
                }
            }
            
            # Schema definitions based on Supabase structure
            table_schemas = {
                "Categoria_Emisor": {
                    "required": ["categoria_emisor"],
                    "optional": ["id_categoria_emisor"],
                    "types": {
                        "id_categoria_emisor": int,
                        "categoria_emisor": str
                    },
                    "max_lengths": {
                        "categoria_emisor": 100
                    }
                },
                "Emisores": {
                    "required": ["nombre_emisor"],
                    "optional": ["id_emisor", "id_categoria_emisor", "calificacion_bva"],
                    "types": {
                        "id_emisor": int,
                        "nombre_emisor": str,
                        "id_categoria_emisor": int,
                        "calificacion_bva": str
                    },
                    "max_lengths": {
                        "nombre_emisor": 250,
                        "calificacion_bva": 100
                    }
                },
                "Moneda": {
                    "required": ["codigo_moneda"],
                    "optional": ["id_moneda", "nombre_moneda"],
                    "types": {
                        "id_moneda": int,
                        "codigo_moneda": str,
                        "nombre_moneda": str
                    },
                    "max_lengths": {
                        "codigo_moneda": 10,
                        "nombre_moneda": 50
                    }
                },
                "Frecuencia": {
                    "required": ["nombre_frecuencia"],
                    "optional": ["id_frecuencia"],
                    "types": {
                        "id_frecuencia": int,
                        "nombre_frecuencia": str
                    },
                    "max_lengths": {
                        "nombre_frecuencia": 50
                    }
                },
                "Tipo_Informe": {
                    "required": ["nombre_tipo_informe"],
                    "optional": ["id_tipo_informe"],
                    "types": {
                        "id_tipo_informe": int,
                        "nombre_tipo_informe": str
                    },
                    "max_lengths": {
                        "nombre_tipo_informe": 100
                    }
                },
                "Periodo_Informe": {
                    "required": ["nombre_periodo"],
                    "optional": ["id_periodo"],
                    "types": {
                        "id_periodo": int,
                        "nombre_periodo": str
                    },
                    "max_lengths": {
                        "nombre_periodo": 50
                    }
                },
                "Unidad_Medida": {
                    "required": ["simbolo"],
                    "optional": ["id_unidad_medida", "nombre_unidad"],
                    "types": {
                        "id_unidad_medida": int,
                        "simbolo": str,
                        "nombre_unidad": str
                    },
                    "max_lengths": {
                        "simbolo": 10,
                        "nombre_unidad": 50
                    }
                },
                "Instrumento": {
                    "required": ["simbolo_instrumento"],
                    "optional": ["id_instrumento", "nombre_instrumento"],
                    "types": {
                        "id_instrumento": int,
                        "simbolo_instrumento": str,
                        "nombre_instrumento": str
                    },
                    "max_lengths": {
                        "simbolo_instrumento": 50,
                        "nombre_instrumento": 255
                    }
                },
                "Informe_General": {
                    "required": ["titulo_informe", "fecha_publicacion"],
                    "optional": ["id_informe", "id_emisor", "id_tipo_informe", "id_frecuencia", "id_periodo", "resumen_informe", "url_descarga_original", "detalles_informe_jsonb"],
                    "types": {
                        "id_informe": int,
                        "id_emisor": int,
                        "id_tipo_informe": int,
                        "id_frecuencia": int,
                        "id_periodo": int,
                        "titulo_informe": str,
                        "resumen_informe": str,
                        "fecha_publicacion": str,
                        "url_descarga_original": str,
                        "detalles_informe_jsonb": dict
                    },
                    "max_lengths": {
                        "titulo_informe": 500,
                        "url_descarga_original": 500
                    }
                },
                "Resumen_Informe_Financiero": {
                    "required": ["id_informe", "fecha_corte_informe"],
                    "optional": ["id_resumen_financiero", "id_emisor", "moneda_informe", "activos_totales", "pasivos_totales", "patrimonio_neto", "disponible", "utilidad_del_ejercicio", "ingresos_totales", "costos_operacionales", "total_ganancias", "total_perdidas", "retorno_sobre_patrimonio", "calificacion_riesgo_tendencia", "utilidad_neta_por_accion_ordinaria", "deuda_total", "ebitda", "margen_neto", "flujo_caja_operativo", "capital_integrado", "otras_metricas_jsonb"],
                    "types": {
                        "id_resumen_financiero": int,
                        "id_informe": int,
                        "id_emisor": int,
                        "fecha_corte_informe": str,
                        "moneda_informe": int,
                        "calificacion_riesgo_tendencia": str
                    },
                    "max_lengths": {
                        "calificacion_riesgo_tendencia": 100
                    }
                },
                "Dato_Macroeconomico": {
                    "required": ["indicador_nombre", "fecha_dato", "valor_numerico"],
                    "optional": ["id_dato_macro", "id_informe", "unidad_medida", "id_frecuencia", "link_fuente_especifico", "otras_propiedades_jsonb", "id_moneda", "id_emisor"],
                    "types": {
                        "id_dato_macro": int,
                        "id_informe": int,
                        "indicador_nombre": str,
                        "fecha_dato": str,
                        "valor_numerico": (int, float),
                        "unidad_medida": int,
                        "id_frecuencia": int,
                        "link_fuente_especifico": str,
                        "otras_propiedades_jsonb": dict,
                        "id_moneda": int,
                        "id_emisor": int
                    },
                    "max_lengths": {
                        "indicador_nombre": 250,
                        "link_fuente_especifico": 500
                    }
                },
                "Movimiento_Diario_Bolsa": {
                    "required": ["fecha_operacion", "id_instrumento", "precio_operacion"],
                    "optional": ["id_operacion", "cantidad_operacion", "id_emisor", "fecha_vencimiento_instrumento", "id_moneda", "precio_anterior_instrumento", "tasa_interes_nominal", "tipo_cambio", "variacion_operacion", "volumen_gs_operacion"],
                    "types": {
                        "id_operacion": int,
                        "fecha_operacion": str,
                        "id_instrumento": int,
                        "id_emisor": int,
                        "fecha_vencimiento_instrumento": str,
                        "id_moneda": int
                    }
                },
                "Licitacion_Contrato": {
                    "required": ["titulo"],
                    "optional": ["id_licitacion_contrato", "id_emisor_adjudicado", "entidad_convocante", "monto_adjudicado", "id_moneda", "fecha_adjudicacion"],
                    "types": {
                        "id_licitacion_contrato": int,
                        "id_emisor_adjudicado": int,
                        "titulo": str,
                        "entidad_convocante": str,
                        "id_moneda": int,
                        "fecha_adjudicacion": str
                    },
                    "max_lengths": {
                        "titulo": 500,
                        "entidad_convocante": 255
                    }
                }
            }
            
            # Get normalized data 
            data_to_validate = normalized_data.get("normalized", {})
            
            for table_name, records in data_to_validate.items():
                if table_name not in table_schemas:
                    validation_report["report"]["errors"].append({
                        "table": table_name,
                        "error": f"Unknown table schema for {table_name}"
                    })
                    continue
                
                schema = table_schemas[table_name]
                validation_report["valid_data"][table_name] = []
                validation_report["invalid_data"][table_name] = []
                
                table_report = {
                    "table": table_name,
                    "total": len(records),
                    "valid": 0,
                    "invalid": 0,
                    "errors": []
                }
                
                for i, record in enumerate(records):
                    validation_report["report"]["total_records"] += 1
                    is_valid = True
                    record_errors = []
                    
                    # Check required fields
                    for field in schema["required"]:
                        if field not in record or record[field] is None or record[field] == "":
                            is_valid = False
                            record_errors.append(f"Missing required field: {field}")
                    
                    # Check field types and lengths
                    for field, value in record.items():
                        if value is None or value == "":
                            continue
                            
                        # Type validation
                        if field in schema["types"]:
                            expected_type = schema["types"][field]
                            if isinstance(expected_type, tuple):
                                # Multiple types allowed (like int, float)
                                if not isinstance(value, expected_type):
                                    is_valid = False
                                    record_errors.append(f"Field {field} should be one of {expected_type}, got {type(value)}")
                            else:
                                if not isinstance(value, expected_type):
                                    is_valid = False
                                    record_errors.append(f"Field {field} should be {expected_type}, got {type(value)}")
                        
                        # Length validation for strings
                        if field in schema.get("max_lengths", {}) and isinstance(value, str):
                            max_length = schema["max_lengths"][field]
                            if len(value) > max_length:
                                is_valid = False
                                record_errors.append(f"Field {field} exceeds max length {max_length}: {len(value)}")
                        
                        # Date format validation
                        if field.endswith("fecha") or "date" in field.lower():
                            if isinstance(value, str) and value:
                                # Basic date format check (YYYY-MM-DD)
                                import re
                                if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                                    is_valid = False
                                    record_errors.append(f"Field {field} should be in YYYY-MM-DD format: {value}")
                    
                    if is_valid:
                        validation_report["valid_data"][table_name].append(record)
                        validation_report["report"]["valid_records"] += 1
                        table_report["valid"] += 1
                    else:
                        validation_report["invalid_data"][table_name].append({
                            "record": record,
                            "errors": record_errors
                        })
                        validation_report["report"]["invalid_records"] += 1
                        table_report["invalid"] += 1
                        table_report["errors"].extend(record_errors)
                
                validation_report["report"]["tables_validated"].append(table_report)
            
            return validation_report
            
        except Exception as e:
            return {"error": f"Error validating data: {str(e)}", "normalized_data": normalized_data}

    @tool("Create Entity Relationships Tool")
    def create_entity_relationships(validated_data: dict) -> dict:
        """Create foreign key relationships between entities.
        
        Args:
            validated_data: Dictionary with validated data from validate_data tool
            
        Returns:
            Dictionary with data containing established relationships
        """
        try:
            relationship_report = {
                "data_with_relationships": {},
                "created_entities": {},
                "report": {
                    "total_records": 0,
                    "processed_records": 0,
                    "relationship_errors": [],
                    "created_master_entities": {},
                    "tables_processed": []
                }
            }
            
            # Get valid data to process
            valid_data = validated_data.get("valid_data", {})
            
            # Entity ID counters (start from 1)
            entity_counters = {
                "id_categoria_emisor": 1,
                "id_emisor": 1,  
                "id_moneda": 1,
                "id_frecuencia": 1,
                "id_tipo_informe": 1,
                "id_periodo": 1,
                "id_unidad_medida": 1,
                "id_instrumento": 1,
                "id_informe": 1,
                "id_resumen_financiero": 1,
                "id_dato_macro": 1,
                "id_operacion": 1,
                "id_licitacion_contrato": 1
            }
            
            # Entity lookup dictionaries for resolving names to IDs
            entity_lookups = {
                "categoria_emisor": {},  # categoria_emisor -> id_categoria_emisor
                "emisor": {},           # nombre_emisor -> id_emisor
                "moneda": {},           # codigo_moneda -> id_moneda
                "frecuencia": {},       # nombre_frecuencia -> id_frecuencia
                "tipo_informe": {},     # nombre_tipo_informe -> id_tipo_informe
                "periodo": {},          # nombre_periodo -> id_periodo
                "unidad_medida": {},    # simbolo -> id_unidad_medida
                "instrumento": {}       # simbolo_instrumento -> id_instrumento
            }
            
            # Process master entities first to create lookup tables
            master_entities = ["Categoria_Emisor", "Emisores", "Moneda", "Frecuencia", "Tipo_Informe", "Periodo_Informe", "Unidad_Medida", "Instrumento"]
            
            for table_name in master_entities:
                if table_name not in valid_data:
                    continue
                
                relationship_report["data_with_relationships"][table_name] = []
                records = valid_data[table_name]
                
                table_report = {
                    "table": table_name,
                    "total": len(records),
                    "processed": 0,
                    "entities_created": 0
                }
                
                for record in records:
                    relationship_report["report"]["total_records"] += 1
                    processed_record = record.copy()
                    
                    # Assign IDs and create lookups based on table
                    if table_name == "Categoria_Emisor":
                        if "id_categoria_emisor" not in processed_record or processed_record["id_categoria_emisor"] is None:
                            processed_record["id_categoria_emisor"] = entity_counters["id_categoria_emisor"]
                            entity_counters["id_categoria_emisor"] += 1
                        
                        # Create lookup
                        categoria_name = processed_record.get("categoria_emisor")
                        if categoria_name:
                            entity_lookups["categoria_emisor"][categoria_name] = processed_record["id_categoria_emisor"]
                    
                    elif table_name == "Emisores":
                        if "id_emisor" not in processed_record or processed_record["id_emisor"] is None:
                            processed_record["id_emisor"] = entity_counters["id_emisor"]
                            entity_counters["id_emisor"] += 1
                        
                        # Resolve categoria relationship
                        if "categoria_emisor" in processed_record:
                            categoria_name = processed_record["categoria_emisor"]
                            if categoria_name in entity_lookups["categoria_emisor"]:
                                processed_record["id_categoria_emisor"] = entity_lookups["categoria_emisor"][categoria_name]
                            else:
                                # Create new categoria if not found
                                new_categoria_id = entity_counters["id_categoria_emisor"]
                                entity_counters["id_categoria_emisor"] += 1
                                entity_lookups["categoria_emisor"][categoria_name] = new_categoria_id
                                processed_record["id_categoria_emisor"] = new_categoria_id
                                
                                # Add to Categoria_Emisor table
                                if "Categoria_Emisor" not in relationship_report["data_with_relationships"]:
                                    relationship_report["data_with_relationships"]["Categoria_Emisor"] = []
                                relationship_report["data_with_relationships"]["Categoria_Emisor"].append({
                                    "id_categoria_emisor": new_categoria_id,
                                    "categoria_emisor": categoria_name
                                })
                        
                        # Create lookup
                        emisor_name = processed_record.get("nombre_emisor")
                        if emisor_name:
                            entity_lookups["emisor"][emisor_name] = processed_record["id_emisor"]
                    
                    elif table_name == "Moneda":
                        if "id_moneda" not in processed_record or processed_record["id_moneda"] is None:
                            processed_record["id_moneda"] = entity_counters["id_moneda"]
                            entity_counters["id_moneda"] += 1
                        
                        # Create lookup
                        codigo_moneda = processed_record.get("codigo_moneda")
                        if codigo_moneda:
                            entity_lookups["moneda"][codigo_moneda] = processed_record["id_moneda"]
                    
                    elif table_name == "Frecuencia":
                        if "id_frecuencia" not in processed_record or processed_record["id_frecuencia"] is None:
                            processed_record["id_frecuencia"] = entity_counters["id_frecuencia"]
                            entity_counters["id_frecuencia"] += 1
                        
                        # Create lookup
                        nombre_frecuencia = processed_record.get("nombre_frecuencia")
                        if nombre_frecuencia:
                            entity_lookups["frecuencia"][nombre_frecuencia] = processed_record["id_frecuencia"]
                    
                    elif table_name == "Tipo_Informe":
                        if "id_tipo_informe" not in processed_record or processed_record["id_tipo_informe"] is None:
                            processed_record["id_tipo_informe"] = entity_counters["id_tipo_informe"]
                            entity_counters["id_tipo_informe"] += 1
                        
                        # Create lookup
                        nombre_tipo = processed_record.get("nombre_tipo_informe")
                        if nombre_tipo:
                            entity_lookups["tipo_informe"][nombre_tipo] = processed_record["id_tipo_informe"]
                    
                    elif table_name == "Periodo_Informe":
                        if "id_periodo" not in processed_record or processed_record["id_periodo"] is None:
                            processed_record["id_periodo"] = entity_counters["id_periodo"]
                            entity_counters["id_periodo"] += 1
                        
                        # Create lookup
                        nombre_periodo = processed_record.get("nombre_periodo")
                        if nombre_periodo:
                            entity_lookups["periodo"][nombre_periodo] = processed_record["id_periodo"]
                    
                    elif table_name == "Unidad_Medida":
                        if "id_unidad_medida" not in processed_record or processed_record["id_unidad_medida"] is None:
                            processed_record["id_unidad_medida"] = entity_counters["id_unidad_medida"]
                            entity_counters["id_unidad_medida"] += 1
                        
                        # Create lookup
                        simbolo = processed_record.get("simbolo")
                        if simbolo:
                            entity_lookups["unidad_medida"][simbolo] = processed_record["id_unidad_medida"]
                    
                    elif table_name == "Instrumento":
                        if "id_instrumento" not in processed_record or processed_record["id_instrumento"] is None:
                            processed_record["id_instrumento"] = entity_counters["id_instrumento"]
                            entity_counters["id_instrumento"] += 1
                        
                        # Create lookup
                        simbolo_instrumento = processed_record.get("simbolo_instrumento")
                        if simbolo_instrumento:
                            entity_lookups["instrumento"][simbolo_instrumento] = processed_record["id_instrumento"]
                    
                    relationship_report["data_with_relationships"][table_name].append(processed_record)
                    relationship_report["report"]["processed_records"] += 1
                    table_report["processed"] += 1
                    table_report["entities_created"] += 1
                
                relationship_report["report"]["tables_processed"].append(table_report)
            
            # Process dependent entities that reference master entities
            dependent_entities = ["Informe_General", "Resumen_Informe_Financiero", "Dato_Macroeconomico", "Movimiento_Diario_Bolsa", "Licitacion_Contrato"]
            
            for table_name in dependent_entities:
                if table_name not in valid_data:
                    continue
                
                relationship_report["data_with_relationships"][table_name] = []
                records = valid_data[table_name]
                
                table_report = {
                    "table": table_name,
                    "total": len(records),
                    "processed": 0,
                    "relationship_errors": []
                }
                
                for record in records:
                    relationship_report["report"]["total_records"] += 1
                    processed_record = record.copy()
                    
                    # Assign primary key ID
                    if table_name == "Informe_General":
                        if "id_informe" not in processed_record or processed_record["id_informe"] is None:
                            processed_record["id_informe"] = entity_counters["id_informe"]
                            entity_counters["id_informe"] += 1
                        
                        # Resolve foreign key relationships
                        if "nombre_emisor" in processed_record:
                            emisor_name = processed_record["nombre_emisor"]
                            if emisor_name in entity_lookups["emisor"]:
                                processed_record["id_emisor"] = entity_lookups["emisor"][emisor_name]
                    
                    elif table_name == "Resumen_Informe_Financiero":
                        if "id_resumen_financiero" not in processed_record or processed_record["id_resumen_financiero"] is None:
                            processed_record["id_resumen_financiero"] = entity_counters["id_resumen_financiero"]
                            entity_counters["id_resumen_financiero"] += 1
                    
                    elif table_name == "Dato_Macroeconomico":
                        if "id_dato_macro" not in processed_record or processed_record["id_dato_macro"] is None:
                            processed_record["id_dato_macro"] = entity_counters["id_dato_macro"]
                            entity_counters["id_dato_macro"] += 1
                    
                    elif table_name == "Movimiento_Diario_Bolsa":
                        if "id_operacion" not in processed_record or processed_record["id_operacion"] is None:
                            processed_record["id_operacion"] = entity_counters["id_operacion"]
                            entity_counters["id_operacion"] += 1
                    
                    elif table_name == "Licitacion_Contrato":
                        if "id_licitacion_contrato" not in processed_record or processed_record["id_licitacion_contrato"] is None:
                            processed_record["id_licitacion_contrato"] = entity_counters["id_licitacion_contrato"]
                            entity_counters["id_licitacion_contrato"] += 1
                    
                    relationship_report["data_with_relationships"][table_name].append(processed_record)
                    relationship_report["report"]["processed_records"] += 1
                    table_report["processed"] += 1
                
                relationship_report["report"]["tables_processed"].append(table_report)
            
            # Store entity lookups for reference
            relationship_report["created_entities"] = entity_lookups
            relationship_report["report"]["created_master_entities"] = {
                key: len(value) for key, value in entity_lookups.items()
            }
            
            return relationship_report
            
        except Exception as e:
            return {"error": f"Error creating entity relationships: {str(e)}", "validated_data": validated_data}

    @tool("Structure Extracted Data Tool")
    def structure_extracted_data(relationship_data: dict) -> dict:
        """Structure data with relationships into final format for loading.
        
        Args:
            relationship_data: Dictionary with data from create_entity_relationships tool
            
        Returns:
            Dictionary with structured data ready for database loading
        """
        try:
            structured_report = {
                "structured_data": {},
                "metadata": {
                    "total_tables": 0,
                    "total_records": 0,
                    "loading_batches": {},
                    "table_priorities": [],
                    "processing_summary": []
                },
                "report": {
                    "tables_structured": 0,
                    "records_structured": 0,
                    "empty_tables": [],
                    "processing_errors": []
                }
            }
            
            # Get data with relationships
            data_with_relationships = relationship_data.get("data_with_relationships", {})
            
            if not data_with_relationships:
                return {"error": "No data with relationships found", "relationship_data": relationship_data}
            
            # Define loading priority order (master entities first, then dependent entities)
            loading_priority = [
                # Master entities (no foreign keys dependencies)
                "Categoria_Emisor",
                "Moneda", 
                "Frecuencia",
                "Tipo_Informe",
                "Periodo_Informe",
                "Unidad_Medida",
                "Instrumento",
                
                # Entities with minimal dependencies
                "Emisores",  # depends on Categoria_Emisor
                
                # Main content entities
                "Informe_General",  # depends on Emisores, Tipo_Informe, Frecuencia, Periodo_Informe
                
                # Dependent entities
                "Resumen_Informe_Financiero",  # depends on Informe_General, Emisores
                "Dato_Macroeconomico",  # depends on Informe_General, Emisores, Frecuencia, Unidad_Medida, Moneda
                "Movimiento_Diario_Bolsa",  # depends on Instrumento, Emisores, Moneda
                "Licitacion_Contrato"  # depends on Emisores, Moneda
            ]
            
            structured_report["metadata"]["table_priorities"] = loading_priority
            
            # Process each table according to priority
            for table_name in loading_priority:
                if table_name not in data_with_relationships:
                    structured_report["report"]["empty_tables"].append(table_name)
                    continue
                
                records = data_with_relationships[table_name]
                
                if not records:
                    structured_report["report"]["empty_tables"].append(table_name)
                    continue
                
                # Structure the data for this table
                structured_records = []
                table_processing_summary = {
                    "table": table_name,
                    "total_records": len(records),
                    "structured_records": 0,
                    "batch_size_recommended": 50 if len(records) > 100 else len(records),
                    "fields_present": set(),
                    "processing_notes": []
                }
                
                for record in records:
                    try:
                        # Clean and structure each record
                        structured_record = {}
                        
                        # Copy all fields, ensuring proper data types
                        for field, value in record.items():
                            if value is None or value == "":
                                structured_record[field] = None
                            else:
                                structured_record[field] = value
                            
                            table_processing_summary["fields_present"].add(field)
                        
                        # Apply table-specific structuring rules
                        if table_name == "Informe_General":
                            # Ensure required fields are present
                            if "titulo_informe" not in structured_record:
                                table_processing_summary["processing_notes"].append("Missing titulo_informe in record")
                                continue
                            if "fecha_publicacion" not in structured_record:
                                table_processing_summary["processing_notes"].append("Missing fecha_publicacion in record")
                                continue
                        
                        elif table_name == "Emisores":
                            # Ensure required fields are present
                            if "nombre_emisor" not in structured_record:
                                table_processing_summary["processing_notes"].append("Missing nombre_emisor in record")
                                continue
                        
                        elif table_name == "Dato_Macroeconomico":
                            # Ensure required fields are present
                            required_fields = ["indicador_nombre", "fecha_dato", "valor_numerico"]
                            missing_fields = [field for field in required_fields if field not in structured_record]
                            if missing_fields:
                                table_processing_summary["processing_notes"].append(f"Missing required fields: {missing_fields}")
                                continue
                            
                            # Ensure valor_numerico is numeric
                            if not isinstance(structured_record["valor_numerico"], (int, float)):
                                try:
                                    structured_record["valor_numerico"] = float(structured_record["valor_numerico"])
                                except:
                                    table_processing_summary["processing_notes"].append("Invalid valor_numerico format")
                                    continue
                        
                        elif table_name == "Movimiento_Diario_Bolsa":
                            # Ensure required fields are present
                            required_fields = ["fecha_operacion", "id_instrumento", "precio_operacion"]
                            missing_fields = [field for field in required_fields if field not in structured_record]
                            if missing_fields:
                                table_processing_summary["processing_notes"].append(f"Missing required fields: {missing_fields}")
                                continue
                        
                        elif table_name == "Licitacion_Contrato":
                            # Ensure required fields are present
                            if "titulo" not in structured_record:
                                table_processing_summary["processing_notes"].append("Missing titulo in record")
                                continue
                        
                        structured_records.append(structured_record)
                        table_processing_summary["structured_records"] += 1
                        structured_report["report"]["records_structured"] += 1
                        
                    except Exception as record_error:
                        structured_report["report"]["processing_errors"].append({
                            "table": table_name,
                            "record_index": len(structured_records),
                            "error": str(record_error)
                        })
                
                # Store structured data for this table
                if structured_records:
                    structured_report["structured_data"][table_name] = structured_records
                    structured_report["metadata"]["total_records"] += len(structured_records)
                    
                    # Calculate optimal batch size for loading
                    if len(structured_records) > 200:
                        batch_size = 50
                    elif len(structured_records) > 50:
                        batch_size = 25
                    else:
                        batch_size = len(structured_records)
                    
                    structured_report["metadata"]["loading_batches"][table_name] = {
                        "total_records": len(structured_records),
                        "recommended_batch_size": batch_size,
                        "estimated_batches": (len(structured_records) + batch_size - 1) // batch_size
                    }
                
                # Convert set to list for JSON serialization
                table_processing_summary["fields_present"] = list(table_processing_summary["fields_present"])
                structured_report["metadata"]["processing_summary"].append(table_processing_summary)
                structured_report["report"]["tables_structured"] += 1
            
            structured_report["metadata"]["total_tables"] = len(structured_report["structured_data"])
            
            # Add loading recommendations
            structured_report["loading_recommendations"] = {
                "load_order": [table for table in loading_priority if table in structured_report["structured_data"]],
                "parallel_loading_groups": [
                    ["Categoria_Emisor", "Moneda", "Frecuencia", "Tipo_Informe", "Periodo_Informe", "Unidad_Medida", "Instrumento"],
                    ["Emisores"],
                    ["Informe_General"], 
                    ["Resumen_Informe_Financiero", "Dato_Macroeconomico", "Movimiento_Diario_Bolsa", "Licitacion_Contrato"]
                ],
                "estimated_loading_time": f"{structured_report['metadata']['total_records'] / 100:.1f} minutes",
                "database_validation_required": True
            }
            
            return structured_report
            
        except Exception as e:
            return {"error": f"Error structuring extracted data: {str(e)}", "relationship_data": relationship_data}

    @tool("Filter Duplicate Data Tool")
    def filter_duplicate_data(structured_data:dict) -> dict:
        """Filter out data that already exists in Supabase

        Args:
            structured_data: Dicionary with structured data by table

        Returns:
            Dictionary with filtered data and report
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"error": "Supabase credentials not found in environmental variables"}
        
        try:
            supabase = create_client(supabase_url, supabase_key)
            
            filtered_data = {
                "new_data": {},
                "existing_data": {},
                "report": {
                    "total_records": 0,
                    "new_records": 0,
                    "existing_records": 0,
                    "tables_processed": []
                }
            }
            
            for table_name, records in structured_data.items():
                filtered_data["new_data"][table_name] = []
                filtered_data["existing_data"][table_name] = []
                table_report = {
                    "table": table_name,
                    "total": len(records),
                    "new": 0,
                    "existing": 0
                }
                
                if not records:
                    filtered_data["report"]["tables_processed"].append(table_report)
                    continue
                
                # Reemplaza la sección marcada con este código:
                key_field = None
                unique_fields = []

                # Definir campos únicos para cada tabla basado en la estructura de Supabase
                table_unique_fields = {
                    "Categoria_Emisor": ["categoria_emisor"],
                    "Emisores": ["nombre_emisor"],
                    "Moneda": ["codigo_moneda"],
                    "Frecuencia": ["nombre_frecuencia"],
                    "Tipo_Informe": ["nombre_tipo_informe"],
                    "Periodo_Informe": ["nombre_periodo"],
                    "Unidad_Medida": ["simbolo"],
                    "Instrumento": ["simbolo_instrumento"],
                    "Informe_General": ["titulo_informe", "fecha_publicacion"],
                    "Resumen_Informe_Financiero": ["id_informe", "fecha_corte_informe"],
                    "Dato_Macroeconomico": ["indicador_nombre", "fecha_dato", "id_emisor"],
                    "Movimiento_Diario_Bolsa": ["fecha_operacion", "id_instrumento", "id_emisor"],
                    "Licitacion_Contrato": ["titulo", "fecha_adjudicacion"]
                }

                if table_name in table_unique_fields:
                    unique_fields = table_unique_fields[table_name]
                    if records and all(field in records[0] for field in unique_fields):
                        key_field = unique_fields[0]  # Usar el primer campo como principal
                    
                if not key_field:
                    filtered_data["new_data"][table_name] = records
                    table_report["new"] = len(records)
                    filtered_data["report"]["total_records"] += len(records)
                    filtered_data["report"]["new_records"] += len(records)
                    filtered_data["report"]["tables_processed"].append(table_report)
                    continue

                for record in records: 
                    filtered_data["report"]["total_records"] += 1
                    
                    # Construir query con múltiples campos únicos si es necesario
                    query = supabase.table(table_name).select("*")
                    for field in unique_fields:
                        if field in record:
                            query = query.eq(field, record[field])
                    
                    result = query.execute()
                    
                    if result.data and len(result.data) > 0:
                        filtered_data["existing_data"][table_name].append(record)
                        filtered_data["report"]["existing_records"] += 1
                        table_report["existing"] += 1
                    else: 
                        filtered_data["new_data"][table_name].append(record)
                        filtered_data["report"]["new_records"] += 1
                        table_report["new"] += 1
                filtered_data["report"]["tables_processed"].append(table_report)  
            return filtered_data
        except Exception as e:
            return {"error": f"Error filtering duplicate data : {str(e)}", "structured_data": structured_data}
        
    
    @tool("Extract Text from PDF Tool")
    def extract_text_from_pdf(pdf_url: str) -> dict:
        """Extract text content from PDF documents.
        
        Args:
            pdf_url: URL or file path to the PDF document
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            import requests
            import io
            
            # Try to import PyMuPDF (fitz)
            try:
                import fitz
            except ImportError:
                return {"error": "PyMuPDF (fitz) not installed. Please install with: pip install PyMuPDF"}
            
            extraction_result = {
                "extracted_text": "",
                "metadata": {
                    "source_url": pdf_url,
                    "page_count": 0,
                    "extraction_method": "PyMuPDF",
                    "file_size_kb": 0,
                    "extraction_errors": []
                },
                "pages": [],
                "report": {
                    "success": False,
                    "total_characters": 0,
                    "pages_processed": 0,
                    "pages_with_text": 0,
                    "processing_time": 0
                }
            }
            
            import time
            start_time = time.time()
            
            # Download PDF if it's a URL
            pdf_data = None
            if pdf_url.startswith(('http://', 'https://')):
                try:
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()
                    pdf_data = response.content
                    extraction_result["metadata"]["file_size_kb"] = len(pdf_data) / 1024
                except Exception as download_error:
                    return {"error": f"Failed to download PDF from URL: {str(download_error)}", "pdf_url": pdf_url}
            else:
                try:
                    with open(pdf_url, 'rb') as file:
                        pdf_data = file.read()
                        extraction_result["metadata"]["file_size_kb"] = len(pdf_data) / 1024
                except Exception as file_error:
                    return {"error": f"Failed to read PDF file: {str(file_error)}", "pdf_url": pdf_url}
            
            # Extract text using PyMuPDF
            try:
                # Open PDF from memory
                pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
                extraction_result["metadata"]["page_count"] = pdf_document.page_count
                
                all_text = []
                
                for page_num in range(pdf_document.page_count):
                    try:
                        page = pdf_document.load_page(page_num)
                        page_text = page.get_text()
                        
                        page_info = {
                            "page_number": page_num + 1,
                            "text": page_text.strip(),
                            "character_count": len(page_text),
                            "has_text": len(page_text.strip()) > 0
                        }
                        
                        extraction_result["pages"].append(page_info)
                        extraction_result["report"]["pages_processed"] += 1
                        
                        if page_info["has_text"]:
                            all_text.append(page_text)
                            extraction_result["report"]["pages_with_text"] += 1
                        
                    except Exception as page_error:
                        extraction_result["metadata"]["extraction_errors"].append({
                            "page": page_num + 1,
                            "error": str(page_error)
                        })
                
                pdf_document.close()
                
                # Combine all text
                extraction_result["extracted_text"] = "\n\n".join(all_text)
                extraction_result["report"]["total_characters"] = len(extraction_result["extracted_text"])
                extraction_result["report"]["processing_time"] = time.time() - start_time
                extraction_result["report"]["success"] = True
                
                # Add document metadata if available
                try:
                    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
                    metadata = pdf_document.metadata
                    extraction_result["metadata"].update({
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""), 
                        "subject": metadata.get("subject", ""),
                        "creator": metadata.get("creator", ""),
                        "producer": metadata.get("producer", ""),
                        "creation_date": metadata.get("creationDate", ""),
                        "modification_date": metadata.get("modDate", "")
                    })
                    pdf_document.close()
                except:
                    pass  # Metadata extraction is optional
                
                return extraction_result
                
            except Exception as extraction_error:
                return {"error": f"Failed to extract text from PDF: {str(extraction_error)}", "pdf_url": pdf_url}
            
        except Exception as e:
            return {"error": f"Error in PDF text extraction: {str(e)}", "pdf_url": pdf_url}

    @tool("Chunk Document Tool")
    def chunk_document(text_content: str, chunk_size: int = 1200, overlap: int = 200) -> dict:
        """Split document text into overlapping chunks for vectorization.
        
        Args:
            text_content: Full text content to chunk
            chunk_size: Target size of each chunk in tokens (default 1200)
            overlap: Number of tokens to overlap between chunks (default 200)
            
        Returns:
            Dictionary with list of text chunks and metadata
        """
        try:
            # Try to import tiktoken for token counting
            try:
                import tiktoken
                tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
                use_tiktoken = True
            except ImportError:
                # Fallback to character-based chunking
                use_tiktoken = False
            
            chunking_result = {
                "chunks": [],
                "metadata": {
                    "total_chunks": 0,
                    "chunk_size_target": chunk_size,
                    "overlap_size": overlap,
                    "tokenizer_used": "tiktoken" if use_tiktoken else "character_based",
                    "original_length": len(text_content),
                    "total_tokens_estimate": 0
                },
                "report": {
                    "success": False,
                    "chunks_created": 0,
                    "average_chunk_size": 0,
                    "chunks_with_overlap": 0,
                    "processing_errors": []
                }
            }
            
            if not text_content or len(text_content.strip()) == 0:
                return {"error": "Empty text content provided", "text_content": text_content}
            
            text_content = text_content.strip()
            
            if use_tiktoken:
                # Token-based chunking
                tokens = tokenizer.encode(text_content)
                chunking_result["metadata"]["total_tokens_estimate"] = len(tokens)
                
                if len(tokens) <= chunk_size:
                    # Text is small enough to be a single chunk
                    chunking_result["chunks"].append({
                        "chunk_id": 1,
                        "text": text_content,
                        "token_count": len(tokens),
                        "character_count": len(text_content),
                        "start_position": 0,
                        "end_position": len(text_content),
                        "has_overlap_with_previous": False,
                        "has_overlap_with_next": False
                    })
                    chunking_result["report"]["chunks_created"] = 1
                else:
                    # Split into multiple chunks
                    chunk_id = 1
                    start_idx = 0
                    
                    while start_idx < len(tokens):
                        end_idx = min(start_idx + chunk_size, len(tokens))
                        chunk_tokens = tokens[start_idx:end_idx]
                        chunk_text = tokenizer.decode(chunk_tokens)
                        
                        # Find actual character positions in original text
                        if chunk_id == 1:
                            char_start = 0
                        else:
                            # Find the character position by decoding from beginning
                            preceding_tokens = tokens[:start_idx]
                            char_start = len(tokenizer.decode(preceding_tokens))
                        
                        char_end = min(char_start + len(chunk_text), len(text_content))
                        actual_chunk_text = text_content[char_start:char_end]
                        
                        chunk = {
                            "chunk_id": chunk_id,
                            "text": actual_chunk_text,
                            "token_count": len(chunk_tokens),
                            "character_count": len(actual_chunk_text),
                            "start_position": char_start,
                            "end_position": char_end,
                            "has_overlap_with_previous": chunk_id > 1,
                            "has_overlap_with_next": end_idx < len(tokens)
                        }
                        
                        chunking_result["chunks"].append(chunk)
                        chunking_result["report"]["chunks_created"] += 1
                        
                        if chunk["has_overlap_with_previous"]:
                            chunking_result["report"]["chunks_with_overlap"] += 1
                        
                        chunk_id += 1
                        
                        # Move start position with overlap
                        if end_idx < len(tokens):
                            start_idx = end_idx - overlap
                        else:
                            break
            
            else:
                # Character-based chunking (fallback)
                # Estimate tokens as characters / 4 (rough approximation)
                char_chunk_size = chunk_size * 4
                char_overlap = overlap * 4
                
                chunking_result["metadata"]["total_tokens_estimate"] = len(text_content) // 4
                
                if len(text_content) <= char_chunk_size:
                    chunking_result["chunks"].append({
                        "chunk_id": 1,
                        "text": text_content,
                        "token_count": len(text_content) // 4,
                        "character_count": len(text_content),
                        "start_position": 0,
                        "end_position": len(text_content),
                        "has_overlap_with_previous": False,
                        "has_overlap_with_next": False
                    })
                    chunking_result["report"]["chunks_created"] = 1
                else:
                    chunk_id = 1
                    start_pos = 0
                    
                    while start_pos < len(text_content):
                        end_pos = min(start_pos + char_chunk_size, len(text_content))
                        
                        # Try to break at sentence or paragraph boundaries
                        if end_pos < len(text_content):
                            # Look for sentence endings within the last 200 characters
                            search_start = max(end_pos - 200, start_pos)
                            sentence_endings = []
                            for i in range(search_start, end_pos):
                                if text_content[i] in '.!?\n':
                                    sentence_endings.append(i)
                            
                            if sentence_endings:
                                end_pos = sentence_endings[-1] + 1
                        
                        chunk_text = text_content[start_pos:end_pos].strip()
                        
                        if chunk_text:
                            chunk = {
                                "chunk_id": chunk_id,
                                "text": chunk_text,
                                "token_count": len(chunk_text) // 4,
                                "character_count": len(chunk_text),
                                "start_position": start_pos,
                                "end_position": end_pos,
                                "has_overlap_with_previous": chunk_id > 1,
                                "has_overlap_with_next": end_pos < len(text_content)
                            }
                            
                            chunking_result["chunks"].append(chunk)
                            chunking_result["report"]["chunks_created"] += 1
                            
                            if chunk["has_overlap_with_previous"]:
                                chunking_result["report"]["chunks_with_overlap"] += 1
                            
                            chunk_id += 1
                        
                        # Move start with overlap
                        if end_pos < len(text_content):
                            start_pos = max(end_pos - char_overlap, start_pos + 1)
                        else:
                            break
            
            # Calculate final statistics
            chunking_result["metadata"]["total_chunks"] = len(chunking_result["chunks"])
            if chunking_result["chunks"]:
                total_chars = sum(chunk["character_count"] for chunk in chunking_result["chunks"])
                chunking_result["report"]["average_chunk_size"] = total_chars // len(chunking_result["chunks"])
            
            chunking_result["report"]["success"] = True
            
            return chunking_result
            
        except Exception as e:
            return {"error": f"Error chunking document: {str(e)}", "text_content": text_content[:500] + "..."}

    @tool("Prepare Document Metadata Tool")
    def prepare_document_metadata(chunks_data: dict, source_info: dict, index_name: str) -> dict:
        """Prepare metadata for Pinecone vector storage.
        
        Args:
            chunks_data: Dictionary with chunks from chunk_document tool
            source_info: Dictionary with source document information  
            index_name: Target Pinecone index name
            
        Returns:
            Dictionary with vector-ready data including metadata
        """
        try:
            import uuid
            from datetime import datetime
            
            metadata_result = {
                "vector_data": [],
                "metadata": {
                    "index_name": index_name,
                    "source_document": source_info,
                    "total_vectors": 0,
                    "metadata_schema": {},
                    "processing_timestamp": datetime.now().isoformat()
                },
                "report": {
                    "success": False,
                    "vectors_prepared": 0,
                    "metadata_errors": [],
                    "skipped_chunks": 0
                }
            }
            
            # Get chunks from input
            chunks = chunks_data.get("chunks", [])
            if not chunks:
                return {"error": "No chunks found in chunks_data", "chunks_data": chunks_data}
            
            # Define metadata schema based on index type
            index_schemas = {
                "documentos-informes-vector": {
                    "required_fields": ["id_informe", "chunk_id"],
                    "optional_fields": ["id_emisor", "id_tipo_informe", "id_frecuencia", "id_periodo", "fecha_publicacion", "chunk_text"]
                },
                "dato-macroeconomico-vector": {
                    "required_fields": ["id_dato_macro", "chunk_id"],
                    "optional_fields": ["indicador_nombre", "fecha_dato", "id_unidad_medida", "id_moneda", "id_frecuencia", "id_emisor", "id_informe", "chunk_text"]
                },
                "licitacion-contrato-vector": {
                    "required_fields": ["id_licitacion_contrato", "chunk_id"],
                    "optional_fields": ["titulo", "id_emisor_adjudicado", "entidad_convocante", "monto_adjudicado", "id_moneda", "fecha_adjudicacion", "chunk_text"]
                }
            }
            
            if index_name not in index_schemas:
                return {"error": f"Unknown index schema for {index_name}", "index_name": index_name}
            
            schema = index_schemas[index_name]
            metadata_result["metadata"]["metadata_schema"] = schema
            
            # Process each chunk into vector format
            for chunk in chunks:
                try:
                    chunk_text = chunk.get("text", "")
                    if not chunk_text or len(chunk_text.strip()) < 10:
                        metadata_result["report"]["skipped_chunks"] += 1
                        continue
                    
                    # Generate unique vector ID
                    vector_id = str(uuid.uuid4())
                    
                    # Base metadata that applies to all indices
                    base_metadata = {
                        "chunk_id": chunk.get("chunk_id", 1),
                        "chunk_text": chunk_text[:500],  # Truncate for metadata storage
                        "character_count": chunk.get("character_count", len(chunk_text)),
                        "token_count": chunk.get("token_count", len(chunk_text) // 4),
                        "chunk_position": {
                            "start": chunk.get("start_position", 0),
                            "end": chunk.get("end_position", len(chunk_text))
                        },
                        "processing_timestamp": metadata_result["metadata"]["processing_timestamp"],
                        "source_type": source_info.get("type", "document")
                    }
                    
                    # Add source-specific metadata
                    source_metadata = {}
                    
                    if index_name == "documentos-informes-vector":
                        source_metadata = {
                            "id_informe": source_info.get("id_informe", 1),
                            "id_emisor": source_info.get("id_emisor"),
                            "id_tipo_informe": source_info.get("id_tipo_informe"),
                            "id_frecuencia": source_info.get("id_frecuencia"),
                            "id_periodo": source_info.get("id_periodo"),
                            "fecha_publicacion": source_info.get("fecha_publicacion"),
                            "titulo_informe": source_info.get("titulo_informe", "")[:100],
                            "url_original": source_info.get("url_descarga_original", "")
                        }
                    
                    elif index_name == "dato-macroeconomico-vector":
                        source_metadata = {
                            "id_dato_macro": source_info.get("id_dato_macro", 1),
                            "indicador_nombre": source_info.get("indicador_nombre", "")[:100],
                            "fecha_dato": source_info.get("fecha_dato"),
                            "id_unidad_medida": source_info.get("id_unidad_medida"),
                            "id_moneda": source_info.get("id_moneda"),
                            "id_frecuencia": source_info.get("id_frecuencia"),
                            "id_emisor": source_info.get("id_emisor"),
                            "id_informe": source_info.get("id_informe"),
                            "valor_numerico": source_info.get("valor_numerico")
                        }
                    
                    elif index_name == "licitacion-contrato-vector":
                        source_metadata = {
                            "id_licitacion_contrato": source_info.get("id_licitacion_contrato", 1),
                            "titulo": source_info.get("titulo", "")[:100],
                            "id_emisor_adjudicado": source_info.get("id_emisor_adjudicado"),
                            "entidad_convocante": source_info.get("entidad_convocante", "")[:100],
                            "monto_adjudicado": source_info.get("monto_adjudicado"),
                            "id_moneda": source_info.get("id_moneda"),
                            "fecha_adjudicacion": source_info.get("fecha_adjudicacion")
                        }
                    
                    # Combine all metadata
                    full_metadata = {**base_metadata, **source_metadata}
                    
                    # Remove None values
                    full_metadata = {k: v for k, v in full_metadata.items() if v is not None}
                    
                    # Create vector data entry
                    vector_entry = {
                        "id": vector_id,
                        "text": chunk_text,
                        "metadata": full_metadata
                    }
                    
                    metadata_result["vector_data"].append(vector_entry)
                    metadata_result["report"]["vectors_prepared"] += 1
                    
                except Exception as chunk_error:
                    metadata_result["report"]["metadata_errors"].append({
                        "chunk_id": chunk.get("chunk_id", "unknown"),
                        "error": str(chunk_error)
                    })
            
            metadata_result["metadata"]["total_vectors"] = len(metadata_result["vector_data"])
            metadata_result["report"]["success"] = True
            
            return metadata_result
            
        except Exception as e:
            return {"error": f"Error preparing document metadata: {str(e)}", "chunks_data": chunks_data}

    @tool("Filter Duplicate Vectors Tool")
    def filter_duplicate_vectors(vector_data: list, index_name: str) -> dict:
        """Filter out vector data that already exists in Pinecone.
        
        Args:
            vector_data: List of prepared vector data entries
            index_name: Name of the Pinecone index
            
        Returns:
            Dictionary with filtered vector data and report
        """
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        
        if not pinecone_api_key:
            return {"error": "Pinecone API key not found in environment variables"}
        
        try:
            
            
            # Initialize Pinecone (nueva sintaxis)
            pc = Pinecone(api_key=pinecone_api_key)
            
            # Verificar si el índice existe
            if index_name not in [idx.name for idx in pc.list_indexes()]:
                return {"error": f"Index '{index_name}' does not exist in Pinecone"}
            
            index = pc.Index(index_name)
            
            filtered_data = {
                "new_vectors": [],
                "existing_vectors": [],
                "report": {
                    "total_vectors": len(vector_data),
                    "new_vectors": 0,
                    "existing_vectors": 0,
                    "index_name": index_name
                }
            }
            
            # Definir campos únicos por índice según tu estructura
            unique_field_mapping = {
                "documentos-informes-vector": ["id_informe", "chunk_id"],
                "dato-macroeconomico-vector": ["id_dato_macro", "chunk_id"],
                "licitacion-contrato-vector": ["id_licitacion_contrato", "chunk_id"]
            }
            
            if index_name not in unique_field_mapping:
                # Si no conocemos el índice, tratamos todos como nuevos
                filtered_data["new_vectors"] = vector_data
                filtered_data["report"]["new_vectors"] = len(vector_data)
                return filtered_data
            
            unique_fields = unique_field_mapping[index_name]
            
            # Procesar cada vector individualmente
            for vector in vector_data:
                if "metadata" not in vector:
                    filtered_data["new_vectors"].append(vector)
                    filtered_data["report"]["new_vectors"] += 1
                    continue
                
                metadata = vector["metadata"]
                
                # Verificar que los campos únicos existan
                if not all(field in metadata for field in unique_fields):
                    filtered_data["new_vectors"].append(vector)
                    filtered_data["report"]["new_vectors"] += 1
                    continue
                
                # Construir filtro de metadatos
                metadata_filter = {}
                for field in unique_fields:
                    metadata_filter[field] = {"$eq": metadata[field]}
                
                # Query para verificar existencia
                try:
                    result = index.query(
                        vector=[0.0] * 768,  # Vector dummy
                        filter=metadata_filter,
                        top_k=1,
                        include_metadata=False
                    )
                    
                    if result.get("matches", []):
                        filtered_data["existing_vectors"].append(vector)
                        filtered_data["report"]["existing_vectors"] += 1
                    else:
                        filtered_data["new_vectors"].append(vector)
                        filtered_data["report"]["new_vectors"] += 1
                        
                except Exception as query_error:
                    # Si falla la query, tratamos como nuevo por seguridad
                    filtered_data["new_vectors"].append(vector)
                    filtered_data["report"]["new_vectors"] += 1
            
            return filtered_data
            
        except Exception as e:
            return {"error": f"Error filtering duplicate vectors: {str(e)}", "vector_data": vector_data}
    
    
    @tool("Supabase Data Loading Tool")
    def load_data_to_supabase(table_name: str, data: list, test_mode: bool = None) -> str:
        """Load structured data into a Supabase table or save to file in test mode.
        
        Args:
            table_name: Name of the table to load data into
            data: List of records to insert
            test_mode: If True, save to file instead of loading to database
            
        Returns:
            Loading report as JSON string
        """
        # Use class test_mode if not specified
        if test_mode is None:
            test_mode = self.test_mode
            
        if not data:
            return json.dumps({"error": "No data provided to load"})
        
        # TEST MODE: Save to markdown file instead of database
        if test_mode:
            try:
                os.makedirs("output/test_results", exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"output/test_results/supabase_{table_name}_{timestamp}.md"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# Supabase Test Mode Output - {table_name}\n\n")
                    f.write(f"**Timestamp**: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"**Table**: {table_name}\n")
                    f.write(f"**Records Count**: {len(data)}\n\n")
                    f.write("## Data Preview (First 5 Records)\n\n")
                    
                    for i, record in enumerate(data[:5]):
                        f.write(f"### Record {i+1}\n")
                        f.write("```json\n")
                        f.write(json.dumps(record, indent=2, ensure_ascii=False, default=str))
                        f.write("\n```\n\n")
                        
                    if len(data) > 5:
                        f.write(f"... and {len(data) - 5} more records\n\n")
                    
                    f.write("## Complete Data\n\n")
                    f.write("```json\n")
                    f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
                    f.write("\n```\n")
                
                return json.dumps({
                    "status": "success",
                    "mode": "TEST_MODE",
                    "table_name": table_name,
                    "records_processed": len(data),
                    "output_file": filename,
                    "message": f"Test mode: Data saved to {filename} instead of loading to Supabase"
                }, indent=2)
                
            except Exception as e:
                return json.dumps({"error": f"Test mode file save failed: {str(e)}"})
        
        # PRODUCTION MODE: Actual database loading
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return json.dumps({"error": "Supabase credentials not found in environment variables"})
        
        try:
            # Initialize Supabase client - FIX: usar supabase_key en lugar de supabase_url
            supabase = create_client(supabase_url, supabase_key)
            
            loading_report = {
                "table": table_name,
                "total_records": len(data),
                "inserted": 0,
                "skipped": 0,
                "errors": [],
                "batches_processed": 0
            }
            
            # Validar estructura de datos
            if not isinstance(data, list) or not all(isinstance(record, dict) for record in data):
                return json.dumps({"error": "Data must be a list of dictionaries"})
            
            # Process in smaller batches para evitar timeouts
            batch_size = 50  # Reducir batch size
            total_batches = (len(data) + batch_size - 1) // batch_size
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                loading_report["batches_processed"] += 1
                
                try:
                    # Intentar inserción por lotes primero
                    result = supabase.table(table_name).insert(batch).execute()
                    loading_report["inserted"] += len(batch)
                    
                except Exception as batch_error:
                    # Si falla el lote, intentar uno por uno
                    for j, record in enumerate(batch):
                        try:
                            result = supabase.table(table_name).insert(record).execute()
                            loading_report["inserted"] += 1
                        except Exception as record_error:
                            loading_report["skipped"] += 1
                            loading_report["errors"].append({
                                "batch": loading_report["batches_processed"],
                                "record_index": i + j,
                                "record": record,
                                "error": str(record_error)
                            })
            
            # Agregar estadísticas finales
            loading_report["success_rate"] = (loading_report["inserted"] / loading_report["total_records"]) * 100
            loading_report["status"] = "completed"
            
            return json.dumps(loading_report, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Critical error loading data to Supabase: {str(e)}",
                "table": table_name,
                "status": "failed"
            })


    @tool("Pinecone Vector Loading Tool")
    def load_vectors_to_pinecone(index_name: str, vector_data: list, test_mode: bool = None) -> str:
        """Generate embeddings and load vector data into Pinecone or save to file in test mode.
        
        Args:
            index_name: Name of the Pinecone index
            vector_data: List of prepared vector data entries with 'text', 'id', 'metadata'
            test_mode: If True, save to file instead of loading to database
            
        Returns:
            Loading report as JSON string
        """
        # Use class test_mode if not specified
        if test_mode is None:
            test_mode = self.test_mode
            
        if not vector_data:
            return json.dumps({"error": "No vector data provided to load"})
        
        # TEST MODE: Save to markdown file instead of database
        if test_mode:
            try:
                os.makedirs("output/test_results", exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"output/test_results/pinecone_{index_name}_{timestamp}.md"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# Pinecone Test Mode Output - {index_name}\n\n")
                    f.write(f"**Timestamp**: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"**Index**: {index_name}\n")
                    f.write(f"**Vector Count**: {len(vector_data)}\n\n")
                    f.write("## Vector Data Preview (First 3 Vectors)\n\n")
                    
                    for i, vector in enumerate(vector_data[:3]):
                        f.write(f"### Vector {i+1}\n")
                        f.write(f"**ID**: `{vector.get('id', 'N/A')}`\n\n")
                        f.write(f"**Text Preview**: {vector.get('text', 'N/A')[:200]}...\n\n")
                        f.write("**Metadata**:\n")
                        f.write("```json\n")
                        f.write(json.dumps(vector.get('metadata', {}), indent=2, ensure_ascii=False, default=str))
                        f.write("\n```\n\n")
                        f.write("**Full Text Content**:\n")
                        f.write("```\n")
                        f.write(vector.get('text', 'N/A'))
                        f.write("\n```\n\n")
                        f.write("---\n\n")
                        
                    if len(vector_data) > 3:
                        f.write(f"... and {len(vector_data) - 3} more vectors\n\n")
                    
                    f.write("## Complete Vector Data\n\n")
                    f.write("```json\n")
                    f.write(json.dumps(vector_data, indent=2, ensure_ascii=False, default=str))
                    f.write("\n```\n")
                
                return json.dumps({
                    "status": "success",
                    "mode": "TEST_MODE", 
                    "index_name": index_name,
                    "vectors_processed": len(vector_data),
                    "output_file": filename,
                    "message": f"Test mode: Vector data saved to {filename} instead of loading to Pinecone"
                }, indent=2)
                
            except Exception as e:
                return json.dumps({"error": f"Test mode file save failed: {str(e)}"})
        
        # PRODUCTION MODE: Actual vector loading
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")  
        
        if not pinecone_api_key:
            return json.dumps({"error": "Pinecone API key not found in environment variables"})
        
        if not gemini_api_key:  # Cambio aquí
            return json.dumps({"error": "Gemini API key not found in environment variables"})
        
        try:
            # Initialize Pinecone y Gemini
            from pinecone import Pinecone
            import google.generativeai as genai  # Cambio aquí
            
            pc = Pinecone(api_key=pinecone_api_key)
            genai.configure(api_key=gemini_api_key)  # Nueva configuración
            
            # Check if index exists
            if index_name not in [idx.name for idx in pc.list_indexes()]:
                return json.dumps({"error": f"Index '{index_name}' does not exist in Pinecone"})
            
            index = pc.Index(index_name)
            
            loading_report = {
                "index": index_name,
                "total_vectors": len(vector_data),
                "processed": 0,
                "loaded": 0,
                "errors": [],
                "batches_processed": 0,
                "embedding_model": "models/embedding-001"  # Cambio aquí
            }
            
            # Validar estructura de vector_data
            for i, entry in enumerate(vector_data[:5]):
                if not all(key in entry for key in ["text", "id", "metadata"]):
                    return json.dumps({
                        "error": f"Invalid vector data structure at index {i}. Required keys: 'text', 'id', 'metadata'"
                    })
            
            # Process in smaller batches
            batch_size = 20
            
            for i in range(0, len(vector_data), batch_size):
                batch = vector_data[i:i+batch_size]
                vectors_to_upsert = []
                loading_report["batches_processed"] += 1
                
                # Create embeddings for batch
                for entry in batch:
                    try:
                        # Validar que el texto no esté vacío
                        if not entry["text"] or not entry["text"].strip():
                            loading_report["errors"].append({
                                "vector_id": entry.get("id", "unknown"),
                                "error": "Empty text content"
                            })
                            continue
                        
                        # Create embedding con Gemini
                        response = genai.embed_content(
                            model="models/embedding-001",
                            content=entry["text"].strip(),
                            task_type="retrieval_document"  # Para documentos
                        )
                        embedding = response['embedding']
                        
                        # Validar dimensiones del embedding (768 para Gemini)
                        if len(embedding) != 768:
                            loading_report["errors"].append({
                                "vector_id": entry["id"],
                                "error": f"Invalid embedding dimension: {len(embedding)}"
                            })
                            continue
                        
                        vectors_to_upsert.append({
                            "id": str(entry["id"]),
                            "values": embedding,
                            "metadata": entry["metadata"]
                        })
                        
                        loading_report["processed"] += 1
                        
                    except Exception as e:
                        loading_report["errors"].append({
                            "vector_id": entry.get("id", "unknown"),
                            "error": f"Embedding creation failed: {str(e)}"
                        })
                
                # Upsert vectors if any were created successfully
                if vectors_to_upsert:
                    try:
                        index.upsert(vectors=vectors_to_upsert)
                        loading_report["loaded"] += len(vectors_to_upsert)
                    except Exception as e:
                        loading_report["errors"].append({
                            "batch": loading_report["batches_processed"],
                            "error": f"Upsert failed: {str(e)}"
                        })
            
            # Estadísticas finales
            loading_report["success_rate"] = (loading_report["loaded"] / loading_report["total_vectors"]) * 100 if loading_report["total_vectors"] > 0 else 0
            loading_report["status"] = "completed"
            
            return json.dumps(loading_report, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Critical error loading vectors to Pinecone: {str(e)}",
                "index": index_name,
                "status": "failed"
            })

    @tool("Data Loading Status Tool")
    def check_loading_status(tables_to_check: list = None, indexes_to_check: list = None) -> dict:
        """Check the loading status of data in Supabase and Pinecone.
        
        Args:
            tables_to_check: List of Supabase tables to check (optional)
            indexes_to_check: List of Pinecone indexes to check (optional)
            
        Returns:
            Status report dictionary
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        
        status_report = {
            "supabase_status": {},
            "pinecone_status": {},
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "supabase_tables_checked": 0,
                "pinecone_indexes_checked": 0,
                "total_supabase_records": 0,
                "total_pinecone_vectors": 0
            }
        }
        
        # Check Supabase status
        if supabase_url and supabase_key:
            try:
                supabase = create_client(supabase_url, supabase_key)
                
                # Si no se especifican tablas, usar las del esquema
                if not tables_to_check:
                    tables_to_check = [
                        "Categoria_Emisor", "Emisores", "Moneda", "Frecuencia", 
                        "Tipo_Informe", "Periodo_Informe", "Unidad_Medida", 
                        "Instrumento", "Informe_General", "Resumen_Informe_Financiero",
                        "Dato_Macroeconomico", "Movimiento_Diario_Bolsa", "Licitacion_Contrato"
                    ]
                
                for table in tables_to_check:
                    try:
                        # FIX: Usar count() correctamente
                        result = supabase.table(table).select("*", count="exact", head=True).execute()
                        count = result.count or 0
                        
                        status_report["supabase_status"][table] = {
                            "count": count,
                            "status": "loaded" if count > 0 else "empty"
                        }
                        status_report["summary"]["total_supabase_records"] += count
                        status_report["summary"]["supabase_tables_checked"] += 1
                        
                    except Exception as table_error:
                        status_report["supabase_status"][table] = {
                            "error": str(table_error),
                            "status": "error"
                        }
                        
            except Exception as e:
                status_report["supabase_status"]["connection_error"] = str(e)
        else:
            status_report["supabase_status"]["error"] = "Supabase credentials not found"
        
        # Check Pinecone status
        if pinecone_api_key:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=pinecone_api_key)
                
                available_indexes = [idx.name for idx in pc.list_indexes()]
                status_report["pinecone_status"]["available_indexes"] = available_indexes
                
                # Si no se especifican índices, usar los del esquema
                if not indexes_to_check:
                    indexes_to_check = [
                        "documentos-informes-vector", 
                        "dato-macroeconomico-vector", 
                        "licitacion-contrato-vector"
                    ]
                
                for index_name in indexes_to_check:
                    try:
                        if index_name in available_indexes:
                            index = pc.Index(index_name)
                            stats = index.describe_index_stats()
                            
                            vector_count = stats.get("total_vector_count", 0)
                            status_report["pinecone_status"][index_name] = {
                                "vector_count": vector_count,
                                "dimension": stats.get("dimension", 0),
                                "status": "loaded" if vector_count > 0 else "empty"
                            }
                            status_report["summary"]["total_pinecone_vectors"] += vector_count
                        else:
                            status_report["pinecone_status"][index_name] = {
                                "status": "not_found",
                                "error": "Index does not exist"
                            }
                        
                        status_report["summary"]["pinecone_indexes_checked"] += 1
                        
                    except Exception as index_error:
                        status_report["pinecone_status"][index_name] = {
                            "error": str(index_error),
                            "status": "error"
                        }
                        
            except Exception as e:
                status_report["pinecone_status"]["connection_error"] = str(e)
        else:
            status_report["pinecone_status"]["error"] = "Pinecone API key not found"
        
        return status_report


    @tool("Batch Data Validation Tool")
    def validate_data_before_loading(table_name: str, data: list, index_name: str = None, vector_data: list = None) -> dict:
        """Validate data structure before loading to databases.
        
        Args:
            table_name: Supabase table name for structured data
            data: Structured data to validate
            index_name: Pinecone index name (optional)
            vector_data: Vector data to validate (optional)
            
        Returns:
            Validation report dictionary
        """
        validation_report = {
            "supabase_validation": {"valid": False, "errors": []},
            "pinecone_validation": {"valid": False, "errors": []},
            "recommendations": []
        }
        
        # Validar datos de Supabase
        if data:
            try:
                # Verificar que sea una lista
                if not isinstance(data, list):
                    validation_report["supabase_validation"]["errors"].append("Data must be a list")
                elif len(data) == 0:
                    validation_report["supabase_validation"]["errors"].append("Data list is empty")
                else:
                    # Verificar estructura de registros
                    for i, record in enumerate(data[:10]):  # Validar primeros 10
                        if not isinstance(record, dict):
                            validation_report["supabase_validation"]["errors"].append(f"Record {i} is not a dictionary")
                        elif len(record) == 0:
                            validation_report["supabase_validation"]["errors"].append(f"Record {i} is empty")
                    
                    if not validation_report["supabase_validation"]["errors"]:
                        validation_report["supabase_validation"]["valid"] = True
                        validation_report["recommendations"].append(f"Supabase data for {table_name} is valid for loading")
                        
            except Exception as e:
                validation_report["supabase_validation"]["errors"].append(f"Validation error: {str(e)}")
        
        # Validar datos de Pinecone
        if vector_data and index_name:
            try:
                if not isinstance(vector_data, list):
                    validation_report["pinecone_validation"]["errors"].append("Vector data must be a list")
                elif len(vector_data) == 0:
                    validation_report["pinecone_validation"]["errors"].append("Vector data list is empty")
                else:
                    # Verificar estructura de vectores
                    required_keys = ["text", "id", "metadata"]
                    for i, vector in enumerate(vector_data[:5]):  # Validar primeros 5
                        if not isinstance(vector, dict):
                            validation_report["pinecone_validation"]["errors"].append(f"Vector {i} is not a dictionary")
                        elif not all(key in vector for key in required_keys):
                            missing_keys = [key for key in required_keys if key not in vector]
                            validation_report["pinecone_validation"]["errors"].append(f"Vector {i} missing keys: {missing_keys}")
                        elif not vector.get("text", "").strip():
                            validation_report["pinecone_validation"]["errors"].append(f"Vector {i} has empty text content")
                    
                    if not validation_report["pinecone_validation"]["errors"]:
                        validation_report["pinecone_validation"]["valid"] = True
                        validation_report["recommendations"].append(f"Vector data for {index_name} is valid for loading")
                        
            except Exception as e:
                validation_report["pinecone_validation"]["errors"].append(f"Validation error: {str(e)}")
        
        # Recomendaciones generales
        if validation_report["supabase_validation"]["valid"] and validation_report["pinecone_validation"]["valid"]:
            validation_report["recommendations"].append("All data is valid. Proceed with loading.")
        elif validation_report["supabase_validation"]["valid"]:
            validation_report["recommendations"].append("Only Supabase data is valid. Check Pinecone data before loading.")
        elif validation_report["pinecone_validation"]["valid"]:
            validation_report["recommendations"].append("Only Pinecone data is valid. Check Supabase data before loading.")
        else:
            validation_report["recommendations"].append("Data validation failed. Fix errors before loading.")
        
        return validation_report
    
    @agent
    def extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['extractor'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                # serper_dev_tool,
                self.scrape_bva_emisores,
                self.scrape_bva_daily,
                self.scrape_bva_monthly,
                self.scrape_bva_annual,
                self.scrape_datos_gov,
                self.scrape_ine_main,
                self.scrape_ine_social,
                self.scrape_contrataciones,
                self.scrape_dnit_investment,
                self.scrape_dnit_financial
            ]
        )

    @agent
    def processor(self) -> Agent:
        return Agent(
            config=self.agents_config['processor'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm,
            tools=[
                self.normalize_data,
                self.validate_data,
                self.create_entity_relationships,
                self.structure_extracted_data,
                self.filter_duplicate_data,
            ]
        )
        
    @agent
    def vector(self) -> Agent:
        return Agent(
            config=self.agents_config['vector'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm,
            tools=[
                self.extract_text_from_pdf,
                self.chunk_document,
                self.prepare_document_metadata,
                self.filter_duplicate_vectors
            ]
        )

    @agent
    def loader(self) -> Agent:
        return Agent(
            config=self.agents_config['loader'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm,
            tools=[
                self.load_data_to_supabase,
                self.load_vectors_to_pinecone,
                self.check_loading_status,
                self.validate_data_before_loading
            ]
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
        """Creates the InverbotPipelineDato crew with performance tracking"""
        
        # Initialize performance tracking
        self.performance_metrics["pipeline_start_time"] = datetime.datetime.now().timestamp()
        self.log_performance("InverBot Pipeline Starting")
        self.log_performance(f"Test Mode: {'ENABLED' if self.test_mode else 'DISABLED'}")
        
        return Crew(
            agents=self.agents, 
            tasks=self.tasks, 
            process=Process.sequential,
            verbose=True,
            max_rpm=30
        )
    
    def kickoff_with_tracking(self):
        """Execute the crew with performance tracking"""
        try:
            self.log_performance("Starting pipeline execution...")
            
            # Get the crew and execute it
            crew_instance = self.crew()
            result = crew_instance.kickoff()
            
            # Pipeline completed successfully
            self.performance_metrics["pipeline_end_time"] = datetime.datetime.now().timestamp()
            self.log_performance("Pipeline completed successfully!")
            
            # Generate performance report
            report_file = self.generate_performance_report()
            self.log_performance(f"Performance report generated: {report_file}")
            
            return result
            
        except Exception as e:
            self.performance_metrics["pipeline_end_time"] = datetime.datetime.now().timestamp()
            self.log_performance(f"Pipeline failed: {str(e)}", "ERROR")
            
            # Generate performance report even on failure
            report_file = self.generate_performance_report()
            self.log_performance(f"Performance report generated: {report_file}")
            
            raise e
