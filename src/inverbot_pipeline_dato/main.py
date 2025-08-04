#!/usr/bin/env python
import sys
import warnings
import os
from datetime import datetime

from inverbot_pipeline_dato.crew import InverbotPipelineDato

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the InverBot ETL Pipeline with comprehensive tracking and test mode support.
    """
    print("=" * 60)
    print("INVERBOT ETL PIPELINE - Starting Execution")
    print("=" * 60)
    
    try:
        # Initialize the crew
        crew_instance = InverbotPipelineDato()
        
        # Display configuration
        print(f"Test Mode: {'ENABLED' if crew_instance.test_mode else 'DISABLED'}")
        print(f"LLM Model: {crew_instance.model_llm}")
        print(f"Embedder: {crew_instance.model_embedder}")
        
        if crew_instance.test_mode:
            print("\n" + " TEST MODE ACTIVE ".center(60, "-"))
            print("Output will be saved to markdown files in:")
            print("   - output/test_results/ (performance reports)")
            print("   - output/try_1/ (task outputs)")
            print("No data will be pushed to Supabase or Pinecone")
            print("-" * 60)
        else:
            print("\n" + " PRODUCTION MODE ACTIVE ".center(60, "-"))
            print("Data will be loaded to:")
            print("   - Supabase (structured data)")
            print("   - Pinecone (vector embeddings)")
            print("WARNING: Make sure all API keys are configured!")
            print("-" * 60)
        
        print("\nStarting pipeline execution...\n")
        
        # Run the crew with tracking
        result = crew_instance.kickoff_with_tracking()
        
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION COMPLETED")
        print("=" * 60)
        
        if crew_instance.test_mode:
            print("\nNEXT STEPS (Test Mode):")
            print("1. Check performance report in output/test_results/")
            print("2. Review all output files for data quality")
            print("3. Verify component functionality")
            print("4. Set test_mode = False for production run")
        else:
            print("\nNEXT STEPS (Production Mode):")
            print("1. Check performance report for any errors")
            print("2. Verify data in Supabase tables")
            print("3. Confirm vector embeddings in Pinecone")
            print("4. Run data integrity checks")
        
        print(f"\nPerformance reports saved to: output/test_results/")
        print("=" * 60)
        
        return result
        
    except KeyboardInterrupt:
        print("\n\nWARNING: Pipeline execution interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\nERROR: Pipeline execution failed: {str(e)}")
        print("Check the performance report for detailed error information")
        raise Exception(f"An error occurred while running the crew: {e}")


def configure_test_mode(enabled: bool = True):
    """
    Helper function to easily configure test mode.
    
    Args:
        enabled: True to enable test mode, False for production mode
    """
    print(f"Configuring test mode: {'ENABLED' if enabled else 'DISABLED'}")
    
    # This would need to be implemented to modify the crew.py file
    # For now, users need to manually change test_mode in crew.py
    print("To change test mode, modify 'test_mode' variable in crew.py")
    print(f"   Set: test_mode = {enabled}")


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--production":
            print("WARNING: Production mode requested!")
            print("Make sure to set test_mode = False in crew.py")
        elif sys.argv[1] == "--test":
            print("Test mode requested!")
            print("Make sure to set test_mode = True in crew.py")
        elif sys.argv[1] == "--help":
            print("InverBot ETL Pipeline Usage:")
            print("  python main.py          # Run with current settings")
            print("  python main.py --test   # Reminder to enable test mode")
            print("  python main.py --prod   # Reminder to enable production mode")
            print("  python main.py --help   # Show this help")
            sys.exit(0)
    
    run()
