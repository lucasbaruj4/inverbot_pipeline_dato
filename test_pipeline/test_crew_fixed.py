#!/usr/bin/env python3
"""
Fixed test file for the complete structured data processing pipeline.
Tests: Scraping -> PDF Extraction -> Data Structuring -> Vectorization
All functions are standalone for proper tool binding.
"""

import os
import re
import json
import time
import requests
import io
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from crewai_tools import FileReadTool, DirectoryReadTool

# Load environment variables from .env.local
from dotenv import load_dotenv
load_dotenv('.env.local')

# ===================================================================
# SECTION 1: FIRECRAWL HELPER FUNCTIONS
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
        "wait_for": 1500 if test_mode else 5000,
        "timeout": 15000 if test_mode else 45000,
        "source_type": "generic"
    }
    
    # Source-specific optimizations - aggressive test mode settings
    if "bolsadevalores.com.py" in url or "bva" in url.lower():
        return {
            "wait_for": 2500 if test_mode else 8000,
            "timeout": 20000 if test_mode else 60000,
            "source_type": "bva"
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
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            else:
                raise e
    
    raise Exception(f"Failed to execute {operation_name} after {max_retries} attempts")

def firecrawl_scrape_native(url: str, prompt: str = "", schema: dict = {}, test_mode: bool = True):
    """Native Firecrawl scraping with enhanced error handling"""
    try:
        app = get_firecrawl_app()
        config = _get_scrape_config_for_url(url, test_mode)
        
        scrape_options = {
            "pageOptions": {
                "onlyMainContent": True,
                "removeBase64Images": True,
                "waitFor": config["wait_for"],
                "timeout": config["timeout"]
            }
        }
        
        def scrape_operation():
            return app.scrape_url(
                url=url,
                formats=["markdown"],
                wait_for=config["wait_for"],
                timeout=config["timeout"]
            )
        
        result = _execute_firecrawl_with_retry(
            scrape_operation, 
            f"Firecrawl scrape for {url}", 
            max_retries=2, 
            retry_delay=3
        )
        
        return {
            "page_content": getattr(result, 'markdown', ''),
            "links": getattr(result, 'linksOnPage', []),
            "documents": [link for link in getattr(result, 'linksOnPage', []) if any(ext in link.lower() for ext in ['.pdf', '.xlsx', '.xls', '.doc', '.docx'])],
            "metadata": {
                "url": url,
                "source_type": config["source_type"],
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        print(f"Firecrawl error for {url}: {str(e)}")
        return {
            "page_content": f"Error: {str(e)}",
            "links": [],
            "documents": [],
            "metadata": {"url": url, "error": str(e)}
        }

# ===================================================================
# SECTION 2: STANDALONE TOOL DEFINITIONS
# ===================================================================

@tool("BVA Daily Reports Scraper")
def scrape_bva_daily() -> str:
    """Scrapes BVA daily reports for testing"""
    url = "https://www.bolsadevalores.com.py/informes-diarios/"
    
    try:
        result = firecrawl_scrape_native(url, "", {}, True)  # test_mode = True
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return f"Error scraping BVA Daily: {str(e)}"

@tool("BVA Monthly Reports Scraper")
def scrape_bva_monthly() -> str:
    """Scrapes BVA monthly reports for testing"""
    url = "https://www.bolsadevalores.com.py/informes-mensuales/"
    
    try:
        result = firecrawl_scrape_native(url, "", {}, True)  # test_mode = True
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return f"Error scraping BVA Monthly: {str(e)}"

@tool("Extract Text from PDF")
def extract_text_from_pdf(pdf_url: str) -> str:
    """Extract text content from PDF documents"""
    try:
        import fitz  # PyMuPDF
        
        # Download PDF
        response = requests.get(pdf_url, timeout=30)
        if response.status_code != 200:
            return json.dumps({"error": f"Failed to download PDF: HTTP {response.status_code}"})
        
        # Extract text
        pdf_document = fitz.open(stream=response.content, filetype="pdf")
        text_content = ""
        
        for page_num in range(min(5, len(pdf_document))):  # Limit to 5 pages for testing
            page = pdf_document.load_page(page_num)
            text_content += page.get_text()
        
        pdf_document.close()
        
        result = {
            "pdf_url": pdf_url,
            "text_content": text_content,
            "pages_extracted": min(5, len(pdf_document)),
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"PDF extraction failed: {str(e)}", "pdf_url": pdf_url})

@tool("Extract Text from Excel")
def extract_text_from_excel(excel_url: str) -> str:
    """Extract text content from Excel documents"""
    try:
        import pandas as pd
        
        # Download Excel file
        response = requests.get(excel_url, timeout=30)
        if response.status_code != 200:
            return json.dumps({"error": f"Failed to download Excel: HTTP {response.status_code}"})
        
        # Read Excel content
        excel_data = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        
        text_content = ""
        sheets_processed = 0
        
        for sheet_name, df in excel_data.items():
            if sheets_processed >= 3:  # Limit to 3 sheets for testing
                break
            
            text_content += f"\\n\\n=== Sheet: {sheet_name} ===\\n"
            text_content += df.to_string(index=False)
            sheets_processed += 1
        
        result = {
            "excel_url": excel_url,
            "text_content": text_content,
            "sheets_processed": sheets_processed,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"Excel extraction failed: {str(e)}", "excel_url": excel_url})

@tool("Extract Structured Data from Raw Content")
def extract_structured_data_from_raw(raw_content: dict) -> dict:
    """Convert raw scraped content into structured database format"""
    try:
        # Extract content from raw_content
        page_content = raw_content.get("page_content", "")
        links = raw_content.get("links", [])
        documents = raw_content.get("documents", [])
        metadata = raw_content.get("metadata", {})
        
        # Initialize structured data for all tables
        structured_data = {
            "Categoria_Emisor": [{"id_categoria_emisor": 1, "categoria_emisor": "Sociedades Anónimas"}],
            "Emisores": [],
            "Moneda": [{"id_moneda": 1, "codigo_moneda": "PYG", "nombre_moneda": "Paraguayan Guarani"}],
            "Frecuencia": [{"id_frecuencia": 1, "nombre_frecuencia": "Daily"}],
            "Tipo_Informe": [{"id_tipo_informe": 1, "nombre_tipo_informe": "Market Report"}],
            "Periodo_Informe": [{"id_periodo": 1, "nombre_periodo": "2024"}],
            "Unidad_Medida": [{"id_unidad_medida": 1, "simbolo": "%", "nombre_unidad": "Percentage"}],
            "Instrumento": [],
            "Informe_General": [],
            "Resumen_Informe_Financiero": [],
            "Dato_Macroeconomico": [],
            "Movimiento_Diario_Bolsa": [],
            "Licitacion_Contrato": []
        }
        
        # Get URL from metadata or use first link as fallback
        source_url = metadata.get("url", "")
        if not source_url and links:
            source_url = links[0]
        elif not source_url:
            source_url = "unknown"
        
        # Simple content processing for BVA data
        if "bva" in source_url.lower() or "bolsadevalores" in source_url.lower():
            # Extract simple emisor patterns
            emisor_patterns = re.findall(r'([A-Z][A-Za-z\\s]+(?:S\\.A\\.|SA|LTDA|Corp))', page_content)
            for i, emisor in enumerate(set(emisor_patterns[:5])):  # Limit to 5 for testing
                structured_data["Emisores"].append({
                    "id_emisor": i + 1,
                    "nombre_emisor": emisor.strip(),
                    "id_categoria_emisor": 1,
                    "calificacion_bva": "N/A"
                })
            
            # Extract report information
            for i, doc_url in enumerate(documents[:3]):  # Limit to 3 for testing
                title = doc_url.split('/')[-1].replace('.pdf', '').replace('.xlsx', '').replace('_', ' ').replace('-', ' ').title()
                structured_data["Informe_General"].append({
                    "id_informe": i + 1,
                    "id_emisor": 1,
                    "id_tipo_informe": 1,
                    "titulo_informe": title,
                    "fecha_publicacion": datetime.now().strftime("%Y-%m-%d"),
                    "url_descarga_original": doc_url,
                    "resumen_informe": f"Report extracted from BVA: {title[:100]}...",
                    "id_periodo": 1,
                    "contenido_raw": ""
                })
        
        processing_report = {
            "status": "success",
            "records_extracted": sum(len(records) for records in structured_data.values()),
            "tables_populated": sum(1 for records in structured_data.values() if len(records) > 0),
            "source_url": source_url
        }
        
        return {
            "structured_data": structured_data,
            "processing_report": processing_report
        }
        
    except Exception as e:
        return {
            "structured_data": {table: [] for table in ["Categoria_Emisor", "Emisores", "Moneda", "Frecuencia", "Tipo_Informe", "Periodo_Informe", "Unidad_Medida", "Instrumento", "Informe_General", "Resumen_Informe_Financiero", "Dato_Macroeconomico", "Movimiento_Diario_Bolsa", "Licitacion_Contrato"]},
            "processing_report": {
                "status": "error",
                "error": str(e),
                "records_extracted": 0
            }
        }

@tool("Normalize Data Tool")
def normalize_data(structured_data: dict) -> dict:
    """Clean and normalize structured data"""
    try:
        normalized_data = {}
        
        for table_name, records in structured_data.items():
            normalized_records = []
            
            for record in records:
                normalized_record = {}
                
                for field, value in record.items():
                    if isinstance(value, str):
                        # Clean string data
                        cleaned_value = re.sub(r'[^\\w\\s\\-\\.]', '', value).strip()
                        normalized_record[field] = cleaned_value
                    else:
                        normalized_record[field] = value
                
                normalized_records.append(normalized_record)
            
            normalized_data[table_name] = normalized_records
        
        return {
            "normalized_data": normalized_data,
            "normalization_report": {
                "status": "success",
                "tables_processed": len(normalized_data),
                "total_records": sum(len(records) for records in normalized_data.values())
            }
        }
        
    except Exception as e:
        return {
            "normalized_data": structured_data,
            "normalization_report": {
                "status": "error",
                "error": str(e)
            }
        }

@tool("Validate Data Tool")
def validate_data(normalized_data: dict) -> dict:
    """Validate data against schema requirements"""
    try:
        validation_report = {
            "valid_data": {},
            "invalid_data": {},
            "validation_errors": [],
            "status": "success"
        }
        
        for table_name, records in normalized_data.items():
            valid_records = []
            invalid_records = []
            
            for record in records:
                is_valid = True
                
                # Basic validation - check for required fields
                if table_name == "Emisores":
                    if not record.get("nombre_emisor"):
                        is_valid = False
                elif table_name == "Informe_General":
                    if not record.get("titulo_informe"):
                        is_valid = False
                
                if is_valid:
                    valid_records.append(record)
                else:
                    invalid_records.append(record)
            
            validation_report["valid_data"][table_name] = valid_records
            validation_report["invalid_data"][table_name] = invalid_records
        
        return validation_report
        
    except Exception as e:
        return {
            "valid_data": normalized_data,
            "invalid_data": {},
            "validation_errors": [str(e)],
            "status": "error"
        }

@tool("Chunk Document Tool")
def chunk_document(text_content: str) -> dict:
    """Chunk document text for vector processing"""
    try:
        # Simple chunking - split by sentences/paragraphs
        chunks = []
        sentences = text_content.split('.')
        
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            if len(current_chunk + sentence) > 1200:  # Max chunk size
                if current_chunk:
                    chunks.append({
                        "chunk_id": chunk_id,
                        "text": current_chunk.strip(),
                        "char_count": len(current_chunk),
                        "position": chunk_id
                    })
                    chunk_id += 1
                    current_chunk = sentence
                else:
                    current_chunk += sentence
            else:
                current_chunk += sentence + "."
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "chunk_id": chunk_id,
                "text": current_chunk.strip(),
                "char_count": len(current_chunk),
                "position": chunk_id
            })
        
        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "chunking_report": {
                "status": "success",
                "original_length": len(text_content),
                "chunks_created": len(chunks)
            }
        }
        
    except Exception as e:
        return {
            "chunks": [],
            "total_chunks": 0,
            "chunking_report": {
                "status": "error",
                "error": str(e)
            }
        }

# ===================================================================
# SECTION 3: TEST CREW CLASS (Simplified version)
# ===================================================================

class TestInverbotPipelineDato:
    """Fixed test crew with standalone tools"""
    
    def __init__(self):
        # Set model configuration with Gemini-1.5-flash for stability
        self.model_llm = os.getenv('MODEL', 'gemini/gemini-1.5-flash')
        self.model_embedder = os.getenv('EMBEDDER', 'models/embedding-001')
        self.test_mode = True
        
        # Load test configurations
        self.agents_config = self._load_test_config('agent_config.yaml')
        self.tasks_config = self._load_test_config('task_config.yaml')
    
    def _load_test_config(self, filename: str) -> dict:
        """Load test configuration files"""
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), 'test_config', filename)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                # Return default config if file doesn't exist
                return self._get_default_config(filename)
        except Exception as e:
            print(f"Warning: Could not load {filename}, using defaults: {e}")
            return self._get_default_config(filename)
    
    def _get_default_config(self, filename: str) -> dict:
        """Get default configurations for test environment"""
        if 'agent' in filename:
            return {
                'extractor': {
                    'role': 'Test Data Extraction Specialist',
                    'goal': 'Extract raw content from 2 key sources for testing',
                    'backstory': 'Specialized in rapid content extraction for pipeline testing'
                },
                'processor': {
                    'role': 'Test Data Processing Expert', 
                    'goal': 'Process extracted content into structured format',
                    'backstory': 'Expert in document processing and data structuring'
                },
                'vector': {
                    'role': 'Test Vector Processing Specialist',
                    'goal': 'Create embeddings and metadata from processed content',
                    'backstory': 'Specialist in vector database operations and embeddings'
                }
            }
        else:  # task config
            return {
                'extract_task': {
                    'description': 'Extract content from BVA Daily and Monthly sources',
                    'expected_output': 'Raw content with links and documents'
                },
                'process_task': {
                    'description': 'Extract PDFs/Excel and structure data into database format',
                    'expected_output': 'Structured data ready for loading'
                },
                'vectorize_task': {
                    'description': 'Create vector embeddings from structured content',
                    'expected_output': 'Vector data with metadata relationships'
                }
            }

    # ===================================================================
    # SECTION 4: AGENT DEFINITIONS (using standalone tools)
    # ===================================================================

    def extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['extractor'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                scrape_bva_daily,
                scrape_bva_monthly
            ]
        )

    def processor(self) -> Agent:
        return Agent(
            config=self.agents_config['processor'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                extract_text_from_pdf,
                extract_text_from_excel,
                extract_structured_data_from_raw,
                normalize_data,
                validate_data
            ]
        )

    def vector(self) -> Agent:
        return Agent(
            config=self.agents_config['vector'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                chunk_document
            ]
        )

    # ===================================================================
    # SECTION 5: TASK DEFINITIONS
    # ===================================================================

    def extract_task(self) -> Task:
        return Task(
            config=self.tasks_config['extract_task'],
            agent=self.extractor(),
            output_file='test_pipeline/test_results/raw_extraction_output.txt'
        )

    def process_task(self) -> Task:
        return Task(
            config=self.tasks_config['process_task'],
            agent=self.processor(),
            context=[self.extract_task()],
            output_file='test_pipeline/test_results/structured_data_output.txt'
        )

    def vectorize_task(self) -> Task:
        return Task(
            config=self.tasks_config['vectorize_task'],
            agent=self.vector(),
            context=[self.process_task()],
            output_file='test_pipeline/test_results/vector_data_output.txt'
        )

    # ===================================================================
    # SECTION 6: CREW DEFINITION
    # ===================================================================

    def crew(self) -> Crew:
        """Creates the test crew"""
        return Crew(
            agents=[self.extractor(), self.processor(), self.vector()],
            tasks=[self.extract_task(), self.process_task(), self.vectorize_task()],
            process=Process.sequential,
            verbose=True
        )

    def run_test_pipeline(self):
        """Run the complete test pipeline"""
        print("Starting Test Pipeline...")
        print(f"Model: {self.model_llm}")
        print(f"Test Mode: {self.test_mode}")
        
        # Ensure output directory exists
        os.makedirs("test_pipeline/test_results", exist_ok=True)
        
        try:
            # Execute the crew
            result = self.crew().kickoff()
            
            print("Test Pipeline completed successfully!")
            print(f"Result: {result}")
            
            return result
            
        except Exception as e:
            print(f"Test Pipeline failed: {e}")
            raise e


# ===================================================================
# SECTION 7: MAIN EXECUTION
# ===================================================================

if __name__ == "__main__":
    test_crew = TestInverbotPipelineDato()
    test_crew.run_test_pipeline()