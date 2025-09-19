# Task Completion Guidelines

## When a Development Task is Completed

### 1. Code Quality Checks
Run these commands before considering a task complete:

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### 2. Testing Requirements
Ensure appropriate tests are written and passing:

```bash
# Run unit tests with coverage
pytest tests/unit/ -v --cov=src --cov-report=xml

# Run integration tests
pytest tests/integration/ -v

# Verify test coverage is above thresholds
# - Unit tests: >85% coverage
# - Integration tests: All critical paths covered
```

### 3. Documentation Updates
- Update docstrings for new/modified functions
- Update README.md if public API changes
- Add/update technical documentation in `docs/` if architectural changes
- Update this memory file if development processes change

### 4. Git Workflow
```bash
# Ensure clean working directory
git status

# Create descriptive commit message
git add .
git commit -m "feat: implement feature X with Y functionality

- Add new analyzer for Z technology
- Update models to support new validation scope
- Include comprehensive test coverage
- Update documentation"

# Push to feature branch
git push origin feature/feature-name
```

### 5. Performance Verification
For performance-critical changes:

```bash
# Run performance tests
pytest tests/performance/ -v -m performance

# Monitor memory usage
# Check execution time benchmarks
```

### 6. API Testing (for API changes)
```bash
# Start development server
uvicorn src.api.routes:app --reload

# Test key endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/technologies

# Verify OpenAPI documentation
# Visit http://localhost:8000/docs
```

### 7. Security Considerations
- No hardcoded credentials or secrets
- Input validation for all user inputs
- Proper error handling without information disclosure
- File upload security (type validation, size limits)

### 8. Deployment Readiness
- Configuration externalized (no hardcoded values)
- Environment variables properly used
- Docker compatibility maintained
- Dependencies properly specified

## Definition of Done Checklist

### For New Features
- [ ] Code implemented and follows style guidelines
- [ ] Unit tests written with >85% coverage
- [ ] Integration tests for critical paths
- [ ] Documentation updated (docstrings, README, technical docs)
- [ ] API endpoints tested manually
- [ ] Security review completed
- [ ] Performance impact assessed
- [ ] Code review completed
- [ ] All CI/CD checks pass

### For Bug Fixes
- [ ] Root cause identified and documented
- [ ] Fix implemented with minimal scope
- [ ] Regression test added
- [ ] Existing tests still pass
- [ ] No new security vulnerabilities
- [ ] Code review completed

### For Refactoring
- [ ] Functionality preserved (all tests pass)
- [ ] Code quality improved (complexity, readability)
- [ ] Performance impact neutral or positive
- [ ] Documentation updated if needed
- [ ] No breaking API changes (or properly versioned)

## Quality Gates

### Automated Checks (Required)
- All tests pass (`pytest tests/` returns 0)
- Code formatting (`black --check src/ tests/`)
- Linting passes (`flake8 src/ tests/`)
- Type checking passes (`mypy src/`)
- Security scan clean (`bandit -r src/`)
- Test coverage above threshold

### Manual Review (Required)
- Code review by another developer
- Architecture review for significant changes
- Security review for user-facing features
- Performance review for critical path changes

## Rollback Plan
Always have a rollback plan for production deployments:
- Previous working version identified
- Database migration rollback scripts (if applicable)
- Configuration rollback procedure
- Monitoring and alerting in place