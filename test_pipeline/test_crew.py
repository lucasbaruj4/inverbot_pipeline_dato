#!/usr/bin/env python3
"""
Isolated test file for the structured data processing pipeline.
Tests: Scraping -> PDF Extraction -> Data Structuring
All functions are exact copies from crew.py for production-level testing.
"""

import os
import re
import json
import time
import requests
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# ===================================================================
# SECTION 1: FIRECRAWL HELPER FUNCTIONS (from crew.py)
# ===================================================================

def get_firecrawl_app():
    """Initialize Firecrawl app with API key"""
    from firecrawl import FirecrawlApp
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not found in environment variables")
    return FirecrawlApp(api_key=api_key)

def _get_scrape_config_for_url(url: str, test_mode: bool = True) -> dict:
    """Get optimized scraping configuration based on URL/source type"""
    
    # Default configuration - much faster for testing
    default_config = {
        "wait_for": 1500 if test_mode else 5000,      # Reduced from 3000
        "timeout": 15000 if test_mode else 45000,     # Reduced from 30000
        "source_type": "generic"
    }
    
    # Source-specific optimizations - aggressive test mode settings
    if "bolsadevalores.com.py" in url or "bva" in url.lower():
        return {
            "wait_for": 2500 if test_mode else 8000,  # Reduced from 5000
            "timeout": 20000 if test_mode else 60000, # Reduced from 30000
            "source_type": "bva"
        }
    elif "ine.gov.py" in url:
        return {
            "wait_for": 1500 if test_mode else 5000,  # Reduced from 3000
            "timeout": 15000 if test_mode else 40000, # Reduced from 25000
            "source_type": "ine"
        }
    elif "datos.gov.py" in url:
        return {
            "wait_for": 2000 if test_mode else 6000,  # Reduced from 4000
            "timeout": 18000 if test_mode else 50000, # Reduced from 30000
            "source_type": "datos_gov"
        }
    elif "contrataciones.gov.py" in url:
        return {
            "wait_for": 3000 if test_mode else 10000, # Reduced from 6000
            "timeout": 20000 if test_mode else 60000, # Reduced from 35000
            "source_type": "contrataciones"
        }
    elif "dnit.gov.py" in url:
        return {
            "wait_for": 2000 if test_mode else 7000,  # Reduced from 4000
            "timeout": 18000 if test_mode else 50000, # Reduced from 30000
            "source_type": "dnit"
        }
    
    return default_config

def _execute_firecrawl_with_retry(operation_func, operation_name: str, max_retries: int = 2, retry_delay: int = 3):
    """Execute Firecrawl operation with retry logic for network resilience"""
    import time
    
    for attempt in range(max_retries):
        try:
            result = operation_func()
            if result:
                return result
            else:
                print(f"Attempt {attempt + 1}: Empty result for {operation_name}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                continue
        except Exception as e:
            error_message = str(e)
            if any(error_type in error_message.lower() for error_type in ['connection', 'timeout', 'network', 'refused']):
                print(f"Network error on attempt {attempt + 1} for {operation_name}: {error_message}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            else:
                # Non-network error, don't retry
                raise e
    
    raise Exception(f"Failed to execute {operation_name} after {max_retries} attempts")

def firecrawl_scrape_native(url, prompt="", schema={}, test_mode=True):
    """Custom Firecrawl scraper using direct API with optimized per-source configuration"""
    try:
        app = get_firecrawl_app()
        
        # Get optimized configuration for this URL
        scrape_config = _get_scrape_config_for_url(url, test_mode)
        
        print(f"SCRAPING {url} with config: {scrape_config['source_type']}")
        print(f"TIMING Wait time: {scrape_config['wait_for']}ms, Timeout: {scrape_config['timeout']}ms")
        
        def scrape_operation():
            return app.scrape_url(
                url=url,
                formats=["markdown"],
                only_main_content=True,
                wait_for=scrape_config["wait_for"],
                timeout=scrape_config["timeout"]
            )
        
        # Execute with retry logic - faster for testing
        result = _execute_firecrawl_with_retry(
            operation_func=scrape_operation,
            operation_name=f"scrape {url}",
            max_retries=2,  # Reduced from 3
            retry_delay=3   # Reduced from 5
        )
        
        # Extract content from response - handle both dict and object
        if isinstance(result, dict):
            # Dictionary response
            if 'data' in result and result['data']:
                data = result['data']
                if isinstance(data, dict):
                    if 'markdown' in data and data['markdown']:
                        print(f"SUCCESS Successfully scraped {len(data['markdown'])} characters")
                        return data['markdown']
                    elif 'content' in data and data['content']:
                        print(f"SUCCESS Successfully scraped {len(data['content'])} characters")
                        return data['content']
                    else:
                        return str(data)
                else:
                    # data is an object
                    if hasattr(data, 'markdown') and data.markdown:
                        print(f"SUCCESS Successfully scraped {len(data.markdown)} characters")
                        return data.markdown
                    elif hasattr(data, 'content') and data.content:
                        print(f"SUCCESS Successfully scraped {len(data.content)} characters")
                        return data.content
                    else:
                        return str(data)
            elif 'markdown' in result:
                print(f"SUCCESS Successfully scraped {len(result['markdown'])} characters")
                return result['markdown']
            elif 'content' in result:
                print(f"SUCCESS Successfully scraped {len(result['content'])} characters")
                return result['content']
            else:
                return str(result) if result else f"No content extracted from {url}"
        else:
            # Object response
            if hasattr(result, 'data') and result.data:
                if hasattr(result.data, 'markdown') and result.data.markdown:
                    print(f"SUCCESS Successfully scraped {len(result.data.markdown)} characters")
                    return result.data.markdown
                elif hasattr(result.data, 'content') and result.data.content:
                    print(f"SUCCESS Successfully scraped {len(result.data.content)} characters")
                    return result.data.content
                else:
                    return str(result.data)
            elif hasattr(result, 'markdown'):
                print(f"SUCCESS Successfully scraped {len(result.markdown)} characters")
                return result.markdown
            elif hasattr(result, 'content'):
                print(f"SUCCESS Successfully scraped {len(result.content)} characters")
                return result.content
            else:
                return str(result) if result else f"No content extracted from {url}"
            
    except Exception as e:
        print(f"ERROR Scrape error for {url}: {str(e)}")
        return f"Error with Firecrawl scraper: {str(e)}"

# ===================================================================
# SECTION 2: PDF EXTRACTION FUNCTION (from crew.py)
# ===================================================================

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
            
            return extraction_result
            
        except Exception as extraction_error:
            return {"error": f"Failed to extract text from PDF: {str(extraction_error)}", "pdf_url": pdf_url}
        
    except Exception as e:
        return {"error": f"Error in PDF text extraction: {str(e)}", "pdf_url": pdf_url}

# ===================================================================
# SECTION 3: STRUCTURED DATA PROCESSING (from crew.py)
# ===================================================================

class TestDataProcessor:
    """Contains all data processing methods from InverbotPipelineDato"""
    
    def _identify_content_type(self, url: str, content: str) -> str:
        """Identify the type of content based on URL and content patterns"""
        url_lower = url.lower()
        
        if "bva" in url_lower or "bolsadevalores" in url_lower:
            return "BVA Financial Data"
        elif "ine.gov.py" in url_lower:
            return "INE Statistical Data"
        elif "datos.gov.py" in url_lower:
            return "Open Government Data"
        elif "contrataciones" in url_lower:
            return "Public Contracts"
        elif "dnit" in url_lower:
            return "DNIT Investment/Financial"
        else:
            return "Generic Content"
    
    def _extract_title_from_link(self, link: str) -> str:
        """Extract a reasonable title from a URL or document link."""
        import re
        
        # Remove file extension and URL parameters
        title = link.split("/")[-1].split("?")[0]
        title = re.sub(r"\.(pdf|xlsx?|csv|doc|docx)$", "", title, flags=re.IGNORECASE)
        title = title.replace("_", " ").replace("-", " ").title()
        return title if len(title) > 3 else "Documento sin título específico"
    
    def _extract_date_from_content(self, content: str, context: str = "") -> str:
        """Extract date information from content or context."""
        import re
        from datetime import datetime
        
        # Look for year patterns
        year_pattern = r"20\d{2}"
        years = re.findall(year_pattern, content + " " + context)
        if years:
            return f"{years[0]}-01-01"  # Default to January 1st of found year
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_summary_from_content(self, content: str, link: str) -> str:
        """Extract a summary or description from content related to a link."""
        # Simple heuristic: find text near the link mention
        link_context = ""
        if link in content:
            link_pos = content.find(link)
            start = max(0, link_pos - 100)
            end = min(len(content), link_pos + 100)
            link_context = content[start:end].strip()
        
        return link_context if len(link_context) > 10 else "Documento extraído del contenido de la página"
    
    def _get_currency_name(self, code: str) -> str:
        """Get full currency name from code."""
        currency_names = {
            "USD": "Dólar Estadounidense",
            "GS": "Guaraní Paraguayo", 
            "EUR": "Euro",
            "ARS": "Peso Argentino"
        }
        return currency_names.get(code, f"Moneda {code}")
    
    def _process_bva_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Process BVA (stock exchange) content into structured format."""
        import re
        
        metrics = {"processing_method": "BVA_content_analysis"}
        
        # Extract emisores (issuers) information
        emisor_pattern = r"(?i)(banco|financiera|sa|s\.a\.|ltda|cooperativa|empresa|compañía)"
        emisor_matches = re.findall(r"([A-Z][A-Za-z\s]{3,50}(?:S\.?A\.?|LTDA\.?|BANCO|FINANCIERA))", content)
        
        for emisor_name in set(emisor_matches[:20]):  # Limit to 20 to avoid duplicates
            structured_data["Emisores"].append({
                "nombre_emisor": emisor_name.strip(),
                "id_categoria_emisor": 1,  # Default category
                "calificacion_bva": "No especificada"
            })
        
        # Extract reports from links and documents
        for link in links + documents:
            if any(term in link.lower() for term in ["informe", "reporte", "balance", "prospecto"]):
                # Determine report type
                if "anual" in link.lower():
                    tipo_informe = "Informe Anual"
                    frecuencia = "Anual"
                elif "mensual" in link.lower():
                    tipo_informe = "Informe Mensual"
                    frecuencia = "Mensual"
                elif "diario" in link.lower():
                    tipo_informe = "Informe Diario"
                    frecuencia = "Diario"
                else:
                    tipo_informe = "Informe General"
                    frecuencia = "Variable"
                
                structured_data["Informe_General"].append({
                    "titulo_informe": self._extract_title_from_link(link),
                    "id_tipo_informe": 1,  # Will be resolved by entity relationships tool
                    "fecha_publicacion": self._extract_date_from_content(content, link),
                    "url_descarga_original": link,
                    "resumen_informe": self._extract_summary_from_content(content, link)
                })
                
                # Add corresponding type and frequency
                if tipo_informe not in [t["nombre_tipo_informe"] for t in structured_data["Tipo_Informe"]]:
                    structured_data["Tipo_Informe"].append({"nombre_tipo_informe": tipo_informe})
                
                if frecuencia not in [f["nombre_frecuencia"] for f in structured_data["Frecuencia"]]:
                    structured_data["Frecuencia"].append({"nombre_frecuencia": frecuencia})
        
        # Extract financial movements data from content
        movement_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # Dates
            r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",  # Amounts
            r"(USD|GS|EUR|ARS)",  # Currencies
        ]
        
        for pattern in movement_patterns:
            matches = re.findall(pattern, content)
            if pattern == r"(USD|GS|EUR|ARS)" and matches:
                for currency in set(matches):
                    if currency not in [m["codigo_moneda"] for m in structured_data["Moneda"]]:
                        structured_data["Moneda"].append({
                            "codigo_moneda": currency,
                            "nombre_moneda": self._get_currency_name(currency)
                        })
        
        metrics["emisores_extracted"] = len(structured_data["Emisores"])
        metrics["reports_extracted"] = len(structured_data["Informe_General"])
        metrics["currencies_extracted"] = len(structured_data["Moneda"])
        
        return structured_data, metrics
    
    def _process_ine_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Process INE (statistics institute) content into structured format."""
        from datetime import datetime
        
        metrics = {"processing_method": "INE_content_analysis"}
        
        # Extract statistical reports and publications
        for link in links + documents:
            if any(term in link.lower() for term in ["pdf", "publicacion", "censo", "encuesta", "estadistica"]):
                structured_data["Informe_General"].append({
                    "titulo_informe": self._extract_title_from_link(link),
                    "id_tipo_informe": 2,  # Statistical report type
                    "fecha_publicacion": self._extract_date_from_content(content, link),
                    "url_descarga_original": link,
                    "resumen_informe": self._extract_summary_from_content(content, link)
                })
        
        # Extract macroeconomic indicators
        macro_indicators = [
            "PIB", "inflación", "desempleo", "pobreza", "población", "vivienda",
            "educación", "salud", "ingresos", "exportaciones", "importaciones"
        ]
        
        for indicator in macro_indicators:
            if indicator.lower() in content.lower():
                structured_data["Dato_Macroeconomico"].append({
                    "indicador_nombre": indicator,
                    "fecha_dato": datetime.now().strftime("%Y-%m-%d"),
                    "valor_numerico": 0.0,  # Will be extracted by more specific parsing
                    "id_frecuencia": 1,
                    "otras_propiedades_jsonb": {"source": "INE", "extraction_method": "content_analysis"}
                })
        
        # Add INE as default emisor
        structured_data["Emisores"].append({
            "nombre_emisor": "Instituto Nacional de Estadística",
            "id_categoria_emisor": 2,  # Government institution
            "calificacion_bva": "Institución Gubernamental"
        })
        
        metrics["reports_extracted"] = len(structured_data["Informe_General"])
        metrics["indicators_identified"] = len(structured_data["Dato_Macroeconomico"])
        
        return structured_data, metrics
    
    def _process_datos_gov_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Process open data portal content into structured format."""
        metrics = {"processing_method": "open_data_analysis"}
        
        # Similar processing for other content types...
        # Extract datasets and reports from open data portal
        for link in links + documents:
            if any(term in link.lower() for term in ["dataset", "csv", "excel", "datos"]):
                structured_data["Informe_General"].append({
                    "titulo_informe": self._extract_title_from_link(link),
                    "id_tipo_informe": 3,  # Dataset type
                    "fecha_publicacion": self._extract_date_from_content(content, link),
                    "url_descarga_original": link,
                    "resumen_informe": "Dataset del portal de datos abiertos"
                })
        
        return structured_data, metrics
    
    def _process_contracts_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Process public contracts content into structured format."""
        import re
        from datetime import datetime
        
        metrics = {"processing_method": "contracts_analysis"}
        
        # Extract contract information
        contract_pattern = r"(?i)(licitación|contrato|adjudicación|convocatoria)"
        if re.search(contract_pattern, content):
            # Extract contract titles and amounts
            amount_pattern = r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(gs|guaraníes|usd|dólares)"
            amounts = re.findall(amount_pattern, content.lower())
            
            for amount, currency in amounts[:10]:  # Limit to first 10 contracts
                structured_data["Licitacion_Contrato"].append({
                    "titulo": "Contrato público identificado",
                    "entidad_convocante": "Entidad gubernamental",
                    "monto_adjudicado": float(amount.replace(".", "").replace(",", ".")),
                    "fecha_adjudicacion": datetime.now().strftime("%Y-%m-%d")
                })
        
        return structured_data, metrics
    
    def _process_dnit_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Process DNIT investment/financial content into structured format."""
        metrics = {"processing_method": "DNIT_analysis"}
        
        # Extract investment reports and financial documents
        for link in links + documents:
            if any(term in link.lower() for term in ["informe", "financiero", "inversion", "pdf"]):
                structured_data["Informe_General"].append({
                    "titulo_informe": self._extract_title_from_link(link),
                    "id_tipo_informe": 4,  # Financial/investment report
                    "fecha_publicacion": self._extract_date_from_content(content, link),
                    "url_descarga_original": link,
                    "resumen_informe": "Informe financiero o de inversión DNIT"
                })
        
        return structured_data, metrics
    
    def _process_generic_content(self, content: str, links: list, documents: list, structured_data: dict) -> tuple:
        """Generic processing for unknown content types."""
        from datetime import datetime
        
        metrics = {"processing_method": "generic_analysis"}
        
        # Basic extraction of any documents found
        for link in links + documents:
            structured_data["Informe_General"].append({
                "titulo_informe": self._extract_title_from_link(link),
                "id_tipo_informe": 5,  # Generic document
                "fecha_publicacion": datetime.now().strftime("%Y-%m-%d"),
                "url_descarga_original": link,
                "resumen_informe": "Documento identificado en fuente desconocida"
            })
        
        return structured_data, metrics
    
    def extract_structured_data_from_raw(self, raw_content: dict) -> dict:
        """Convert raw scraped content into structured database format.
        
        This is the main processing function that takes raw content and
        structures it for the 14 Supabase tables.
        """
        import re
        from datetime import datetime
        import json
        
        try:
            # Extract content from raw_content
            page_content = raw_content.get("page_content", "")
            links = raw_content.get("links", [])
            documents = raw_content.get("documents", [])
            metadata = raw_content.get("metadata", {})
            
            # Initialize structured data for all 14 tables
            structured_data = {
                "Categoria_Emisor": [],
                "Emisores": [],
                "Moneda": [],
                "Frecuencia": [],
                "Tipo_Informe": [],
                "Periodo_Informe": [],
                "Unidad_Medida": [],
                "Instrumento": [],
                "Informe_General": [],
                "Resumen_Informe_Financiero": [],
                "Dato_Macroeconomico": [],
                "Movimiento_Diario_Bolsa": [],
                "Licitacion_Contrato": []
            }
            
            processing_report = {
                "status": "success",
                "records_extracted": 0,
                "tables_populated": 0,
                "processing_notes": [],
                "data_quality_metrics": {},
                "extraction_summary": ""
            }
            
            # Analyze content type based on URL and content patterns
            source_url = metadata.get("url", "")
            content_type = self._identify_content_type(source_url, page_content)
            
            # Route processing based on content type
            if "bva" in source_url.lower() or "bolsadevalores" in source_url.lower():
                structured_data, metrics = self._process_bva_content(page_content, links, documents, structured_data)
            elif "ine.gov.py" in source_url.lower():
                structured_data, metrics = self._process_ine_content(page_content, links, documents, structured_data)
            elif "datos.gov.py" in source_url.lower():
                structured_data, metrics = self._process_datos_gov_content(page_content, links, documents, structured_data)
            elif "contrataciones.gov.py" in source_url.lower():
                structured_data, metrics = self._process_contracts_content(page_content, links, documents, structured_data)
            elif "dnit.gov.py" in source_url.lower():
                structured_data, metrics = self._process_dnit_content(page_content, links, documents, structured_data)
            else:
                # Generic processing for unknown sources
                structured_data, metrics = self._process_generic_content(page_content, links, documents, structured_data)
            
            # Update processing report
            processing_report["records_extracted"] = sum(len(records) for records in structured_data.values())
            processing_report["tables_populated"] = sum(1 for records in structured_data.values() if len(records) > 0)
            processing_report["data_quality_metrics"] = metrics
            processing_report["extraction_summary"] = f"Processed {content_type} content from {source_url}, extracted {processing_report['records_extracted']} records across {processing_report['tables_populated']} tables"
            
            # Add processing metadata
            processing_report["processing_notes"].append(f"Content type identified as: {content_type}")
            processing_report["processing_notes"].append(f"Source URL: {source_url}")
            processing_report["processing_notes"].append(f"Content length: {len(page_content)} characters")
            processing_report["processing_notes"].append(f"Links found: {len(links)}")
            processing_report["processing_notes"].append(f"Documents found: {len(documents)}")
            
            return {
                "structured_data": structured_data,
                "processing_report": processing_report,
                "raw_content_summary": {
                    "content_length": len(page_content),
                    "links_count": len(links),
                    "documents_count": len(documents),
                    "source_identified": content_type
                }
            }
            
        except Exception as e:
            return {
                "structured_data": {table: [] for table in ["Categoria_Emisor", "Emisores", "Moneda", "Frecuencia", "Tipo_Informe", "Periodo_Informe", "Unidad_Medida", "Instrumento", "Informe_General", "Resumen_Informe_Financiero", "Dato_Macroeconomico", "Movimiento_Diario_Bolsa", "Licitacion_Contrato"]},
                "processing_report": {
                    "status": "error",
                    "error": str(e),
                    "records_extracted": 0,
                    "tables_populated": 0,
                    "processing_notes": [f"Error during processing: {str(e)}"],
                    "extraction_summary": "Processing failed due to error"
                },
                "raw_content_summary": {
                    "content_length": len(str(raw_content)),
                    "error": str(e)
                }
            }

# ===================================================================
# SECTION 4: SIMPLIFIED BVA SCRAPER
# ===================================================================

def extract_pdf_links_from_markdown(markdown_content: str) -> List[str]:
    """Extract PDF links from markdown content"""
    pdf_links = []
    
    # Look for markdown links ending in .pdf
    pdf_pattern = r'\[.*?\]\((https?://[^\)]+\.pdf)\)'
    pdf_matches = re.findall(pdf_pattern, markdown_content, re.IGNORECASE)
    pdf_links.extend(pdf_matches)
    
    # Also look for plain URLs ending in .pdf
    plain_pdf_pattern = r'https?://[^\s\)]+\.pdf'
    plain_matches = re.findall(plain_pdf_pattern, markdown_content, re.IGNORECASE)
    pdf_links.extend(plain_matches)
    
    # Remove duplicates
    pdf_links = list(set(pdf_links))
    
    return pdf_links

def extract_all_links_from_markdown(markdown_content: str) -> List[str]:
    """Extract all links from markdown content"""
    all_links = []
    
    # Look for markdown links
    link_pattern = r'\[.*?\]\((https?://[^\)]+)\)'
    link_matches = re.findall(link_pattern, markdown_content)
    all_links.extend(link_matches)
    
    # Also look for plain URLs
    plain_link_pattern = r'https?://[^\s\)]+'
    plain_matches = re.findall(plain_link_pattern, markdown_content)
    all_links.extend(plain_matches)
    
    # Remove duplicates
    all_links = list(set(all_links))
    
    return all_links

def scrape_bva_simplified():
    """Scrape BVA page and extract PDF links"""
    # Try informes-mensuales page which usually has PDFs
    url = "https://www.bolsadevalores.com.py/informes-mensuales/"
    
    print(f"Scraping BVA URL: {url}")
    result = firecrawl_scrape_native(url, "", {}, test_mode=True)
    
    if isinstance(result, str) and len(result) > 100:
        # Parse markdown to find PDF links
        pdf_links = extract_pdf_links_from_markdown(result)
        all_links = extract_all_links_from_markdown(result)
        
        print(f"Found {len(pdf_links)} PDF links")
        print(f"Found {len(all_links)} total links")
        
        return {
            "markdown": result,
            "pdf_links": pdf_links,
            "links": all_links
        }
    else:
        print("Failed to scrape BVA content or content too short")
        return {
            "markdown": str(result),
            "pdf_links": [],
            "links": []
        }

# ===================================================================
# SECTION 5: MAIN TEST PIPELINE
# ===================================================================

def test_pipeline():
    """Run isolated test of scraping -> PDF extraction -> structuring"""
    
    print("\n" + "="*70)
    print("ISOLATED PIPELINE TEST: SCRAPING -> PDF EXTRACTION -> STRUCTURING")
    print("="*70)
    
    # Initialize processor
    processor = TestDataProcessor()
    
    # Step 1: Scrape BVA page to get content and PDF links
    print("\nStep 1: Scraping BVA for content and PDF links...")
    print("-" * 50)
    raw_content = scrape_bva_simplified()
    
    if not raw_content.get("markdown"):
        print("ERROR: Failed to scrape BVA content")
        return
    
    print(f"Scraped {len(raw_content['markdown'])} characters of content")
    print(f"Found {len(raw_content['pdf_links'])} PDF links")
    
    # Step 2: Extract PDFs found in links (limit to 2 for testing)
    print("\nStep 2: Extracting text from PDFs...")
    print("-" * 50)
    pdf_texts = []
    pdf_limit = min(2, len(raw_content.get("pdf_links", [])))
    
    if pdf_limit > 0:
        print(f"Processing first {pdf_limit} PDFs...")
        for i, pdf_url in enumerate(raw_content.get("pdf_links", [])[:pdf_limit]):
            print(f"\nPDF {i+1}: {pdf_url}")
            pdf_result = extract_text_from_pdf(pdf_url)
            
            if pdf_result.get("extracted_text"):
                pdf_texts.append(pdf_result["extracted_text"])
                print(f"  SUCCESS: Extracted {len(pdf_result['extracted_text'])} characters")
                print(f"  Pages: {pdf_result['report']['pages_processed']}, With text: {pdf_result['report']['pages_with_text']}")
            elif pdf_result.get("error"):
                print(f"  ERROR: {pdf_result['error']}")
            else:
                print(f"  WARNING: No text extracted")
    else:
        print("No PDFs found to process")
    
    # Step 3: Combine all content
    print("\nStep 3: Combining all content...")
    print("-" * 50)
    combined_page_content = raw_content.get("markdown", "")
    if pdf_texts:
        combined_page_content += "\n\n=== PDF CONTENT ===\n\n" + "\n\n".join(pdf_texts)
    
    combined_content = {
        "page_content": combined_page_content,
        "links": raw_content.get("links", []),
        "documents": raw_content.get("pdf_links", []),
        "metadata": {
            "url": "https://www.bolsadevalores.com.py",
            "source_type": "bva_daily",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    print(f"Total content length: {len(combined_page_content)} characters")
    print(f"Total links: {len(combined_content['links'])}")
    print(f"Total documents: {len(combined_content['documents'])}")
    
    # Step 4: Process into structured data
    print("\nStep 4: Processing into structured data...")
    print("-" * 50)
    structured_result = processor.extract_structured_data_from_raw(combined_content)
    
    # Step 5: Display results
    print_results(structured_result)
    
    # Save results to file for inspection
    save_results_to_file(structured_result)

def print_results(structured_result):
    """Print detailed test results"""
    print("\n" + "="*70)
    print("STRUCTURED DATA EXTRACTION RESULTS")
    print("="*70)
    
    # Processing Report
    report = structured_result.get("processing_report", {})
    print(f"\nProcessing Status: {report.get('status', 'unknown')}")
    
    if report.get('status') == 'error':
        print(f"ERROR: {report.get('error', 'Unknown error')}")
    
    print(f"Records Extracted: {report.get('records_extracted', 0)}")
    print(f"Tables Populated: {report.get('tables_populated', 0)}")
    
    # Data Quality Metrics
    metrics = report.get('data_quality_metrics', {})
    if metrics:
        print("\nData Quality Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
    
    # Structured Data by Table
    print("\nStructured Data by Table:")
    print("-" * 50)
    
    structured_data = structured_result.get("structured_data", {})
    for table_name, records in structured_data.items():
        if records:
            print(f"\n{table_name}: {len(records)} records")
            # Show first record as sample
            if records:
                sample = records[0]
                print("  Sample record:")
                for key, value in list(sample.items())[:5]:  # Show first 5 fields
                    value_str = str(value)[:100]  # Limit value length
                    print(f"    {key}: {value_str}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Extraction Summary: {report.get('extraction_summary', 'N/A')}")
    
    # Processing Notes
    if report.get('processing_notes'):
        print("\nProcessing Notes:")
        for note in report['processing_notes']:
            print(f"  - {note}")

def save_results_to_file(structured_result):
    """Save results to JSON file for inspection"""
    output_file = "test_pipeline_results.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nResults saved to: {output_file}")
    except Exception as e:
        print(f"\nFailed to save results: {str(e)}")

# ===================================================================
# MAIN EXECUTION
# ===================================================================

if __name__ == "__main__":
    # Load environment variables from .env.local
    from dotenv import load_dotenv
    
    # Try to load .env.local file
    env_file = ".env.local"
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
    
    # Check for required environment variables
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("ERROR: FIRECRAWL_API_KEY environment variable not set")
        print("Please set it in .env.local or environment")
        exit(1)
    
    # Run the test pipeline
    test_pipeline()