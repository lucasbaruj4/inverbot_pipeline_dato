#!/usr/bin/env python3
"""
Direct test of the processor agent with existing extraction data.
"""
import sys
import os
import warnings
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def test_processor():
    """Test the processor agent directly with existing extraction data."""
    
    # Load environment variables
    if os.path.exists(".env.local"):
        load_dotenv(".env.local")
        print("✅ Loaded environment variables from .env.local")
    elif os.path.exists(".env"):
        load_dotenv(".env")
        print("✅ Loaded environment variables from .env")
    else:
        print("❌ No environment file found!")
        return
    
    print("=" * 60)
    print("TESTING PROCESSOR AGENT WITH EXISTING EXTRACTION DATA")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if extraction file exists
    extraction_file = "output/try_1/raw_extraction_output.txt"
    if not os.path.exists(extraction_file):
        print(f"❌ Extraction file not found: {extraction_file}")
        return
    
    print(f"✅ Found extraction file: {extraction_file}")
    
    # Create crew instance
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    
    # Get processor agent and task using CrewBase decorators
    processor_agent = crew_instance.processor()
    process_task = crew_instance.process_task()
    
    if not processor_agent:
        print("❌ Processor agent not found!")
        return
    
    if not process_task:
        print("❌ Process task not found!")
        return
    
    print(f"✅ Found processor agent: {processor_agent.role}")
    print(f"✅ Found process task")
    
    # Execute processor task directly
    print("\n" + "=" * 60)
    print("EXECUTING PROCESSOR TASK")
    print("=" * 60)
    
    try:
        # Execute task with processor agent
        result = process_task.execute_sync(
            agent=processor_agent,
            context="Raw extraction data is available in output/try_1/raw_extraction_output.txt",
            tools=processor_agent.tools
        )
        
        print("\n✅ PROCESSOR TASK COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("RESULT:")
        print(str(result)[:2000] + ("..." if len(str(result)) > 2000 else ""))
        
        # Check output files
        structured_file = "output/try_1/structured_data_output.txt"
        if os.path.exists(structured_file):
            print(f"\n✅ Structured data file created: {structured_file}")
            
            # Get file size
            file_size = os.path.getsize(structured_file)
            print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print(f"\n⚠️ Structured data file not found: {structured_file}")
        
    except Exception as e:
        print(f"\n❌ PROCESSOR TASK FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_processor()