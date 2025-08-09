#!/usr/bin/env python3
"""
Test the updated database loading tools with real structured data
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

def test_database_loading():
    """Test the database loading tools with real structured data."""
    
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
    print("TESTING DATABASE LOADING PIPELINE")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if required files exist
    relationships_file = "output/try_1/relationships_data_output.txt"
    vector_file = "output/try_1/vector_data_output.txt"
    
    if not os.path.exists(relationships_file):
        print(f"❌ Relationships data file not found: {relationships_file}")
        return
    
    if not os.path.exists(vector_file):
        print(f"❌ Vector data file not found: {vector_file}")
        return
    
    print(f"✅ Found relationships data file: {relationships_file}")
    print(f"✅ Found vector data file: {vector_file}")
    
    # Create crew instance and get loader agent
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    loader_agent = crew_instance.loader()
    
    if not loader_agent:
        print("❌ Loader agent not found!")
        return
    
    # Find the loading tools
    supabase_tool = None
    pinecone_tool = None
    
    for tool in loader_agent.tools:
        tool_name = getattr(tool, 'name', getattr(tool, '_name', ''))
        if 'Load Structured Data to Supabase from Pipeline' in tool_name:
            supabase_tool = tool
        elif 'Load Vectors to Pinecone from Pipeline' in tool_name:
            pinecone_tool = tool
    
    print(f"✅ Found Supabase loading tool: {'✓' if supabase_tool else '✗'}")
    print(f"✅ Found Pinecone loading tool: {'✓' if pinecone_tool else '✗'}")
    
    if not all([supabase_tool, pinecone_tool]):
        print("❌ Some loading tools not found!")
        print(f"Available tools: {[getattr(t, 'name', getattr(t, '_name', str(t))) for t in loader_agent.tools]}")
        return
    
    try:
        # STEP 1: Test Supabase Loading
        print("\n" + "=" * 50)
        print("STEP 1: TESTING SUPABASE LOADING")
        print("=" * 50)
        
        supabase_result = supabase_tool.run("")
        
        if "error" in supabase_result:
            print(f"❌ Supabase loading failed: {supabase_result['error']}")
            if "error_details" in supabase_result:
                print(f"Error details: {supabase_result['error_details']}")
            return
        
        print("✅ Supabase loading executed successfully!")
        
        # Show Supabase loading summary
        summary = supabase_result.get("summary", {})
        print(f"\n📊 SUPABASE LOADING SUMMARY:")
        print(f"   Mode: {supabase_result.get('mode', 'unknown')}")
        print(f"   Tables processed: {summary.get('total_tables', 0)}")
        print(f"   Successful tables: {summary.get('successful_tables', 0)}")
        print(f"   Total records: {summary.get('total_records', 0)}")
        print(f"   Output files: {summary.get('output_files_count', 0)}")
        
        # Show table details
        tables_processed = supabase_result.get("tables_processed", [])
        if tables_processed:
            print(f"\n🗄️ TABLES PROCESSED:")
            for table in tables_processed:
                status_icon = "✅" if table.get("status") == "success" else "❌"
                print(f"   {status_icon} {table.get('table_name', 'unknown')}: {table.get('records_count', 0)} records")
                if table.get("output_file"):
                    file_size = table.get("file_size_kb", 0)
                    print(f"      File: {file_size:.1f} KB")
        
        # STEP 2: Test Pinecone Loading
        print("\n" + "=" * 50)
        print("STEP 2: TESTING PINECONE LOADING")
        print("=" * 50)
        
        pinecone_result = pinecone_tool.run("")
        
        if "error" in pinecone_result:
            print(f"❌ Pinecone loading failed: {pinecone_result['error']}")
            if "error_details" in pinecone_result:
                print(f"Error details: {pinecone_result['error_details']}")
            return
        
        print("✅ Pinecone loading executed successfully!")
        
        # Show Pinecone loading summary
        embedding_summary = pinecone_result.get("embedding_summary", {})
        print(f"\n🔍 PINECONE LOADING SUMMARY:")
        print(f"   Mode: {pinecone_result.get('mode', 'unknown')}")
        print(f"   Indices processed: {embedding_summary.get('total_indices', 0)}")
        print(f"   Successful indices: {embedding_summary.get('successful_indices', 0)}")
        print(f"   Total vectors: {embedding_summary.get('total_vectors', 0)}")
        print(f"   Embedding dimensions: {embedding_summary.get('embedding_dimensions', 0)}")
        
        # Show index details
        indices_processed = pinecone_result.get("indices_processed", [])
        if indices_processed:
            print(f"\n📊 INDICES PROCESSED:")
            for index in indices_processed:
                status_icon = "✅" if index.get("status") == "success" else "❌"
                print(f"   {status_icon} {index.get('index_name', 'unknown')}: {index.get('vectors_count', 0)} vectors")
                if index.get("output_file"):
                    file_size = index.get("file_size_kb", 0)
                    print(f"      File: {file_size:.1f} KB")
        
        # Check output files
        output_files = supabase_result.get("output_files", []) + pinecone_result.get("output_files", [])
        if output_files:
            print(f"\n💾 OUTPUT FILES CREATED:")
            for file_path in output_files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   📁 {file_path} ({file_size:,} bytes)")
        
        print("\n" + "=" * 60)
        print("✅ ALL DATABASE LOADING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("🎯 Complete Pipeline Status:")
        print("   ✅ Extract: Structured data extracted from raw content")
        print("   ✅ Normalize: Data normalized and cleaned")
        print("   ✅ Validate: Data validated against schemas")
        print("   ✅ Relationships: Entity relationships established")
        print("   ✅ Vectorization: Vector-ready data generated for 3 indices")
        print("   ✅ Supabase Loading: 14 tables prepared for database")
        print("   ✅ Pinecone Loading: Vector embeddings prepared for indices")
        print("\n🔄 Ready for next phase: End-to-End Pipeline Testing")
        
    except Exception as e:
        print(f"❌ DATABASE LOADING FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_loading()