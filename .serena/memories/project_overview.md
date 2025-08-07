# InverBot Pipeline Dato - Project Overview

## Purpose
InverBot is a sophisticated ETL (Extract, Transform, Load) system designed to collect, process, and store Paraguayan financial data. The system uses CrewAI multi-agent architecture to create a comprehensive database for financial analysis and RAG (Retrieval-Augmented Generation) applications.

## Architecture
```
Extractor (10 scrapers) → Processor (5 tools) → Vector (5 tools) → Loader (4 tools)
     ↓                      ↓                    ↓                   ↓
Raw Content         → Data Structuring    → Document Processing → Database Storage
Firecrawl API       → Normalization      → PDF/Excel Extraction → Supabase (structured)
Web Scraping        → Validation         → Text Chunking        → Pinecone (vectors)
                    → Relationships      → Embeddings
```

## Data Sources (Paraguayan Financial Data)
1. **BVA (Bolsa de Valores de Asunción)**
   - Company listings and balances
   - Daily, monthly, annual reports
   - Stock market movements

2. **Government Data**
   - Open data portal (datos.gov.py)
   - INE statistics (ine.gov.py)
   - Economic indicators

3. **Public Contracts**
   - DNCP procurement data
   - DNIT investment information
   - Government financial reports

## Tech Stack
- **Framework**: CrewAI multi-agent system
- **Language**: Python 3.10-3.13
- **Web Scraping**: Firecrawl API with native CrewAI tools
- **Database**: Supabase (14 tables) + Pinecone (3 vector indices)
- **LLM**: Gemini 2.5 Flash for processing
- **Embeddings**: Gemini embedding-001 (768 dimensions)
- **Document Processing**: PyMuPDF, tiktoken, openpyxl

## Key Features
- **Multi-format Processing**: PDFs, Excel files, CSV, SVG
- **Intelligent Chunking**: 1200 tokens with 200 token overlap
- **Duplicate Detection**: Both structured and vector data
- **Test Mode**: Safe testing without database writes
- **Performance Tracking**: Comprehensive metrics and reporting
- **Error Resilience**: Robust error handling and retry logic

## Current Status
✅ **Fully Operational**: All 24 tools implemented and tested
✅ **Architecture Restored**: After corruption incident, fully recovered
✅ **Response Handling Fixed**: Dict/object API response issues resolved
✅ **Dependencies**: All multimodal tools (PyMuPDF, tiktoken, openpyxl) installed
✅ **Ready for Testing**: Test mode enabled for safe validation