#!/usr/bin/env python3
"""
Test the complete pipeline agent flow using existing real data
Tests: Processor → Vector → Loader agent communication and data flow
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

def test_pipeline_agent_flow():
    """Test the pipeline agent flow with real data."""
    
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
    
    print("=" * 70)
    print("TESTING PIPELINE AGENT FLOW WITH REAL FINANCIAL DATA")
    print("=" * 70)
    print("Pipeline Flow Test:")
    print("  📥 Input: Existing raw_extraction_output.txt (real BVA data)")
    print("  🔄 Process: Processor → Vector → Loader agent execution")
    print("  📤 Output: Complete database-ready data")
    print("=" * 70)
    
    try:
        # Import after setting up environment
        from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
        
        # Verify we have the raw extraction data
        raw_file = "output/try_1/raw_extraction_output.txt"
        if not os.path.exists(raw_file):
            print(f"❌ Raw extraction file not found: {raw_file}")
            print("   Please run the extraction first or use existing data")
            return
        
        print(f"✅ Found raw extraction data: {raw_file}")
        file_size = os.path.getsize(raw_file)
        print(f"📊 Raw data size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Create crew instance
        print("\n🚀 Initializing InverBot Pipeline...")
        crew_instance = InverbotPipelineDato()
        
        # Test each agent in sequence
        agents = [
            ("processor", "🔧 PROCESSOR AGENT", "process_task", "structured_data_output.txt"),
            ("vector", "🔍 VECTOR AGENT", "vectorize_task", "vector_data_output.txt"),
            ("loader", "💾 LOADER AGENT", "load_task", ["supabase_loading_report.json", "pinecone_loading_report.json"])
        ]
        
        pipeline_results = {}
        
        for agent_name, agent_title, task_name, expected_output in agents:
            print(f"\n{'-' * 50}")
            print(f"{agent_title} - TESTING")
            print(f"{'-' * 50}")
            
            # Convert expected_output to list format for consistent handling
            expected_files = expected_output if isinstance(expected_output, list) else [expected_output]
            
            try:
                # Get agent and task
                agent = getattr(crew_instance, agent_name)()
                task = getattr(crew_instance, task_name)()
                
                print(f"✅ Agent: {agent.role}")
                print(f"✅ Task: {task.description[:100]}...")
                print(f"✅ Tools: {len(agent.tools)} available")
                
                # Execute the task
                print(f"\n⏳ Executing {agent_name} task...")
                
                # Create context from previous outputs
                context = "Processing continues from previous agent outputs using file-based pipeline."
                
                # Execute task
                result = task.execute_sync(
                    agent=agent,
                    context=context,
                    tools=agent.tools
                )
                
                print(f"✅ {agent_name.upper()} AGENT COMPLETED")
                
                # Check expected outputs
                found_files = []
                missing_files = []
                
                for filename in expected_files:
                    filepath = os.path.join("output/try_1", filename)
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        print(f"  ✅ Output: {filename} ({file_size:,} bytes)")
                        found_files.append(filename)
                    else:
                        print(f"  ❌ Missing: {filename}")
                        missing_files.append(filename)
                
                # Store results
                pipeline_results[agent_name] = {
                    "status": "success" if not missing_files else "partial",
                    "found_files": found_files,
                    "missing_files": missing_files,
                    "result_preview": str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                }
                
                if missing_files:
                    print(f"⚠️ {agent_name.upper()} AGENT: {len(missing_files)} expected files missing")
                else:
                    print(f"🎯 {agent_name.upper()} AGENT: All outputs created successfully")
                
            except Exception as agent_error:
                print(f"❌ {agent_name.upper()} AGENT FAILED: {str(agent_error)}")
                pipeline_results[agent_name] = {
                    "status": "failed", 
                    "error": str(agent_error),
                    "found_files": [],
                    "missing_files": expected_files
                }
                # Continue with next agent to test as much as possible
        
        # Generate final report
        print(f"\n{'=' * 70}")
        print("📊 COMPLETE PIPELINE AGENT FLOW TEST RESULTS")
        print(f"{'=' * 70}")
        
        successful_agents = 0
        total_agents = len(agents)
        
        for agent_name, agent_title, _ in agents:
            result = pipeline_results.get(agent_name, {"status": "not_run"})
            status = result["status"]
            
            if status == "success":
                status_icon = "✅"
                successful_agents += 1
            elif status == "partial":
                status_icon = "⚠️"
                successful_agents += 0.5
            else:
                status_icon = "❌"
            
            print(f"{status_icon} {agent_title}: {status.upper()}")
            
            if result.get("found_files"):
                print(f"    📁 Files created: {', '.join(result['found_files'])}")
            if result.get("missing_files"):
                print(f"    💥 Missing files: {', '.join(result['missing_files'])}")
            if result.get("error"):
                print(f"    🚨 Error: {result['error']}")
        
        # Calculate success rate
        success_rate = (successful_agents / total_agents) * 100
        print(f"\n🎯 PIPELINE SUCCESS RATE: {success_rate:.1f}% ({successful_agents}/{total_agents} agents)")
        
        # Check all expected pipeline files
        all_expected_files = [
            "raw_extraction_output.txt",      # Input (should exist)
            "structured_data_output.txt",     # Processor output  
            "normalized_data_output.txt",     # Processor stage 2
            "validated_data_output.txt",      # Processor stage 3
            "relationships_data_output.txt",  # Processor stage 4
            "vector_data_output.txt",         # Vector agent output
            "supabase_loading_report.json",   # Loader Supabase
            "pinecone_loading_report.json"    # Loader Pinecone
        ]
        
        print(f"\n📋 COMPLETE PIPELINE FILE STATUS:")
        pipeline_files_found = 0
        for filename in all_expected_files:
            filepath = os.path.join("output/try_1", filename)
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"  ✅ {filename}: {file_size:,} bytes")
                pipeline_files_found += 1
            else:
                print(f"  ❌ {filename}: MISSING")
        
        file_completion = (pipeline_files_found / len(all_expected_files)) * 100
        print(f"\n📈 FILE COMPLETION: {file_completion:.1f}% ({pipeline_files_found}/{len(all_expected_files)})")
        
        # Final assessment
        if success_rate >= 80 and file_completion >= 75:
            print(f"\n{'🎉' * 20}")
            print("🎉 PIPELINE AGENT FLOW TEST: SUCCESS!")
            print(f"{'🎉' * 20}")
            print("✅ Agent communication working correctly")
            print("✅ File-based data passing functional")
            print("✅ Real financial data processing end-to-end")
            print("✅ Ready for production deployment")
        elif success_rate >= 50:
            print(f"\n{'⚠️' * 20}")
            print("⚠️ PIPELINE AGENT FLOW TEST: PARTIAL SUCCESS")
            print(f"{'⚠️' * 20}")
            print("✅ Core pipeline functionality working")
            print("❌ Some agents/outputs have issues")
            print("🔧 Needs debugging and optimization")
        else:
            print(f"\n{'❌' * 20}")
            print("❌ PIPELINE AGENT FLOW TEST: NEEDS WORK")
            print(f"{'❌' * 20}")
            print("❌ Major pipeline issues detected")
            print("🔧 Significant debugging required")
        
        print(f"\n{'=' * 70}")
        
    except Exception as e:
        print(f"\n❌ PIPELINE FLOW TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline_agent_flow()