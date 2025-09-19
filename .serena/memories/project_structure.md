# Project Structure Overview

## Root Directory Layout
```
AI-Powered-Migration-Validation-System/
├── docs/                    # Comprehensive documentation
├── src/                     # Main source code
├── tests/                   # Test directories (empty - needs implementation)
├── config/                  # Configuration files (empty)
├── .serena/                 # Serena MCP configuration
├── .claude/                 # Claude configuration
├── README.md               # Basic project description
├── proposta.md             # Detailed proposal (Portuguese)
└── evolucao.md             # Evolution/architecture updates
```

## Source Code Structure (`src/`)
```
src/
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── migration_validator.py    # Main orchestrator
│   ├── models.py                 # Data models and enums
│   └── input_processor.py        # Input data processing
├── api/                     # REST API layer
│   ├── __init__.py
│   └── routes.py                 # FastAPI routes and endpoints
├── analyzers/               # Analysis engines
│   ├── __init__.py
│   ├── base.py                   # Base analyzer interface
│   ├── code_analyzer.py          # Code analysis (AST, regex)
│   └── visual_analyzer.py        # Visual/screenshot analysis
├── comparators/             # Comparison logic
│   └── semantic_comparator.py    # Semantic comparison engine
└── reporters/               # Report generation
    └── validation_reporter.py    # Report formatting and generation
```

## Documentation Structure (`docs/`)
```
docs/
├── README.md                     # Documentation index
├── architecture-analysis.md     # System architecture review
├── deployment-guide.md          # Deployment instructions
├── implementation-backlog.md    # Development backlog/stories
├── technical-specifications.md  # Technical implementation details
└── testing-strategy.md          # Comprehensive testing approach
```

## Key Components

### Core Layer (`src/core/`)
- **MigrationValidator**: Main orchestrator class
- **Models**: Data structures using dataclasses and enums
- **InputProcessor**: Handles file uploads and data processing

### API Layer (`src/api/`)
- **Routes**: FastAPI application with RESTful endpoints
- **File uploads**: Source/target file handling
- **Background tasks**: Async validation processing
- **Error handling**: HTTP exceptions and responses

### Analysis Layer (`src/analyzers/`)
- **BaseAnalyzer**: Abstract interface for all analyzers
- **CodeAnalyzer**: Language-specific code parsing (Python, JS, Java, etc.)
- **VisualAnalyzer**: Screenshot and UI analysis

### Comparison Layer (`src/comparators/`)
- **SemanticComparator**: AI-powered semantic comparison logic

### Reporting Layer (`src/reporters/`)
- **ValidationReporter**: Multiple format report generation (JSON, HTML, Markdown)

## Missing Components (Development Needed)
- **Test suite**: Complete test infrastructure needed
- **Configuration management**: Environment-specific settings
- **Dependencies**: requirements.txt files need creation
- **CI/CD**: GitHub Actions workflows
- **LLM integration**: AI service connections
- **Browser automation**: CrewAI + browser-use implementation

## Technology-Specific Analysis Support
- **Python**: AST parsing, Flask/Django route detection
- **JavaScript/TypeScript**: React component extraction, API call detection
- **Java**: Basic pattern matching (needs enhancement)
- **C#**: Basic pattern matching (needs enhancement)
- **PHP**: Basic pattern matching (needs enhancement)
- **HTML**: Form element extraction, UI component detection