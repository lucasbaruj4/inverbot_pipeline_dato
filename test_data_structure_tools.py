#!/usr/bin/env python3
"""
Test the updated data structure tools (normalize, validate, relationships)
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

def test_data_structure_tools():
    """Test the updated data structure tools."""
    
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
    print("TESTING DATA STRUCTURE TOOLS PIPELINE")
    print("=" * 60)
    
    # Import after setting up environment
    from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
    
    # Check if structured data file exists (from extract tool)
    structured_file = "output/try_1/structured_data_output.txt"
    if not os.path.exists(structured_file):
        print(f"❌ Structured data file not found: {structured_file}")
        print("   Please run the extract tool first!")
        return
    
    print(f"✅ Found structured data file: {structured_file}")
    
    # Create crew instance and get processor agent
    print("🚀 Initializing InverBot Pipeline...")
    crew_instance = InverbotPipelineDato()
    processor_agent = crew_instance.processor()
    
    if not processor_agent:
        print("❌ Processor agent not found!")
        return
    
    # Find the data structure tools
    normalize_tool = None
    validate_tool = None  
    relationships_tool = None
    
    for tool in processor_agent.tools:
        tool_name = getattr(tool, 'name', getattr(tool, '_name', ''))
        if 'Normalize Data Tool' in tool_name:
            normalize_tool = tool
        elif 'Validate Data Tool' in tool_name:
            validate_tool = tool
        elif 'Create Entity Relationships Tool' in tool_name:
            relationships_tool = tool
    
    print(f"✅ Found normalize tool: {'✓' if normalize_tool else '✗'}")
    print(f"✅ Found validate tool: {'✓' if validate_tool else '✗'}")
    print(f"✅ Found relationships tool: {'✓' if relationships_tool else '✗'}")
    
    if not all([normalize_tool, validate_tool, relationships_tool]):
        print("❌ Some tools not found!")
        return
    
    try:
        # STEP 1: Test Normalize Tool
        print("\n" + "=" * 40)
        print("STEP 1: TESTING NORMALIZE TOOL")
        print("=" * 40)
        
        normalize_result = normalize_tool.run("")
        if "error" in normalize_result:
            print(f"❌ Normalize tool failed: {normalize_result['error']}")
            if "error_details" in normalize_result:
                print(f"Error details: {normalize_result['error_details']}")
            return
        
        print("✅ Normalize tool executed successfully!")
        print(f"📊 Total records normalized: {normalize_result.get('report', {}).get('normalized_records', 0)}")
        print(f"📁 Tables processed: {len(normalize_result.get('report', {}).get('tables_processed', []))}")
        
        if normalize_result.get('output_file') and os.path.exists(normalize_result['output_file']):
            file_size = os.path.getsize(normalize_result['output_file'])
            print(f"💾 Output file created: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # STEP 2: Test Validate Tool
        print("\n" + "=" * 40)
        print("STEP 2: TESTING VALIDATE TOOL")
        print("=" * 40)
        
        validate_result = validate_tool.run("")
        if "error" in validate_result:
            print(f"❌ Validate tool failed: {validate_result['error']}")
            if "error_details" in validate_result:
                print(f"Error details: {validate_result['error_details']}")
            return
        
        print("✅ Validate tool executed successfully!")
        report = validate_result.get('report', {})
        print(f"📊 Total records: {report.get('total_records', 0)}")
        print(f"✅ Valid records: {report.get('valid_records', 0)}")
        print(f"❌ Invalid records: {report.get('invalid_records', 0)}")
        print(f"📁 Tables validated: {len(report.get('tables_validated', []))}")
        
        if validate_result.get('output_file') and os.path.exists(validate_result['output_file']):
            file_size = os.path.getsize(validate_result['output_file'])
            print(f"💾 Output file created: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # STEP 3: Test Relationships Tool
        print("\n" + "=" * 40)
        print("STEP 3: TESTING RELATIONSHIPS TOOL")
        print("=" * 40)
        
        relationships_result = relationships_tool.run("")
        if "error" in relationships_result:
            print(f"❌ Relationships tool failed: {relationships_result['error']}")
            if "error_details" in relationships_result:
                print(f"Error details: {relationships_result['error_details']}")
            return
        
        print("✅ Relationships tool executed successfully!")
        rel_report = relationships_result.get('report', {})
        print(f"📊 Total records processed: {rel_report.get('processed_records', 0)}")
        print(f"🔗 Tables with relationships: {len(rel_report.get('tables_processed', []))}")
        
        created_entities = rel_report.get('created_master_entities', {})
        if created_entities:
            print("🏭 Master entities created:")
            for entity_type, count in created_entities.items():
                if count > 0:
                    print(f"   - {entity_type}: {count}")
        
        if relationships_result.get('output_file') and os.path.exists(relationships_result['output_file']):
            file_size = os.path.getsize(relationships_result['output_file'])
            print(f"💾 Output file created: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # SUMMARY
        print("\n" + "=" * 60)
        print("✅ ALL DATA STRUCTURE TOOLS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("🎯 Pipeline Status:")
        print("   ✅ Extract: Structured data extracted from raw content")
        print("   ✅ Normalize: Data normalized and cleaned")
        print("   ✅ Validate: Data validated against schemas") 
        print("   ✅ Relationships: Entity relationships established")
        print("\n🔄 Ready for next phase: Vector Processing")
        
    except Exception as e:
        print(f"❌ PIPELINE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_structure_tools()