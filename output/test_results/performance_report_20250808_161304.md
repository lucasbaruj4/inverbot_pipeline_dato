# InverBot Pipeline Performance Report

**Generated**: 2025-08-08T16:13:04.921333
**Test Mode**: ENABLED
**Total Pipeline Duration**: 259.31 seconds

## Component Status Overview

- **Extractor**: [PENDING] Pending
  - Records Extracted: 0
- **Processor**: [PENDING] Pending
  - Records Processed: 0
- **Vector**: [PENDING] Pending
  - Vectors Created: 0
- **Loader**: [PENDING] Pending
  - Records Loaded: 0

## Agent Performance Details

## Resource Usage

- **Total Tokens**: 0
- **Firecrawl Credits**: 0
- **Embedding API Calls**: 0

## Errors

- [16:13:04] Pipeline failed: Invalid response from LLM call - None or empty.

## Quick Verification Checklist

### Data Flow Verification
- [ ] Extractor: Check raw extraction output files
- [ ] Processor: Verify structured data output
- [ ] Vector: Confirm chunking and metadata preparation
- [ ] Loader: Review test mode output files

### Quality Checks
- [ ] No critical errors in the pipeline
- [ ] Record counts make sense across stages
- [ ] Output files are properly formatted
- [ ] Performance metrics within acceptable ranges

### Next Steps
- [ ] Review all test output files in `output/test_results/`
- [ ] Verify data quality and completeness
- [ ] Set `test_mode = False` for production run
