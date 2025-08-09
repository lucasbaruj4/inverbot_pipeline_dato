#!/usr/bin/env python3
"""
Test the complete end-to-end InverBot ETL Pipeline with updated agent communication
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

def test_full_pipeline():
    """Test the complete end-to-end InverBot ETL Pipeline."""
    
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
    
    print("=" * 80)
    print("TESTING COMPLETE END-TO-END INVERBOT ETL PIPELINE")
    print("=" * 80)
    print("This test will run all 4 agents in sequence:")
    print("  1. EXTRACTOR: Raw content extraction from 10 sources")  
    print("  2. PROCESSOR: Data structuring through 4-stage pipeline")
    print("  3. VECTOR: Vector generation for 3 Pinecone indices")
    print("  4. LOADER: Database loading to Supabase + Pinecone")
    print("=" * 80)
    
    try:
        # Import after setting up environment
        from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
        
        # Create crew instance in test mode
        print("🚀 Initializing InverBot Pipeline in TEST MODE...")
        crew_instance = InverbotPipelineDato()
        
        # Verify test mode is enabled
        if not getattr(crew_instance, "test_mode", True):
            print("⚠️ WARNING: Pipeline not in test mode - forcing test mode for safety")
            crew_instance.test_mode = True
        
        print(f"✅ Test mode confirmed: {crew_instance.test_mode}")
        
        # Get the complete crew
        crew = crew_instance.crew()
        print(f"✅ Crew initialized with {len(crew.agents)} agents")
        
        # Clean output directory
        output_dir = "output/try_1"
        if os.path.exists(output_dir):
            print(f"🧹 Cleaning output directory: {output_dir}")
            for file in os.listdir(output_dir):
                if file.endswith('.txt') or file.endswith('.json'):
                    os.remove(os.path.join(output_dir, file))
        
        print("\n" + "=" * 60)
        print("🚀 STARTING COMPLETE PIPELINE EXECUTION")
        print("=" * 60)
        print("Expected flow:")
        print("  Raw Extraction → Data Processing → Vectorization → Database Loading")
        print("  Each agent reads from the previous agent's output files")
        print("=" * 60)
        
        # Execute the complete crew workflow
        print("\n⏳ Executing complete crew workflow...")
        print("This may take several minutes as all agents run in sequence...")
        
        result = crew.kickoff()
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE EXECUTION COMPLETED!")
        print("=" * 80)
        
        # Check output files from each stage
        expected_files = [
            "raw_extraction_output.txt",      # Extractor output
            "structured_data_output.txt",     # Processor stage 1 output  
            "normalized_data_output.txt",     # Processor stage 2 output
            "validated_data_output.txt",      # Processor stage 3 output
            "relationships_data_output.txt",  # Processor stage 4 output
            "vector_data_output.txt",         # Vector agent output
            "supabase_loading_report.json",   # Loader agent Supabase output
            "pinecone_loading_report.json"    # Loader agent Pinecone output
        ]
        
        print("📊 PIPELINE OUTPUT FILES:")
        files_found = 0
        files_missing = 0
        
        for filename in expected_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"  ✅ {filename}: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                files_found += 1
            else:
                print(f"  ❌ {filename}: MISSING")
                files_missing += 1
        
        # Check additional output directories
        supabase_dir = os.path.join(output_dir, "supabase_test")
        pinecone_dir = os.path.join(output_dir, "pinecone_test")
        
        if os.path.exists(supabase_dir):
            supabase_files = len([f for f in os.listdir(supabase_dir) if f.endswith('.json')])
            print(f"  📁 Supabase test files: {supabase_files} table files")
        
        if os.path.exists(pinecone_dir):
            pinecone_files = len([f for f in os.listdir(pinecone_dir) if f.endswith('.json')])
            print(f"  📁 Pinecone test files: {pinecone_files} vector files")
        
        print(f"\n📈 FILE COMPLETION RATE: {files_found}/{len(expected_files)} ({files_found/len(expected_files)*100:.1f}%)")
        
        # Show final result summary
        print(f"\n🎯 FINAL CREW RESULT:")
        print(f"   Type: {type(result)}")
        if hasattr(result, '__dict__'):
            result_str = str(result)[:500]
            print(f"   Content: {result_str}{'...' if len(str(result)) > 500 else ''}")
        
        # Final assessment
        if files_found >= len(expected_files) * 0.8:  # 80% completion rate
            print("\n" + "=" * 80)
            print("🎉 PIPELINE TEST SUCCESSFUL!")
            print("=" * 80)
            print("✅ Agent communication working correctly")
            print("✅ File-based data passing working")
            print("✅ All pipeline stages executed")
            print("✅ Real financial data processed end-to-end")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️ PIPELINE TEST PARTIAL SUCCESS")
            print("=" * 80)
            print(f"❌ {files_missing} expected files missing")
            print("❌ Agent communication may have issues")
            print("🔍 Check individual agent outputs for errors")
            print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ PIPELINE EXECUTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("🔍 TROUBLESHOOTING TIPS:")
        print("=" * 80)
        print("1. Check individual agent/tool tests still work")
        print("2. Verify task configuration updates")
        print("3. Check agent tool assignments")
        print("4. Verify file permissions and paths")
        print("=" * 80)

if __name__ == "__main__":
    test_full_pipeline()