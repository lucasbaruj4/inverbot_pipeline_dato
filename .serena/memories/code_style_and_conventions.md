# Code Style and Conventions - InverBot Project

## Python Code Style

### General Conventions
- **Python Version**: 3.10+ (compatible up to 3.13)
- **Code Formatting**: Standard Python PEP 8 style
- **Line Length**: Reasonable (no strict limit, but keep readable)
- **Indentation**: 4 spaces (standard Python)

### Naming Conventions
- **Functions**: `snake_case` (e.g., `scrape_bva_emisores`, `extract_text_from_pdf`)
- **Variables**: `snake_case` (e.g., `test_mode`, `model_llm`)
- **Classes**: `PascalCase` (e.g., `InverbotPipelineDato`)
- **Constants**: `UPPER_SNAKE_CASE` (rare in this project)
- **Private methods**: Leading underscore (e.g., `_process_bva_content`)

### CrewAI-Specific Patterns

#### Tool Definitions
```python
@tool("Tool Display Name")
def tool_function_name(parameter: type, test_mode=True) -> str:
    \"\"\"Tool description for LLM understanding.
    
    Args:
        parameter: Description of parameter
        test_mode: Always include for development flexibility
        
    Returns:
        String result (tools should return strings for LLM consumption)
    \"\"\"
    try:
        # Implementation
        return "Success result"
    except Exception as e:
        return f"Error: {str(e)}"
```

#### Agent Definitions
```python
@agent
def agent_name(self) -> Agent:
    return Agent(
        config=self.agents_config['agent_name'],
        verbose=True,
        llm=self.model_llm,
        tools=[self.tool1, self.tool2, self.tool3]
    )
```

#### Task Definitions
```python
@task
def task_name(self) -> Task:
    return Task(config=self.tasks_config['task_name'])
```

## Documentation Standards

### Docstrings
- **Format**: Standard Google-style docstrings
- **Required for**: All public functions, tools, agents, tasks
- **Include**: Purpose, parameters, return values, examples if complex

### Comments
- **Inline comments**: For complex logic explanation
- **Section headers**: Use `# ====` style for major sections
- **TODO/FIXME**: Use when appropriate with context

### Type Hints
- **Function parameters**: Always include where possible
- **Return types**: Always specify
- **Complex types**: Use from `typing` module when needed

## Project-Specific Patterns

### Error Handling
```python
try:
    # Main logic
    result = process_data()
    return result
except Exception as e:
    return f"Error in {function_name}: {str(e)}"
```

### Test Mode Integration
```python
def tool_function(self, param: str, test_mode=True) -> str:
    # Always include test_mode parameter
    timeout = 30000 if test_mode else 60000
    limit = 10 if test_mode else 50
```

### Data Structure Returns
```python
# For tools returning structured data
result = {
    "success": True,
    "data": processed_data,
    "metadata": {
        "timestamp": datetime.now().isoformat(),
        "source": "data_source_name"
    },
    "report": {
        "records_processed": count,
        "errors": error_list
    }
}
return json.dumps(result, indent=2, ensure_ascii=False)
```

## File Organization

### Main Structure
- **crew.py**: Monolithic file with all tools and agents (3800+ lines)
- **main.py**: Entry point with configuration and execution logic
- **config/**: YAML configurations for agents and tasks
- **tools/**: Custom tools (legacy, mostly unused)

### Import Organization
```python
# Standard library imports first
import os
import json
from datetime import datetime
from typing import List, Dict

# Third-party imports
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import tool

# Local imports last
from .custom_modules import helper_function
```

## Database and API Integration

### Environment Variables
- Always load from `.env.local` first, then `.env`
- Use descriptive names: `SUPABASE_URL`, `PINECONE_API_KEY`
- Never commit API keys to repository

### API Error Handling
```python
try:
    response = api_call()
    if isinstance(response, dict):
        # Handle dictionary response
        data = response.get('data', response)
    else:
        # Handle object response
        data = getattr(response, 'data', response)
    return process_data(data)
except Exception as e:
    return f"API error: {str(e)}"
```

## Testing Conventions

### Test Mode Usage
- All tools should support `test_mode=True` parameter
- Test mode should limit API calls and data processing
- Never write to production databases in test mode

### Output Validation
- All tools return strings for LLM consumption
- Include metadata and error information in responses
- Use JSON format for structured returns when appropriate