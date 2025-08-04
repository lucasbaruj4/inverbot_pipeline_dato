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
            
            if schema and "properties" in schema:
                for prop_name, prop_value in schema["properties"].items():
                    if "items" in prop_value and prop_value["type"] == "array":
                        prop_value["maxItems"] = 3
            
            
            
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
            
            if schema and "properties" in schema:
                for prop_name, prop_value in schema["properties"].items():
                    if "items" in prop_value and prop_value["type"] == "array":
                        prop_value["maxItems"] = 3
            
            
            
        response = requests.post(
            "https://api.firecrawl.dev/v1/crawl",
            headers={"Authorization": f"Bearer: {api_key}"},
            json=payload
        )
        if response.status == 200:
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


    # 1. Balances de Empresas
    @tool("BVA Emisores Scraper")
    def scrape_bva_emisores(test_mode=True) -> str:
        """Scrapes BVA emisores listing page. Contains list of issuers, balances, prospectuses, risk analysis and relevant facts."""
        schema = {
            "type": "object",
            "properties": {
                "Categoria_Emisor": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_categoria_emisor": {"type": "integer"},
                            "categoria_emisor": {"type": "string"}
                        },
                        "required": ["categoria_emisor"]
                    }
                },
                "Emisores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_emisor": {"type": "integer"},
                            "nombre_emisor": {"type": "string"},
                            "id_categoria_emisor": {"type": "integer"},
                            "calificacion_bva": {"type": "string"}
                        },
                        "required": ["nombre_emisor"]
                    }
                },
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
                            "url_descarga_original": {"type": "string"},
                            "detalles_informe_jsonb": {"type": "object", "additionalProperties": True},
                            "contenido_raw": {"type": "string", "description": "Contenido textual sin procesar del informe o documento"}
                        },
                        "required": ["titulo_informe", "fecha_publicacion"]
                    }
                },
                "Resumen_Informe_Financiero": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_resumen_financiero": {"type": "integer"},
                            "id_informe": {"type": "integer"},
                            "id_emisor": {"type": "integer"},
                            "fecha_corte_informe": {"type": "string", "format": "date"},
                            "moneda_informe": {"type": "integer"},
                            "activos_totales": {"type": "number"},
                            "pasivos_totales": {"type": "number"},
                            "patrimonio_neto": {"type": "number"},
                            "disponible": {"type": "number"},
                            "utilidad_del_ejercicio": {"type": "number"},
                            "ingresos_totales": {"type": "number"},
                            "costos_operacionales": {"type": "number"},
                            "total_ganancias": {"type": "number"},
                            "total_perdidas": {"type": "number"},
                            "retorno_sobre_patrimonio": {"type": "number"},
                            "calificacion_riesgo_tendencia": {"type": "string"},
                            "utilidad_neta_por_accion_ordinaria": {"type": "number"},
                            "deuda_total": {"type": "number"},
                            "ebitda": {"type": "number"},
                            "margen_neto": {"type": "number"},
                            "flujo_caja_operativo": {"type": "number"},
                            "capital_integrado": {"type": "number"},
                            "otras_metricas_jsonb": {"type": "object", "additionalProperties": True}
                        },
                        "required": ["id_emisor", "fecha_corte_informe"]
                    }
                }
            },
            "required": ["Emisores"]
        }
        
        url = "https://www.bolsadevalores.com.py/listado-de-emisores/"
        prompt = """Extrae la siguiente información:
        1. Lista de categorías de emisores (Categoria_Emisor)
        2. Lista completa de emisores con nombre, categoría y calificación (Emisores)
        3. Todos los informes disponibles para cada emisor con título, fecha, URL y resumen (Informe_General)
        4. Datos financieros estructurados de los balances para cada emisor (Resumen_Informe_Financiero)
        
        Para cada documento o informe, incluye también el contenido raw cuando sea posible. Mantén la relación entre las tablas usando los IDs correspondientes.
        GUIA DE CRAWLING
        Cuando entres a la pagina te vas a encontrar con un listado de emisores, para ver mas emisores vas a tener que darle al boton que dice 'Cargar Mas', debes entrar en todos los emisores que encuentres y extraer los documentos que se te indican arriba. Tené en cuenta que vas a tener que guardar los links que llevan a los informes y tambien el texto para su posterior vectorizacion de los informes y otros documentos que encuentres en donde hayan metricas importantes. Adentro de cada emisor los documentos que buscamos estan bajo elementos que dice 'Balances', 'Prospectos', 'Calificaciones' y 'Hechos de Relevancia'."""
        
        return firecrawl_crawl(url, prompt, schema, test_mode)


    # 2. Movimientos Diarios
    @tool("BVA Daily Reports Scraper")
    def scrape_bva_daily(test_mode=True) -> str:
        """Scrapes BVA daily market movements reports."""
        schema = {
            "type": "object",
            "properties": {
                "Movimiento_Diario_Bolsa": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_operacion": {"type": "integer"},
                            "fecha_operacion": {"type": "string", "format": "date"},
                            "cantidad_operacion": {"type": "number"},
                            "id_instrumento": {"type": "integer"},
                            "id_emisor": {"type": "integer"},
                            "fecha_vencimiento_instrumento": {"type": "string", "format": "date"},
                            "id_moneda": {"type": "integer"},
                            "precio_operacion": {"type": "number"},
                            "precio_anterior_instrumento": {"type": "number"},
                            "tasa_interes_nominal": {"type": "number"},
                            "tipo_cambio": {"type": "number"},
                            "variacion_operacion": {"type": "number"},
                            "volumen_gs_operacion": {"type": "number"}
                        },
                        "required": ["fecha_operacion", "id_instrumento", "precio_operacion"]
                    }
                },
                "Instrumento": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id_instrumento": {"type": "integer"},
                            "simbolo_instrumento": {"type": "string"},
                            "nombre_instrumento": {"type": "string"}
                        },
                        "required": ["simbolo_instrumento"]
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
                            "fecha_publicacion": {"type": "string", "format": "date"},
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
    def load_data_to_supabase(table_name: str, data: list) -> str:
        """Load structured data into a Supabase table.
        
        Args:
            table_name: Name of the table to load data into
            data: List of records to insert
            
        Returns:
            Loading report as JSON string
        """
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return json.dumps({"error": "Supabase credentials not found in environment variables"})
        
        if not data:
            return json.dumps({"error": "No data provided to load"})
        
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
    def load_vectors_to_pinecone(index_name: str, vector_data: list) -> str:
        """Generate embeddings and load vector data into Pinecone.
        
        Args:
            index_name: Name of the Pinecone index
            vector_data: List of prepared vector data entries with 'text', 'id', 'metadata'
            
        Returns:
            Loading report as JSON string
        """
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")  
        
        if not pinecone_api_key:
            return json.dumps({"error": "Pinecone API key not found in environment variables"})
        
        if not gemini_api_key:  # Cambio aquí
            return json.dumps({"error": "Gemini API key not found in environment variables"})
        
        if not vector_data:
            return json.dumps({"error": "No vector data provided to load"})
        
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
                self.filter_duplicate_data
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
        """Creates the InverbotPipelineDato crew"""

        return Crew(
            agents=self.agents, 
            tasks=self.tasks, 
            process=Process.sequential,
            verbose=True,
            max_rpm=30
        )
