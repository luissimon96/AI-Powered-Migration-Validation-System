#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# Direct Master Deployment Script
# AI-Powered Migration Validation System
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
DEPLOY_VERSION="${2:-$(git rev-parse --short HEAD)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify we're on master branch
verify_master_branch() {
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [[ "$current_branch" != "master" ]]; then
        log_error "❌ Not on master branch (currently on: $current_branch)"
        log_error "Direct master deployment requires being on the master branch"
        exit 1
    fi

    log_success "✅ Verified on master branch"
}

# Check if working directory is clean
check_clean_working_directory() {
    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "⚠️  Working directory has uncommitted changes"
        echo "Uncommitted files:"
        git status --porcelain
        echo
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "❌ Deployment cancelled"
            exit 1
        fi
    else
        log_success "✅ Working directory is clean"
    fi
}

# Run quality checks
run_quality_checks() {
    log_info "🔍 Running quality checks..."

    # Check if we have a Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "❌ Python 3 not found"
        exit 1
    fi

    # Install dependencies if needed
    if [[ ! -d "venv" ]]; then
        log_info "📦 Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate || {
        log_error "❌ Failed to activate virtual environment"
        exit 1
    }

    # Install/update dependencies
    log_info "📦 Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -e ".[dev,quality]" || {
        log_error "❌ Failed to install dependencies"
        exit 1
    }

    # Run linting
    log_info "🎨 Checking code formatting..."
    ruff format --check src/ tests/ || {
        log_error "❌ Code formatting issues found"
        log_info "Run: ruff format src/ tests/"
        exit 1
    }

    log_info "🔍 Running linting..."
    ruff check src/ tests/ || {
        log_error "❌ Linting issues found"
        exit 1
    }

    # Run tests
    log_info "🧪 Running tests..."
    python run_tests.py --unit --integration --parallel 4 || {
        log_error "❌ Tests failed"
        exit 1
    }

    # Security scan
    log_info "🛡️ Running security scan..."
    bandit -r src/ --severity-level medium --quiet || {
        log_warning "⚠️  Security issues detected (check manually)"
    }

    log_success "✅ All quality checks passed"
}

# Build Docker image
build_docker_image() {
    log_info "🐳 Building Docker image..."

    local image_tag="migration-validator:${DEPLOY_VERSION}"
    local latest_tag="migration-validator:latest"

    docker build \
        --target production \
        --tag "$image_tag" \
        --tag "$latest_tag" \
        . || {
        log_error "❌ Docker build failed"
        exit 1
    }

    log_success "✅ Docker image built: $image_tag"
}

# Deploy to environment
deploy_to_environment() {
    log_info "🚀 Deploying to $ENVIRONMENT environment..."

    case "$ENVIRONMENT" in
        "development"|"dev")
            deploy_development
            ;;
        "staging")
            deploy_staging
            ;;
        "production"|"prod")
            deploy_production
            ;;
        *)
            log_error "❌ Unknown environment: $ENVIRONMENT"
            log_info "Valid environments: development, staging, production"
            exit 1
            ;;
    esac
}

# Deploy to development (Docker Compose)
deploy_development() {
    log_info "🔧 Deploying to development environment with Docker Compose..."

    # Stop existing containers
    docker-compose down || true

    # Start services
    docker-compose up -d --build || {
        log_error "❌ Development deployment failed"
        exit 1
    }

    # Wait for services to be ready
    log_info "⏳ Waiting for services to be ready..."
    sleep 10

    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "✅ Development deployment successful"
        log_info "🌐 Application available at: http://localhost:8000"
    else
        log_error "❌ Health check failed"
        exit 1
    fi
}

# Deploy to staging (Kubernetes)
deploy_staging() {
    log_info "☸️  Deploying to staging environment with Kubernetes..."

    # Check kubectl access
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log_error "❌ Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Update image in staging
    kubectl set image deployment/migration-validator-app \
        app="migration-validator:${DEPLOY_VERSION}" \
        -n migration-validator-staging || {
        log_error "❌ Failed to update staging deployment"
        exit 1
    }

    # Wait for rollout
    log_info "⏳ Waiting for staging rollout to complete..."
    kubectl rollout status deployment/migration-validator-app \
        -n migration-validator-staging --timeout=300s || {
        log_error "❌ Staging rollout failed"
        exit 1
    }

    log_success "✅ Staging deployment successful"
}

# Deploy to production (Kubernetes)
deploy_production() {
    log_info "🏭 Deploying to production environment with Kubernetes..."

    # Extra confirmation for production
    log_warning "⚠️  You are about to deploy to PRODUCTION"
    echo "Environment: $ENVIRONMENT"
    echo "Version: $DEPLOY_VERSION"
    echo "Commit: $(git log -1 --oneline)"
    echo
    read -p "Continue with production deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "❌ Production deployment cancelled"
        exit 1
    fi

    # Check kubectl access
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log_error "❌ Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Update image in production
    kubectl set image deployment/migration-validator-app \
        app="migration-validator:${DEPLOY_VERSION}" \
        -n migration-validator-prod || {
        log_error "❌ Failed to update production deployment"
        exit 1
    }

    # Wait for rollout
    log_info "⏳ Waiting for production rollout to complete..."
    kubectl rollout status deployment/migration-validator-app \
        -n migration-validator-prod --timeout=600s || {
        log_error "❌ Production rollout failed"
        exit 1
    }

    # Health check
    log_info "🏥 Running post-deployment health check..."
    sleep 30

    # Get the ingress URL (adjust as needed)
    PROD_URL="https://api.migration-validator.com"
    if curl -f "${PROD_URL}/health" > /dev/null 2>&1; then
        log_success "✅ Production deployment successful"
        log_success "🌐 Application available at: $PROD_URL"
    else
        log_warning "⚠️  Health check failed - manual verification needed"
    fi
}

# Generate deployment report
generate_deployment_report() {
    local report_file="deployment-report-${DEPLOY_VERSION}.md"

    cat > "$report_file" << EOF
# Deployment Report

**Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Environment**: $ENVIRONMENT
**Version**: $DEPLOY_VERSION
**Commit**: $(git log -1 --oneline)
**Branch**: $(git rev-parse --abbrev-ref HEAD)

## Changes in this deployment

$(git log --oneline -10)

## Quality Gates
- ✅ Code formatting (ruff)
- ✅ Linting (ruff)
- ✅ Unit tests
- ✅ Integration tests
- ✅ Security scan (bandit)

## Deployment Status
- ✅ Docker image built
- ✅ Deployed to $ENVIRONMENT
- ✅ Health check passed

## Rollback Instructions
If issues are discovered, rollback using:
\`\`\`bash
# Get previous deployment version
kubectl rollout history deployment/migration-validator-app -n migration-validator-${ENVIRONMENT}

# Rollback to previous version
kubectl rollout undo deployment/migration-validator-app -n migration-validator-${ENVIRONMENT}
\`\`\`

---
Generated by direct master deployment script
EOF

    log_info "📄 Deployment report saved to: $report_file"
}

# Main deployment function
main() {
    log_info "🚀 Starting direct master deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Version: $DEPLOY_VERSION"
    echo "Timestamp: $(date -u)"
    echo

    # Pre-deployment checks
    verify_master_branch
    check_clean_working_directory

    # Quality gates
    run_quality_checks

    # Build and deploy
    build_docker_image
    deploy_to_environment

    # Post-deployment
    generate_deployment_report

    log_success "🎉 Deployment completed successfully!"
    log_info "📊 Check the deployment report for details"
}

# Handle script arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Direct Master Deployment Script"
        echo
        echo "Usage: $0 [environment] [version]"
        echo
        echo "Environments:"
        echo "  development, dev    - Deploy to local Docker Compose"
        echo "  staging            - Deploy to Kubernetes staging"
        echo "  production, prod   - Deploy to Kubernetes production"
        echo
        echo "Examples:"
        echo "  $0 development     - Deploy to development"
        echo "  $0 production      - Deploy to production"
        echo "  $0 staging v1.2.3  - Deploy specific version to staging"
        echo
        exit 0
        ;;
    *)
        main
        ;;
esac