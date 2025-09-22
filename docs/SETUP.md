# AI-Powered Migration Validation System - Setup Guide

## 🚀 Quick Start

**Initialization (Complete Setup):**
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install core dependencies
pip install -e .

# 3. Install AI framework dependencies (required)
pip install crewai crewai-tools

# 4. Start the system
python -m uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000
```

**Quick verification:**
```bash
# Check if system is running
curl http://localhost:8000/health
curl http://localhost:8000/
```

### 1. Environment Setup

```bash
# Create virtual environment (if not done in Quick Start)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install core dependencies
pip install -e .

# Install required AI dependencies
pip install crewai crewai-tools

# For development (optional - includes testing tools)
pip install -e ".[dev,quality]"
```

**Note:** The `crewai` and `crewai-tools` packages are required dependencies that are not automatically installed with the core package. They must be installed separately for the behavioral validation system to work.

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required Configuration:**
- Set at least one LLM provider API key:
  - `OPENAI_API_KEY=your-openai-key`
  - `ANTHROPIC_API_KEY=your-anthropic-key` 
  - `GOOGLE_API_KEY=your-google-key`

### 3. Install Browser Dependencies (for Behavioral Validation)

```bash
# Install Playwright browsers
playwright install

# Verify installation
playwright --version
```

### 4. Run the System

**Start API Server:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Start server (tested and working)
python -m uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000

# Alternative: Using the CLI tool
python -m src.main serve --port 8000
```

**Access the system:**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-22T12:01:28.686491",
  "services": {
    "validator": "operational",
    "input_processor": "operational"
  }
}
```

## 🧪 Testing

**Run all tests:**
```bash
pytest
```

**Run specific test categories:**
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests  
pytest -m behavioral    # Behavioral validation tests
pytest tests/unit/       # Specific directory
```

**Test with coverage:**
```bash
pytest --cov=src --cov-report=html
```

## 📊 Usage Examples

### CLI Usage

**Static Code Validation:**
```bash
python -m src.main validate \
  --source-tech python-flask \
  --target-tech java-spring \
  --source-files ./source_code \
  --target-files ./target_code \
  --scope business_logic \
  --output results.json
```

**Behavioral Validation:**
```bash
python -m src.main behavioral \
  --source-url http://legacy-system.com/app \
  --target-url http://new-system.com/app \
  --scenarios "login,signup,password_reset" \
  --output behavioral_results.json
```

**System Health Check:**
```bash
python -m src.main health
```

### API Usage

**Static Validation:**
```bash
curl -X POST "http://localhost:8000/api/validate" \
  -F "request_data={\"source_technology\":\"python-flask\",\"target_technology\":\"java-spring\",\"validation_scope\":\"business_logic\"}" \
  -F "source_files=@source.py" \
  -F "target_files=@target.java"
```

**Check Validation Status:**
```bash
curl "http://localhost:8000/api/validate/{request_id}/status"
```

**Get Results:**
```bash
curl "http://localhost:8000/api/validate/{request_id}/result"
```

## 🔧 System Architecture

The system implements a unique **dual validation approach**:

### Static Validation Pipeline
1. **Code Analysis** - AST parsing, pattern recognition
2. **Semantic Comparison** - LLM-powered logic analysis  
3. **Report Generation** - Detailed findings and recommendations

### Behavioral Validation Pipeline (Multi-Agent)
1. **Source Explorer Agent** - Maps original system behavior
2. **Target Executor Agent** - Replicates actions on migrated system
3. **Comparison Judge Agent** - Analyzes behavioral differences
4. **Report Manager Agent** - Orchestrates and generates reports

## 🛠️ Configuration Options

### LLM Providers
- **OpenAI**: GPT-4, GPT-3.5-turbo models
- **Anthropic**: Claude-3 models  
- **Google**: Gemini models

### Validation Scopes
- `ui_layout` - User interface and visual elements
- `backend_functionality` - Server-side logic and APIs
- `data_structure` - Database schemas and models
- `api_endpoints` - REST API compatibility
- `business_logic` - Core business rules and workflows
- `behavioral_validation` - Real system behavior testing
- `full_system` - Comprehensive validation

### Supported Technologies
- **Python**: Flask, Django
- **Java**: Spring Framework
- **JavaScript/TypeScript**: React, Vue, Angular
- **C#**: .NET Framework
- **PHP**: Laravel

## 🐛 Troubleshooting

### Common Issues

**LLM API Errors:**
```bash
# Check configuration
python -m src.main config

# Verify API keys are set
echo $OPENAI_API_KEY
```

**Browser Automation Issues:**
```bash
# Reinstall browsers
playwright install --force

# Check if browsers are installed
playwright --version
```

**Import Errors:**
```bash
# Ensure you're in the project root
pwd
# Should show: /path/to/AI-Powered-Migration-Validation-System

# Check Python path
python -c "import sys; print(sys.path)"

# If getting "crewai" import errors, install the dependencies:
pip install crewai crewai-tools

# If getting "List" type errors, this is a known issue fixed in the latest version
```

**Common Dependency Issues:**
```bash
# Missing CrewAI dependencies
pip install crewai crewai-tools

# Missing browser automation tools (for behavioral validation)
pip install playwright
playwright install

# Virtual environment issues
deactivate
source venv/bin/activate

# Port already in use
pkill -f uvicorn
# Then restart the server
```

### Development Setup

**Enable Debug Mode:**
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

**Run with Auto-reload:**
```bash
# Method 1: Direct uvicorn (recommended, tested working)
python -m uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000

# Method 2: Using CLI tool
python -m src.main serve --reload --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Root**: http://localhost:8000/

## 🔐 Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- In production, set `ENVIRONMENT=production` and `DEBUG=false`
- Configure proper CORS origins for production deployment

## 📈 Performance Tuning

- Adjust `ASYNC_CONCURRENCY_LIMIT` based on system resources
- Set `LLM_MAX_TOKENS` to balance cost vs. analysis depth
- Configure `REQUEST_TIMEOUT` for long-running validations
- Use Redis caching for improved performance (optional)

## 🚢 Production Deployment

**Docker Deployment:**
```bash
# Build image
docker build -t migration-validator .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e ENVIRONMENT=production \
  migration-validator
```

**Environment Variables:**
- Set all required API keys
- Configure `DATABASE_URL` if using persistence
- Set appropriate `LOG_LEVEL` and `CORS_ORIGINS`
- Enable Redis for caching if needed