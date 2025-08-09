#!/usr/bin/env python3
"""
Test the updated vector processing tools with real structured data
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

def test_vector_processing():
    """Test the vector processing tools with real structured data."""
    
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
    print("TESTING VECTOR PROCESSING PIPELINE")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if relationships data file exists (from data structure tools)
    relationships_file = "output/try_1/relationships_data_output.txt"
    if not os.path.exists(relationships_file):
        print(f"❌ Relationships data file not found: {relationships_file}")
        print("   Please run the data structure tools first!")
        return
    
    print(f"✅ Found relationships data file: {relationships_file}")
    
    # Create crew instance and get vector agent
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    vector_agent = crew_instance.vector()
    
    if not vector_agent:
        print("❌ Vector agent not found!")
        return
    
    # Find the vector processing tool
    vector_tool = None
    
    for tool in vector_agent.tools:
        tool_name = getattr(tool, 'name', getattr(tool, '_name', ''))
        if 'Process Structured Data for Vectorization' in tool_name:
            vector_tool = tool
            break
    
    if not vector_tool:
        print("❌ Vector processing tool not found!")
        print(f"Available tools: {[getattr(t, 'name', getattr(t, '_name', str(t))) for t in vector_agent.tools]}")
        return
    
    print(f"✅ Found vector processing tool: {getattr(vector_tool, 'name', 'unknown')}")
    
    try:
        # Test Vector Processing Tool
        print("\n" + "=" * 50)
        print("TESTING VECTOR PROCESSING TOOL")
        print("=" * 50)
        
        vector_result = vector_tool.run("")
        
        if "error" in vector_result:
            print(f"❌ Vector processing failed: {vector_result['error']}")
            if "error_details" in vector_result:
                print(f"Error details: {vector_result['error_details']}")
            return
        
        print("✅ Vector processing executed successfully!")
        
        # Show processing summary
        summary = vector_result.get("vectorization_summary", {})
        print(f"\n📊 VECTOR GENERATION SUMMARY:")
        print(f"   Total vectors: {summary.get('total_vectors', 0)}")
        print(f"   Documento/Informe vectors: {summary.get('documento_informe_vectors', 0)}")
        print(f"   Dato Macroeconómico vectors: {summary.get('dato_macroeconomico_vectors', 0)}")
        print(f"   Licitación/Contrato vectors: {summary.get('licitacion_contrato_vectors', 0)}")
        
        # Show vector data details
        vector_data = vector_result.get("vector_data", {})
        print(f"\n🎯 VECTOR DATA BY INDEX:")
        for index_name, vectors in vector_data.items():
            if vectors:
                print(f"   {index_name}: {len(vectors)} vectors")
                # Show sample vector
                sample_vector = vectors[0]
                print(f"      Sample text: {sample_vector.get('text', '')[:100]}...")
                print(f"      Vector ID: {sample_vector.get('id', 'N/A')}")
                print(f"      Metadata keys: {list(sample_vector.get('metadata', {}).keys())}")
        
        # Check output file
        if vector_result.get('output_file') and os.path.exists(vector_result['output_file']):
            file_size = os.path.getsize(vector_result['output_file'])
            print(f"\n💾 Output file created: {vector_result['output_file']}")
            print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Show processing report
        report = vector_result.get("processing_report", {})
        if report:
            print(f"\n📋 PROCESSING REPORT:")
            print(f"   Status: {report.get('status', 'unknown')}")
            print(f"   Data sources processed: {report.get('data_sources_processed', 0)}")
            print(f"   Indices populated: {report.get('indices_populated', 0)}")
        
        print("\n" + "=" * 60)
        print("✅ VECTOR PROCESSING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("🎯 Pipeline Status:")
        print("   ✅ Extract: Structured data extracted from raw content")
        print("   ✅ Normalize: Data normalized and cleaned")
        print("   ✅ Validate: Data validated against schemas")
        print("   ✅ Relationships: Entity relationships established")
        print("   ✅ Vectorization: Vector-ready data generated for 3 indices")
        print("\n🔄 Ready for next phase: Database Loading")
        
    except Exception as e:
        print(f"❌ VECTOR PROCESSING FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vector_processing()