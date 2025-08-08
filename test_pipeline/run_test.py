#!/usr/bin/env python3
"""
Test runner for the enhanced test pipeline.
Usage: python test_pipeline/run_test.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_crew_fixed import TestInverbotPipelineDato

def main():
    print("="*60)
    print("ENHANCED TEST PIPELINE - DOCUMENT EXTRACTION & STRUCTURING")
    print("="*60)
    print("Testing: BVA Daily + Monthly -> PDF/Excel Extraction -> Structuring -> Vectorization")
    print("Model: gemini-1.5-flash (optimized for testing)")
    print()
    
    try:
        # Initialize test crew
        test_crew = TestInverbotPipelineDato()
        print(f"Model configured: {test_crew.model_llm}")
        print(f"Test mode enabled: {test_crew.test_mode}")
        print()
        
        # Run the test pipeline
        print("Starting test pipeline execution...")
        result = test_crew.run_test_pipeline()
        
        print()
        print("="*60)
        print("TEST PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("Check the following output files:")
        print("- test_pipeline/test_results/raw_extraction_output.txt")
        print("- test_pipeline/test_results/structured_data_output.txt") 
        print("- test_pipeline/test_results/vector_data_output.txt")
        print()
        
    except Exception as e:
        print()
        print("="*60)
        print("TEST PIPELINE FAILED")
        print("="*60)
        print(f"Error: {e}")
        print()
        print("Check the error details above and fix any issues before retrying.")
        sys.exit(1)

if __name__ == "__main__":
    main()