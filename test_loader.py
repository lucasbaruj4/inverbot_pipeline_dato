#!/usr/bin/env python3
"""
Direct test of the loader agent with existing structured and vector data.
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

def test_loader():
    """Test the loader agent directly with existing structured and vector data."""
    
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
    print("TESTING LOADER AGENT WITH EXISTING DATA FILES")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if required files exist
    structured_file = "output/try_1/structured_data_output.txt"
    vector_file = "output/try_1/vector_data_output.txt"
    
    if not os.path.exists(structured_file):
        print(f"❌ Structured data file not found: {structured_file}")
        return
    
    if not os.path.exists(vector_file):
        print(f"❌ Vector data file not found: {vector_file}")
        return
    
    print(f"✅ Found structured data file: {structured_file}")
    print(f"✅ Found vector data file: {vector_file}")
    
    # Create crew instance
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    
    # Get loader agent and task
    loader_agent = crew_instance.loader()
    load_task = crew_instance.load_task()
    
    if not loader_agent:
        print("❌ Loader agent not found!")
        return
    
    if not load_task:
        print("❌ Load task not found!")
        return
    
    print(f"✅ Found loader agent: {loader_agent.role}")
    print(f"✅ Found load task")
    
    # Execute loader task directly
    print("\n" + "=" * 60)
    print("EXECUTING LOADER TASK")
    print("=" * 60)
    
    try:
        # Execute task with loader agent
        result = load_task.execute_sync(
            agent=loader_agent,
            context="Structured data is in output/try_1/structured_data_output.txt and vector data is in output/try_1/vector_data_output.txt from previous agents",
            tools=loader_agent.tools
        )
        
        print("\n✅ LOADER TASK COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("RESULT:")
        print(str(result)[:2000] + ("..." if len(str(result)) > 2000 else ""))
        
        # Check output files
        loading_file = "output/try_1/loading_results_output.txt"
        if os.path.exists(loading_file):
            print(f"\n✅ Loading results file created: {loading_file}")
            
            # Get file size
            file_size = os.path.getsize(loading_file)
            print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print(f"\n⚠️ Loading results file not found: {loading_file}")
        
    except Exception as e:
        print(f"\n❌ LOADER TASK FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_loader()