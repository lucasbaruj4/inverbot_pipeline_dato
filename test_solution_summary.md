# Solution Summary: Document Processing Limits for CrewAI Pipeline

## Problem
The CrewAI pipeline was failing with "Invalid response from LLM call - None or empty" because it was trying to process too many PDFs and Excel files at once, overwhelming the system.

## Solution Implemented

### 1. Document Processing Limits
Added global counters and limits to `crew.py`:
- Maximum 3 PDFs per pipeline run
- Maximum 2 Excel files per pipeline run
- Tools automatically skip documents once limits are reached

### 2. Direct Document Processor
Created `direct_processor.py` that:
- Processes ALL documents found in raw_extraction_output.txt
- Works independently of CrewAI (no LLM orchestration)
- Includes checkpoint/resume capability
- Saves results incrementally to structured_data_output.txt

### 3. Two-Phase Workflow

**Phase 1: Limited CrewAI Processing**
```bash
python -m src.inverbot_pipeline_dato.main test_mode
```
- Scrapes all 10 sources
- Processes only first 3 PDFs and 2 Excel files
- Completes quickly without overwhelming the system

**Phase 2: Complete Document Processing**
```bash
python -m src.inverbot_pipeline_dato.direct_processor
```
- Reads all document URLs from raw_extraction_output.txt
- Processes remaining PDFs and Excel files
- Appends results to structured_data_output.txt

## Key Changes Made

### In `crew.py`:
```python
# Global counters and limits
DOCUMENT_COUNTERS = {'pdf': 0, 'excel': 0, ...}
DOCUMENT_LIMITS = {'pdf': 3, 'excel': 2, 'enabled': True}

# Tools check limits before processing
if not should_process_document('pdf', pdf_url):
    return {"status": "skipped", "reason": "Document limit reached"}

# Increment counter after successful processing
increment_document_counter('pdf', pdf_url)
```

### In `tasks.yaml`:
```yaml
1. **extract_text_from_pdf** & **extract_text_from_excel** - [LIMITED MODE]
   - Document limits are active - Max 3 PDFs and 2 Excel files
   - Skipped documents will be processed later via direct_processor.py
```

## Benefits
1. **No more LLM failures** - Processing stays within manageable limits
2. **Complete data extraction** - All documents get processed eventually
3. **Flexible approach** - Can adjust limits based on needs
4. **Resume capability** - Direct processor can resume from interruptions
5. **Cost effective** - Uses LLM only for orchestration, not bulk processing

## Usage
1. Run the pipeline with limits to get initial data quickly
2. Run direct processor to complete all document extraction
3. Continue with vectorization and database loading

This solution provides immediate relief while maintaining the ability to process all documents completely.