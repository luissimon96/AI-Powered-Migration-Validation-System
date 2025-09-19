# Suggested Development Commands

## Running the Application

### Development Server
```bash
# Start development server with auto-reload
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000 --reload

# Alternative development start
python -m uvicorn src.api.routes:app --reload
```

### Production Server
```bash
# Production server (no reload)
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000
```

## Testing Commands

### Unit Tests
```bash
# Run all unit tests
pytest tests/unit/ -v --cov=src --cov-report=xml

# Run specific test file
pytest tests/unit/test_models.py -v

# Run with coverage report
pytest tests/unit/ --cov=src --cov-report=html
```

### Integration Tests
```bash
# Run integration tests
pytest tests/integration/ -v

# Run with database setup
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_db pytest tests/integration/ -v
```

### All Tests
```bash
# Run all tests with markers
pytest tests/ -v -m "not slow"

# Run performance tests
pytest tests/performance/ -v -m performance

# Run security tests
pytest tests/security/ -v -m security
```

## Code Quality Commands

### Linting and Formatting
```bash
# Format code with Black
black src/ tests/

# Check with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/

# Security check with bandit
bandit -r src/

# Safety check for vulnerabilities
safety check
```

### Development Dependencies
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install production dependencies only
pip install -r requirements.txt
```

## API Testing Commands

### Health Check
```bash
# Check if API is running
curl http://localhost:8000/health

# Get API documentation
curl http://localhost:8000/docs
```

### Manual API Testing
```bash
# Test file upload
curl -X POST "http://localhost:8000/api/upload/source" \
  -F "files=@test_file.py"

# Get technology options
curl http://localhost:8000/api/technologies
```

## System Utilities (Linux)

### File Operations
```bash
# List files
ls -la

# Find Python files
find . -name "*.py" -type f

# Search in files
grep -r "pattern" src/

# Check disk space
df -h
```

### Process Management
```bash
# Find running Python processes
ps aux | grep python

# Kill process by PID
kill <pid>

# Check port usage
netstat -tulpn | grep 8000
```

### Git Operations
```bash
# Check status
git status

# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git add .
git commit -m "descriptive message"

# Push changes
git push origin feature/new-feature
```

## Docker Commands (If Using Containers)

```bash
# Build development image
docker build -t migration-validator:dev -f Dockerfile.dev .

# Run development container
docker run -p 8000:8000 -v $(pwd):/app migration-validator:dev

# Build production image
docker build -t migration-validator:latest .

# Run production container
docker run -p 8000:8000 migration-validator:latest
```