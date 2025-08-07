# Task Completion Checklist - InverBot Project

## When a Task is Completed

### 1. Code Validation
- [ ] **Syntax Check**: Run `python -c "import crew"` to verify no syntax errors
- [ ] **Import Test**: Test that all new imports work correctly
- [ ] **Function Test**: If functions were added/modified, test them individually
- [ ] **Tool Registration**: Ensure new tools are added to appropriate agent tool lists

### 2. Testing Requirements
- [ ] **Test Mode Execution**: Run pipeline with `test_mode=True`
- [ ] **Individual Tool Test**: Test new/modified tools in isolation
- [ ] **Error Handling Test**: Verify error conditions are handled gracefully
- [ ] **Output Validation**: Check that outputs match expected formats

### 3. Documentation Updates
- [ ] **CLAUDE.md**: Update with architectural changes or new features
- [ ] **TASKS.md**: Mark completed tasks and update status
- [ ] **CHATLOG.md**: Log the work performed and outcomes
- [ ] **Code Comments**: Add/update docstrings and inline comments

### 4. File and Environment Management
- [ ] **Dependencies**: Update pyproject.toml if new packages added
- [ ] **Environment Variables**: Document any new .env requirements
- [ ] **Output Cleanup**: Clear test output files if needed
- [ ] **Git Status**: Check for untracked files that should be committed

### 5. Integration Verification
- [ ] **Agent Configuration**: Verify agents.yaml includes new tools
- [ ] **Task Configuration**: Verify tasks.yaml reflects new workflows
- [ ] **Tool Chain**: Ensure new tools integrate properly with existing pipeline
- [ ] **Data Flow**: Verify data passes correctly between agents

## Specific Commands to Run

### Immediate Verification
```bash
# Test syntax and imports
python -c "from src.inverbot_pipeline_dato.crew import InverbotPipelineDato; print('✅ Import successful')"

# Test crew initialization
python -c "
from dotenv import load_dotenv
load_dotenv('.env.local') 
from src.inverbot_pipeline_dato.crew import InverbotPipelineDato
crew = InverbotPipelineDato()
print('✅ Crew initialization successful')
"
```

### Full Pipeline Test
```bash
# Run in test mode
python src/inverbot_pipeline_dato/main.py --test

# Check output files
ls output/test_results/
ls output/try_*/
```

### Performance Validation
- [ ] **Execution Time**: Reasonable completion time in test mode
- [ ] **Memory Usage**: No excessive memory consumption
- [ ] **API Limits**: Verify no rate limiting issues
- [ ] **Error Rate**: Minimal errors in normal execution

## Quality Standards

### Code Quality
- [ ] **No Magic Numbers**: Use named constants for important values
- [ ] **Error Messages**: Descriptive error messages with context
- [ ] **Return Values**: Consistent return formats across similar tools
- [ ] **Type Safety**: Proper type hints and validation

### Data Quality
- [ ] **Schema Compliance**: Data matches Supabase table schemas
- [ ] **Duplicate Handling**: Proper duplicate detection and handling
- [ ] **Data Validation**: Required fields populated correctly
- [ ] **Format Consistency**: Dates, numbers, text in consistent formats

### Documentation Quality
- [ ] **Clear Descriptions**: Easy to understand what code does
- [ ] **Usage Examples**: Include examples for complex functions
- [ ] **Configuration Notes**: Document any special setup requirements
- [ ] **Troubleshooting**: Include common issues and solutions

## Before Marking Task Complete

### Final Checklist
- [ ] All automated tests pass
- [ ] Manual testing completed successfully
- [ ] Documentation is updated and accurate
- [ ] No known bugs or issues remain
- [ ] Performance is acceptable
- [ ] Code follows project conventions
- [ ] Integration points are verified
- [ ] Context files are updated

### Handoff Information
When marking a task complete, always include:
1. **What was implemented** (specific features/fixes)
2. **How to test it** (command sequences)
3. **Known limitations** (if any)
4. **Next recommended steps** (if applicable)
5. **Files modified** (with key line numbers)