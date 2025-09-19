# Code Style and Conventions

## Python Style Guidelines

### Naming Conventions
- **Classes**: PascalCase (`MigrationValidator`, `ValidationResult`)
- **Functions/Methods**: snake_case (`validate_migration`, `analyze_file`)
- **Variables**: snake_case (`fidelity_score`, `execution_time`)
- **Constants**: UPPER_SNAKE_CASE (`INPUT_TYPE`, `SEVERITY_LEVEL`)
- **Private methods**: Leading underscore (`_analyze_file`, `_extract_functions`)

### Type Hints
- **Comprehensive typing**: All functions use type hints
- **Optional types**: `Optional[str]` for nullable values
- **Generic types**: `List[DataField]`, `Dict[str, Any]`
- **Union types**: Used for multiple possible types
- **Return types**: All async functions properly typed

### Documentation Style
- **Docstrings**: Triple-quoted strings with clear descriptions
- **Function docs**: Include Args, Returns, and Raises sections
- **Class docs**: Describe purpose and main responsibilities
- **Module docs**: Explain module's role in the system

### Code Organization
- **Import order**: Standard library, third-party, local imports
- **Dataclasses**: Preferred over regular classes for data structures
- **Enums**: Used for fixed sets of values (`TechnologyType`, `ValidationScope`)
- **Abstract base classes**: Used for interfaces (`BaseAnalyzer`)
- **Exception hierarchy**: Custom exceptions inherit from base classes

### Async/Await Patterns
- **Async methods**: All I/O operations use async/await
- **Function signatures**: Proper async function declarations
- **Error handling**: Try/catch blocks in async contexts
- **Background tasks**: Used for long-running operations

### Error Handling
- **Custom exceptions**: Domain-specific exception classes
- **Error propagation**: Proper exception chaining
- **Logging**: Structured logging with timestamps
- **Graceful degradation**: Fallback mechanisms for failures

### Data Structures
- **Dataclasses**: Primary choice for data containers
- **Field defaults**: Use `field(default_factory=dict)` for mutable defaults
- **Immutability**: Prefer immutable data where possible
- **Validation**: Built-in validation through type hints and Pydantic

## API Design Patterns
- **RESTful endpoints**: Follow REST conventions
- **Response models**: Pydantic models for API responses
- **Error responses**: Consistent error format with HTTPException
- **File uploads**: Proper multipart form handling
- **Async endpoints**: All routes are async for performance