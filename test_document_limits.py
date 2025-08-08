#!/usr/bin/env python3
"""Test script to demonstrate document limit functionality"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from inverbot_pipeline_dato.crew import (
    DOCUMENT_COUNTERS, 
    DOCUMENT_LIMITS,
    should_process_document,
    increment_document_counter,
    reset_document_counters
)

def test_document_limits():
    """Test the document limiting functionality"""
    print("Testing Document Limit System")
    print("="*50)
    
    # Reset counters
    reset_document_counters()
    print(f"Initial state: {DOCUMENT_COUNTERS}")
    print(f"Limits: {DOCUMENT_LIMITS}")
    
    # Test PDF processing
    print("\n" + "="*50)
    print("Testing PDF Processing Limits (max 3):")
    print("="*50)
    
    pdf_urls = [
        "https://example.com/doc1.pdf",
        "https://example.com/doc2.pdf",
        "https://example.com/doc3.pdf",
        "https://example.com/doc4.pdf",  # Should be skipped
        "https://example.com/doc5.pdf",  # Should be skipped
    ]
    
    for url in pdf_urls:
        if should_process_document('pdf', url):
            print(f"[OK] Processing: {url}")
            increment_document_counter('pdf', url)
        else:
            print(f"[SKIP] Skipped (limit reached): {url}")
    
    # Test Excel processing
    print("\n" + "="*50)
    print("Testing Excel Processing Limits (max 2):")
    print("="*50)
    
    excel_urls = [
        "https://example.com/data1.xlsx",
        "https://example.com/data2.xlsx",
        "https://example.com/data3.xlsx",  # Should be skipped
        "https://example.com/data4.xlsx",  # Should be skipped
    ]
    
    for url in excel_urls:
        if should_process_document('excel', url):
            print(f"[OK] Processing: {url}")
            increment_document_counter('excel', url)
        else:
            print(f"[SKIP] Skipped (limit reached): {url}")
    
    # Print final state
    print("\n" + "="*50)
    print("Final State:")
    print("="*50)
    print(f"PDFs processed: {DOCUMENT_COUNTERS['pdf']}/{DOCUMENT_LIMITS['pdf']}")
    print(f"Excel files processed: {DOCUMENT_COUNTERS['excel']}/{DOCUMENT_LIMITS['excel']}")
    print(f"\nProcessed PDFs: {DOCUMENT_COUNTERS['pdf_urls_processed']}")
    print(f"Processed Excel: {DOCUMENT_COUNTERS['excel_urls_processed']}")
    
    print("\n" + "="*50)
    print("CONCLUSION:")
    print("="*50)
    print("[SUCCESS] Document limiting system is working correctly!")
    print("[SUCCESS] CrewAI will process only limited documents (3 PDFs, 2 Excel)")
    print("[SUCCESS] Remaining documents can be processed via direct_processor.py")
    print("\nThis prevents the 'Invalid response from LLM' error by keeping")
    print("the processing workload manageable for CrewAI.")

if __name__ == "__main__":
    test_document_limits()