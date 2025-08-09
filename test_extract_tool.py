#!/usr/bin/env python3
"""
Test the new extract_structured_data_from_raw tool
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

def test_extract_tool():
    """Test the new extract_structured_data_from_raw tool."""
    
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
    print("TESTING NEW EXTRACT_STRUCTURED_DATA_FROM_RAW TOOL")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if raw extraction file exists
    raw_file = "output/try_1/raw_extraction_output.txt"
    if not os.path.exists(raw_file):
        print(f"❌ Raw extraction file not found: {raw_file}")
        return
    
    print(f"✅ Found raw extraction file: {raw_file}")
    
    # Create crew instance and get the tool
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    
    # Get the processor agent and tools
    processor_agent = crew_instance.processor()
    if not processor_agent:
        print("❌ Processor agent not found!")
        return
    
    # Find the extract tool
    extract_tool = None
    for tool in processor_agent.tools:
        tool_name = getattr(tool, 'name', getattr(tool, '_name', ''))
        if 'Extract Structured Data from Raw Content' in tool_name:
            extract_tool = tool
            break
    
    if not extract_tool:
        print("❌ Extract structured data tool not found!")
        print(f"Available tools: {[getattr(t, 'name', getattr(t, '_name', str(t))) for t in processor_agent.tools]}")
        return
    
    print(f"✅ Found extract tool: {getattr(extract_tool, 'name', getattr(extract_tool, '_name', 'unknown'))}")
    
    # Execute the tool
    print("\n" + "=" * 60)
    print("EXECUTING EXTRACT TOOL")
    print("=" * 60)
    
    try:
        # Execute tool using its run method
        result = extract_tool.run("")  # Pass empty string as dummy parameter
        
        print("✅ EXTRACT TOOL EXECUTED SUCCESSFULLY!")
        print("=" * 60)
        
        if "error" in result:
            print(f"❌ Tool returned error: {result['error']}")
            if "error_details" in result:
                print(f"Error details: {result['error_details']}")
        else:
            # Show results summary
            structured_data = result.get("structured_data", {})
            processing_report = result.get("processing_report", {})
            
            print("STRUCTURED DATA SUMMARY:")
            for table_name, records in structured_data.items():
                print(f"  {table_name}: {len(records)} records")
            
            print(f"\nPROCESSING REPORT:")
            print(f"  Status: {processing_report.get('status', 'unknown')}")
            print(f"  Total records: {processing_report.get('records_extracted', 0)}")
            print(f"  Tables populated: {processing_report.get('tables_populated', 0)}")
            
            if "extraction_details" in processing_report:
                details = processing_report["extraction_details"]
                print(f"  Emisores found: {details.get('emisores_found', 0)}")
                print(f"  Bonds processed: {details.get('bonds_processed', 0)}")
                print(f"  Macro indicators: {details.get('macro_indicators', 0)}")
            
            # Check if output file was created
            output_file = result.get("output_file")
            if output_file and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"\n✅ Output file created: {output_file}")
                print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            else:
                print(f"\n⚠️ Output file not found or not created")
        
    except Exception as e:
        print(f"❌ EXTRACT TOOL FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extract_tool()