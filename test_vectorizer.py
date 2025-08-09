#!/usr/bin/env python3
"""
Direct test of the vectorizer agent with mock structured data.
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

def create_mock_structured_data():
    """Create mock structured data for testing vectorization."""
    mock_data = """File write confirmation with processing summary. The structured data has been written to output/try_1/structured_data_output.txt.
Processing Summary:
{
  "file_write_status": {
    "status": "success",
    "file_path": "output/try_1/structured_data_output.txt",
    "total_records_written": 15,
    "tables_written": ["Categoria_Emisor", "Emisores", "Informe_General"],
    "file_size_kb": 2.5
  },
  "processing_summary": {
    "tables_populated": ["Categoria_Emisor", "Emisores", "Informe_General"],
    "total_records_processed": 15,
    "documents_extracted": 4,
    "relationships_created": 8,
    "duplicates_filtered": 2,
    "validation_errors": 0,
    "data_quality_score": 0.95
  },
  "key_statistics": {
    "emisores_created": 5,
    "informes_processed": 3,
    "macroeconomic_data_points": 4,
    "contracts_identified": 2,
    "daily_movements": 1
  }
}"""
    
    # Write mock structured data
    os.makedirs("output/try_1", exist_ok=True)
    with open("output/try_1/structured_data_output.txt", "w", encoding="utf-8") as f:
        f.write(mock_data)
    
    print("✅ Created mock structured data file")

def test_vectorizer():
    """Test the vectorizer agent directly with mock structured data."""
    
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
    print("TESTING VECTORIZER AGENT WITH MOCK STRUCTURED DATA")
    print("=" * 60)
    
    # Create mock data
    create_mock_structured_data()
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Create crew instance
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    
    # Get vectorizer agent and task
    vectorizer_agent = crew_instance.vector()
    vectorize_task = crew_instance.vectorize_task()
    
    if not vectorizer_agent:
        print("❌ Vectorizer agent not found!")
        return
    
    if not vectorize_task:
        print("❌ Vectorize task not found!")
        return
    
    print(f"✅ Found vectorizer agent: {vectorizer_agent.role}")
    print(f"✅ Found vectorize task")
    
    # Execute vectorizer task directly
    print("\n" + "=" * 60)
    print("EXECUTING VECTORIZER TASK")
    print("=" * 60)
    
    try:
        # Execute task with vectorizer agent
        result = vectorize_task.execute_sync(
            agent=vectorizer_agent,
            context="Structured data is available in output/try_1/structured_data_output.txt from the processor agent",
            tools=vectorizer_agent.tools
        )
        
        print("\n✅ VECTORIZER TASK COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("RESULT:")
        print(str(result)[:2000] + ("..." if len(str(result)) > 2000 else ""))
        
        # Check output files
        vector_file = "output/try_1/vector_data_output.txt"
        if os.path.exists(vector_file):
            print(f"\n✅ Vector data file created: {vector_file}")
            
            # Get file size
            file_size = os.path.getsize(vector_file)
            print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        else:
            print(f"\n⚠️ Vector data file not found: {vector_file}")
        
    except Exception as e:
        print(f"\n❌ VECTORIZER TASK FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vectorizer()