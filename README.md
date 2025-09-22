# 🤖 AI-Powered Migration Validation System

**Intelligent software migration validation using LLMs and multi-agent frameworks**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-327%2B-brightgreen.svg)](./tests/)
[![Coverage](https://img.shields.io/badge/coverage-85%25+-success.svg)](./htmlcov/)

## 🚀 Quick Start

### **Core Installation** (Minimal Dependencies)
```bash
# Clone and install core system
git clone <repository-url>
cd AI-Powered-Migration-Validation-System
pip install -e .

# Start basic API server
uvicorn src.main:app --reload
```

### **Development Setup** (Full Feature Set)
```bash
# Install with all development tools
pip install -e ".[dev,quality,ai,browser,database,tools]"

# Run tests
python run_tests.py --coverage

# Start development server
uvicorn src.main:app --reload --port 8000
```

### **Production Deployment**
```bash
# Install production dependencies
pip install -e ".[ai,crewai,database,cache,security]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Start production server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 📦 Installation Options

| Use Case | Installation Command |
|----------|---------------------|
| **Basic API** | `pip install -e .` |
| **Development** | `pip install -e ".[dev,quality,tools]"` |
| **AI Features** | `pip install -e ".[ai,crewai]"` |
| **Browser Testing** | `pip install -e ".[browser,dev]"` |
| **Full Production** | `pip install -e ".[ai,crewai,database,cache,security]"` |
| **Everything** | `pip install -e ".[all]"` |

## 🏗️ Architecture

- **Core API**: FastAPI-based REST API for migration validation
- **LLM Integration**: OpenAI, Anthropic, Google AI support
- **Multi-Agent**: CrewAI framework for complex validation workflows
- **Browser Automation**: Playwright + browser-use for behavioral testing
- **Async Processing**: Full async/await support for performance

## 📚 Documentation

- **[Complete Setup Guide](./docs/SETUP.md)** - Detailed installation and configuration
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (after starting server)
- **[Testing Strategy](./docs/testing-strategy.md)** - Comprehensive testing approach
- **[Architecture Analysis](./docs/architecture-analysis.md)** - System design overview
- **[Deployment Guide](./docs/deployment-guide.md)** - Production deployment

## 🧪 Testing

```bash
# Run all tests with coverage
python run_tests.py --coverage --html-report

# Run specific test categories
python run_tests.py --unit          # Unit tests only
python run_tests.py --integration   # Integration tests
python run_tests.py --behavioral    # AI agent & browser tests
python run_tests.py --system        # End-to-end tests

# Fast tests (skip slow operations)
python run_tests.py --fast --coverage
```

## 🔧 Configuration

Create `.env` file with required settings:

```env
# LLM API Keys (choose your provider)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Optional: Database and caching
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
```

## 🤝 Contributing

1. Install development environment: `pip install -e ".[dev,quality,tools]"`
2. Run tests: `python run_tests.py --coverage`
3. Check code quality: `black . && flake8 . && mypy src/`
4. Submit pull request

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

**🎯 Status**: Production Ready | **📊 Test Coverage**: 85%+ | **🚀 Performance**: <1s API response