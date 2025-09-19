# Technology Stack

## Core Framework
- **Backend**: Python with FastAPI
- **Language**: Python 3.8+ (based on code analysis)
- **Architecture**: RESTful API with async/await support

## Current Implementation (Static Validation)
- **Web Framework**: FastAPI with async support
- **Data Models**: Python dataclasses with Enums
- **File Processing**: AST parsing for Python, regex for other languages
- **API Design**: RESTful endpoints with file upload support
- **Error Handling**: Custom exception hierarchy

## Planned Additions (Behavioral Validation)
- **AI Orchestration**: CrewAI for multi-agent coordination
- **Browser Automation**: browser-use + Playwright
- **LLM Integration**: Gemini/GPT-4 for semantic analysis

## Dependencies (Inferred from Code)
- **FastAPI**: Web framework with auto-documentation
- **Pydantic**: Data validation and serialization
- **Python AST**: Code parsing and analysis
- **CORS Middleware**: Cross-origin request support
- **Uvicorn**: ASGI server for FastAPI

## File Organization
```
src/
├── core/              # Core business logic
│   ├── migration_validator.py
│   ├── models.py
│   ├── input_processor.py
├── api/               # REST API layer
│   └── routes.py
├── analyzers/         # Code analysis engines
│   ├── base.py
│   ├── code_analyzer.py
│   └── visual_analyzer.py
├── comparators/       # Semantic comparison
│   └── semantic_comparator.py
└── reporters/         # Report generation
    └── validation_reporter.py
```

## Development Environment
- **Platform**: Linux (development environment)
- **Server**: Uvicorn ASGI server
- **Entry Point**: `src.api.routes:app`
- **Port**: 8000 (default)