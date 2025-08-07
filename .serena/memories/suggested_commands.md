# Suggested Commands for InverBot Development

## Project Execution
```bash
# Run the main pipeline
python -m inverbot_pipeline_dato.main
# or
python src/inverbot_pipeline_dato/main.py

# Test mode execution (safe for development)
python src/inverbot_pipeline_dato/main.py --test

# Production mode execution (writes to real databases)
python src/inverbot_pipeline_dato/main.py --production

# CrewAI commands
crewai run                    # Alternative execution method
crewai install                # Install dependencies
crewai test                   # Test mode execution
```

## Development and Testing
```bash
# Environment setup
pip install -e .              # Install in development mode
uv sync                       # Sync dependencies with uv

# Code validation
python -c "from src.inverbot_pipeline_dato.crew import InverbotPipelineDato; crew = InverbotPipelineDato(); print('Success!')"

# Test individual components
python -c "from dotenv import load_dotenv; load_dotenv('.env.local'); print('Environment loaded')"
```

## File Navigation (Windows-specific)
```bash
# Directory navigation
cd src/inverbot_pipeline_dato
ls -la                        # List files (in git bash)
dir                          # List files (in cmd)

# View large files safely
head -50 crew.py             # First 50 lines (git bash)
type crew.py | findstr /n "def"  # Find function definitions (cmd)

# Search within files
findstr /n "tool" crew.py    # Find tool decorators (cmd)
grep -n "@tool" crew.py      # Find tool decorators (git bash)
```

## Git Operations
```bash
git status                   # Check repository status
git add .                    # Stage all changes
git commit -m "message"      # Commit changes
git log --oneline -10        # View recent commits
git diff HEAD~1              # View latest changes
```

## Database and API Testing
```bash
# Test API connections (requires .env.local)
python -c "
from dotenv import load_dotenv
import os
load_dotenv('.env.local')
print('GEMINI_API_KEY:', 'SET' if os.getenv('GEMINI_API_KEY') else 'MISSING')
print('FIRECRAWL_API_KEY:', 'SET' if os.getenv('FIRECRAWL_API_KEY') else 'MISSING')
print('SUPABASE_URL:', 'SET' if os.getenv('SUPABASE_URL') else 'MISSING')
print('PINECONE_API_KEY:', 'SET' if os.getenv('PINECONE_API_KEY') else 'MISSING')
"
```

## Debugging and Monitoring
```bash
# Check output files
ls output/test_results/      # Test mode outputs
ls output/try_*/            # CrewAI task outputs

# Monitor real-time execution (in separate terminal)
tail -f output/test_results/performance_report_*.md

# Memory and performance
tasklist | findstr python   # Check Python processes (Windows)
```

## Common Development Tasks
```bash
# Update environment variables
notepad .env.local           # Edit environment file (Windows)

# Modify test mode
# Edit crew.py line ~334: test_mode = True/False

# Check logs and debug info
# All outputs saved to output/ directory
# Performance reports in output/test_results/
# Task outputs in output/try_*/ directories
```

## Project Structure Navigation
```
src/inverbot_pipeline_dato/
├── crew.py                  # Main pipeline (3800+ lines)
├── main.py                  # Entry point and execution
├── config/
│   ├── agents.yaml          # Agent definitions
│   └── tasks.yaml           # Task workflows
├── tools/                   # Custom tools (mostly unused)
└── data/                    # Data utilities
```