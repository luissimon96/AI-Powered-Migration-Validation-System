# Developer Workflow - Direct Master Deployment

## Quick Start Guide

This project uses **direct master deployment** - every commit to master automatically deploys to production after passing quality gates.

### 🚀 Basic Workflow

```bash
# 1. Clone and setup
git clone <repository-url>
cd AI-Powered-Migration-Validation-System
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# 2. Make changes
# Edit your code...

# 3. Test locally
python run_tests.py --unit
ruff format src/ tests/
ruff check src/ tests/

# 4. Commit and deploy
git add .
git commit -m "feat: add new feature"
git push origin master  # 🚀 Triggers automatic deployment!
```

### ✅ Pre-commit Checklist

Before every commit to master:

```bash
# Format code
ruff format src/ tests/

# Check linting
ruff check src/ tests/

# Run tests
python run_tests.py --unit --integration

# Security check
bandit -r src/ --severity-level medium

# Verify everything passes
echo "✅ Ready to commit!"
```

### 📋 Commit Message Format

```
type(scope): description

Examples:
feat(auth): add JWT token validation
fix(api): resolve memory leak in analyzer
docs(deploy): update deployment guide
refactor(core): simplify validation logic
test(unit): add tests for new features
perf(db): optimize query performance
style(format): fix code formatting
chore(deps): update dependencies
```

### 🔄 Monitoring Your Deployment

After pushing to master:

1. **GitHub Actions**: Watch the CI pipeline at `https://github.com/<repo>/actions`
2. **Deployment Progress**: Monitor the pipeline stages:
   - 🔍 Code Quality (2-3 minutes)
   - 🛡️ Security Scan (3-5 minutes)
   - 🧪 Tests (5-10 minutes)
   - 🚀 Production Deployment (2-5 minutes)
3. **Health Check**: Verify at `https://api.migration-validator.com/health`

### 🚨 If Something Goes Wrong

#### Deployment Failed
```bash
# Check the GitHub Actions logs
# Fix the issue locally
# Commit the fix
git add .
git commit -m "fix: resolve deployment issue"
git push origin master  # New deployment attempt
```

#### Production Issue
```bash
# Quick rollback (if needed)
kubectl rollout undo deployment/migration-validator-app -n migration-validator-prod

# Or revert the commit
git revert HEAD
git push origin master  # Deploys the revert
```

### 🛠️ Development Commands

```bash
# Start development environment
docker-compose up -d

# Run specific test types
python run_tests.py --unit           # Unit tests only
python run_tests.py --integration    # Integration tests only
python run_tests.py --behavioral     # Browser tests
python run_tests.py --all           # All tests

# Code quality
ruff format src/ tests/              # Format code
ruff check src/ tests/               # Lint code
isort src/ tests/                    # Sort imports
mypy src/                           # Type checking

# Security
bandit -r src/                      # Security scan
safety check                       # Dependency vulnerabilities

# Manual deployment (if needed)
./scripts/deploy.sh development     # Local deployment
./scripts/deploy.sh production      # Production deployment
./scripts/verify-deployment.sh      # Verify deployment
```

### 📊 Quality Standards

- **Test Coverage**: Maintain > 80%
- **Code Quality**: Zero linting errors
- **Security**: No high-severity vulnerabilities
- **Performance**: API responses < 500ms
- **Documentation**: Update docs for new features

### 🔄 Dependency Updates

Dependabot automatically creates commits for dependency updates that deploy directly to master:

```
deps: bump fastapi from 0.104.0 to 0.104.1
deps-dev: bump pytest from 7.4.0 to 7.4.1
```

These are automatically deployed if they pass all quality gates.

### 📚 Useful Links

- **Production API**: https://api.migration-validator.com
- **Health Check**: https://api.migration-validator.com/health
- **Metrics**: https://api.migration-validator.com/metrics
- **GitHub Actions**: https://github.com/<repo>/actions
- **Documentation**: [docs/](docs/)

### 💡 Tips for Success

1. **Test Locally First**: Always run tests before pushing
2. **Small Commits**: Make focused, atomic commits
3. **Clear Messages**: Write descriptive commit messages
4. **Monitor Deployments**: Watch the pipeline after pushing
5. **Quick Fixes**: For issues, fix and push immediately
6. **Communication**: Coordinate with team for major changes

### 🚫 What NOT to Do

- ❌ Don't push broken code to master
- ❌ Don't push without running tests locally
- ❌ Don't ignore CI pipeline failures
- ❌ Don't make large, risky changes without coordination
- ❌ Don't commit secrets or sensitive data

### 🆘 Getting Help

- **Documentation**: Check [docs/](docs/) folder
- **Issues**: Create GitHub issues for bugs
- **Team Chat**: Use team communication channels
- **Logs**: Check GitHub Actions and application logs

---

**Remember**: Every commit to master goes directly to production. Quality and testing are your responsibility!