#!/usr/bin/env python3
"""
Direct Document Processor - Bypasses CrewAI for complete document processing
This script processes all PDFs and Excel files found in raw_extraction_output.txt
"""

import json
import os
import sys
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Try to import required libraries
try:
    import fitz  # PyMuPDF for PDF processing
except ImportError:
    print("Warning: PyMuPDF not installed. PDF processing will be limited.")
    fitz = None

try:
    import openpyxl  # For Excel processing
except ImportError:
    print("Warning: openpyxl not installed. Excel processing will be limited.")
    openpyxl = None


class DirectDocumentProcessor:
    """Process documents directly without CrewAI orchestration"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join("output", "try_1")
        self.output_dir = output_dir
        self.raw_file = os.path.join(output_dir, "raw_extraction_output.txt")
        self.structured_file = os.path.join(output_dir, "structured_data_output.txt")
        self.checkpoint_file = os.path.join(output_dir, "processing_checkpoint.json")
        self.processed_documents = self.load_checkpoint()
        self.stats = {
            "pdfs_processed": 0,
            "excels_processed": 0,
            "pdfs_failed": 0,
            "excels_failed": 0,
            "total_text_extracted": 0,
            "start_time": time.time()
        }
    
    def load_checkpoint(self) -> Dict:
        """Load processing checkpoint to resume from interruption"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"processed_pdfs": [], "processed_excels": []}
        return {"processed_pdfs": [], "processed_excels": []}
    
    def save_checkpoint(self):
        """Save current processing state"""
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_documents, f, indent=2)
    
    def extract_pdf_text(self, pdf_url: str) -> Optional[str]:
        """Extract text from a single PDF"""
        if not fitz:
            print(f"[Skip] PyMuPDF not available for: {pdf_url}")
            return None
        
        if pdf_url in self.processed_documents["processed_pdfs"]:
            print(f"[Skip] Already processed: {pdf_url}")
            return None
        
        print(f"[Processing PDF] {pdf_url}")
        
        try:
            # Download PDF
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Extract text with PyMuPDF
            pdf = fitz.open(stream=response.content, filetype="pdf")
            text_parts = []
            
            # Process up to 50 pages (configurable)
            max_pages = min(pdf.page_count, 50)
            for page_num in range(max_pages):
                try:
                    page = pdf.load_page(page_num)
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                except Exception as e:
                    print(f"  Warning: Failed to extract page {page_num + 1}: {e}")
            
            pdf.close()
            
            if text_parts:
                full_text = "\n\n".join(text_parts)
                self.stats["pdfs_processed"] += 1
                self.processed_documents["processed_pdfs"].append(pdf_url)
                self.save_checkpoint()
                print(f"  ✓ Extracted {len(full_text)} characters from {max_pages} pages")
                return full_text
            else:
                print(f"  × No text extracted")
                self.stats["pdfs_failed"] += 1
                
        except requests.RequestException as e:
            print(f"  × Download failed: {e}")
            self.stats["pdfs_failed"] += 1
        except Exception as e:
            print(f"  × Processing failed: {e}")
            self.stats["pdfs_failed"] += 1
        
        return None
    
    def extract_excel_text(self, excel_url: str) -> Optional[str]:
        """Extract text from a single Excel file"""
        if not openpyxl:
            print(f"[Skip] openpyxl not available for: {excel_url}")
            return None
        
        if excel_url in self.processed_documents["processed_excels"]:
            print(f"[Skip] Already processed: {excel_url}")
            return None
        
        print(f"[Processing Excel] {excel_url}")
        
        try:
            # Download Excel
            response = requests.get(excel_url, timeout=30)
            response.raise_for_status()
            
            # Load with openpyxl
            from io import BytesIO
            workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=True)
            
            text_parts = []
            
            # Process all sheets (up to 10)
            for sheet_idx, sheet in enumerate(workbook.worksheets[:10]):
                sheet_text = []
                sheet_text.append(f"=== Sheet: {sheet.title} ===")
                
                # Process rows (up to 1000)
                for row_idx, row in enumerate(sheet.iter_rows(max_row=1000)):
                    row_data = []
                    for cell in row:
                        if cell.value is not None:
                            row_data.append(str(cell.value))
                    
                    if row_data:
                        sheet_text.append(" | ".join(row_data))
                
                if len(sheet_text) > 1:  # Has more than just the title
                    text_parts.append("\n".join(sheet_text))
            
            workbook.close()
            
            if text_parts:
                full_text = "\n\n".join(text_parts)
                self.stats["excels_processed"] += 1
                self.processed_documents["processed_excels"].append(excel_url)
                self.save_checkpoint()
                print(f"  ✓ Extracted {len(full_text)} characters from {len(text_parts)} sheets")
                return full_text
            else:
                print(f"  × No data extracted")
                self.stats["excels_failed"] += 1
                
        except requests.RequestException as e:
            print(f"  × Download failed: {e}")
            self.stats["excels_failed"] += 1
        except Exception as e:
            print(f"  × Processing failed: {e}")
            self.stats["excels_failed"] += 1
        
        return None
    
    def get_document_urls(self) -> Tuple[List[str], List[str]]:
        """Extract all PDF and Excel URLs from raw extraction output"""
        pdf_urls = []
        excel_urls = []
        
        if not os.path.exists(self.raw_file):
            print(f"Error: {self.raw_file} not found!")
            return pdf_urls, excel_urls
        
        try:
            with open(self.raw_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Handle both JSON and raw text formats
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                if content.endswith('```'):
                    content = content[:-3]  # Remove ```
                
                raw_data = json.loads(content)
            
            # Traverse all sources to find documents
            for source_category in ['bva_sources', 'government_sources', 'contracts_investment_sources']:
                if source_category in raw_data:
                    for source_name, source_data in raw_data[source_category].items():
                        if isinstance(source_data, dict):
                            # Get documents array
                            documents = source_data.get('documents', [])
                            for doc_url in documents:
                                if doc_url.lower().endswith('.pdf'):
                                    pdf_urls.append(doc_url)
                                elif doc_url.lower().endswith(('.xlsx', '.xls')):
                                    excel_urls.append(doc_url)
                            
                            # Also check links for document URLs
                            links = source_data.get('links', [])
                            for link in links:
                                if link.lower().endswith('.pdf'):
                                    pdf_urls.append(link)
                                elif link.lower().endswith(('.xlsx', '.xls')):
                                    excel_urls.append(link)
            
            print(f"Found {len(pdf_urls)} PDFs and {len(excel_urls)} Excel files to process")
            return pdf_urls, excel_urls
            
        except Exception as e:
            print(f"Error reading raw extraction file: {e}")
            return pdf_urls, excel_urls
    
    def structure_document_data(self, text: str, source_url: str, doc_type: str) -> Dict:
        """Create structured data from extracted text"""
        # Basic structuring - in production this would use NLP/LLM
        structured = {
            "source_url": source_url,
            "document_type": doc_type,
            "extracted_at": datetime.now().isoformat(),
            "content_length": len(text),
            "preview": text[:500] if text else "",
            
            # Placeholder for structured tables
            "structured_data": {
                "Informe_General": [{
                    "titulo_informe": f"Document from {source_url.split('/')[-1]}",
                    "fecha_publicacion": datetime.now().isoformat()[:10],
                    "url_descarga_original": source_url,
                    "contenido_extracto": text[:1000] if text else ""
                }]
            }
        }
        
        return structured
    
    def append_to_structured_output(self, structured_data: Dict):
        """Append structured data to output file"""
        # Load existing structured data
        existing_data = {
            "structured_data": {},
            "metadata": {
                "documents_processed": [],
                "last_updated": datetime.now().isoformat()
            }
        }
        
        if os.path.exists(self.structured_file):
            try:
                with open(self.structured_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        # Merge new data
        for table_name, records in structured_data.get("structured_data", {}).items():
            if table_name not in existing_data["structured_data"]:
                existing_data["structured_data"][table_name] = []
            existing_data["structured_data"][table_name].extend(records)
        
        # Update metadata
        existing_data["metadata"]["documents_processed"].append({
            "url": structured_data["source_url"],
            "type": structured_data["document_type"],
            "processed_at": structured_data["extracted_at"],
            "content_length": structured_data["content_length"]
        })
        existing_data["metadata"]["last_updated"] = datetime.now().isoformat()
        existing_data["metadata"]["total_documents"] = len(existing_data["metadata"]["documents_processed"])
        
        # Save updated data
        with open(self.structured_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    def process_all_documents(self):
        """Main processing function"""
        print("\n" + "="*60)
        print("DIRECT DOCUMENT PROCESSOR")
        print("="*60)
        
        # Get all document URLs
        pdf_urls, excel_urls = self.get_document_urls()
        
        if not pdf_urls and not excel_urls:
            print("No documents found to process!")
            return
        
        print(f"\nProcessing Plan:")
        print(f"  - PDFs to process: {len(pdf_urls)}")
        print(f"  - Excel files to process: {len(excel_urls)}")
        print(f"  - Already processed: {len(self.processed_documents['processed_pdfs'])} PDFs, "
              f"{len(self.processed_documents['processed_excels'])} Excel files")
        
        # Process PDFs
        if pdf_urls:
            print(f"\n{'='*40}")
            print("Processing PDFs...")
            print('='*40)
            
            for pdf_url in pdf_urls:
                text = self.extract_pdf_text(pdf_url)
                if text:
                    self.stats["total_text_extracted"] += len(text)
                    structured = self.structure_document_data(text, pdf_url, "pdf")
                    self.append_to_structured_output(structured)
                    
                    # Small delay to avoid overwhelming servers
                    time.sleep(1)
        
        # Process Excel files
        if excel_urls:
            print(f"\n{'='*40}")
            print("Processing Excel Files...")
            print('='*40)
            
            for excel_url in excel_urls:
                text = self.extract_excel_text(excel_url)
                if text:
                    self.stats["total_text_extracted"] += len(text)
                    structured = self.structure_document_data(text, excel_url, "excel")
                    self.append_to_structured_output(structured)
                    
                    # Small delay to avoid overwhelming servers
                    time.sleep(1)
        
        # Print final statistics
        elapsed_time = time.time() - self.stats["start_time"]
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print('='*60)
        print(f"Time elapsed: {elapsed_time:.1f} seconds")
        print(f"PDFs processed: {self.stats['pdfs_processed']} successful, {self.stats['pdfs_failed']} failed")
        print(f"Excel files processed: {self.stats['excels_processed']} successful, {self.stats['excels_failed']} failed")
        print(f"Total text extracted: {self.stats['total_text_extracted']:,} characters")
        print(f"Output saved to: {self.structured_file}")
        
        # Remove checkpoint file on successful completion
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            print("Checkpoint file removed (processing complete)")


def main():
    """Main entry point"""
    processor = DirectDocumentProcessor()
    
    try:
        processor.process_all_documents()
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted! Progress saved to checkpoint.")
        print("Run again to resume from where you left off.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()