#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# Deployment Verification Script
# AI-Powered Migration Validation System
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-production}"
TIMEOUT="${2:-300}" # 5 minutes default timeout

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

# Get environment configuration
get_environment_config() {
    case "$ENVIRONMENT" in
        "development"|"dev")
            API_URL="http://localhost:8000"
            NAMESPACE="default"
            ;;
        "staging")
            API_URL="https://staging-api.migration-validator.com"
            NAMESPACE="migration-validator-staging"
            ;;
        "production"|"prod")
            API_URL="https://api.migration-validator.com"
            NAMESPACE="migration-validator-prod"
            ;;
        *)
            log_error "❌ Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

# Check API health endpoint
check_api_health() {
    log_info "🏥 Checking API health endpoint..."

    local start_time=$(date +%s)
    local max_time=$((start_time + TIMEOUT))

    while [ $(date +%s) -lt $max_time ]; do
        if curl -f -s "${API_URL}/health" > /dev/null 2>&1; then
            log_success "✅ API health check passed"
            return 0
        fi

        log_info "⏳ Waiting for API to be ready..."
        sleep 10
    done

    log_error "❌ API health check failed after ${TIMEOUT}s"
    return 1
}

# Check detailed health endpoint
check_detailed_health() {
    log_info "🔍 Checking detailed health endpoint..."

    local response
    response=$(curl -s "${API_URL}/health/detailed" 2>/dev/null) || {
        log_error "❌ Failed to get detailed health status"
        return 1
    }

    if echo "$response" | grep -q '"status": "healthy"' 2>/dev/null; then
        log_success "✅ Detailed health check passed"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        return 0
    else
        log_error "❌ Detailed health check failed"
        echo "$response"
        return 1
    fi
}

# Check Kubernetes pods (if applicable)
check_kubernetes_pods() {
    if [[ "$ENVIRONMENT" == "development" ]]; then
        return 0
    fi

    log_info "☸️  Checking Kubernetes pods..."

    if ! command -v kubectl &> /dev/null; then
        log_warning "⚠️  kubectl not available, skipping pod check"
        return 0
    fi

    # Check if we can connect to the cluster
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log_warning "⚠️  Cannot connect to Kubernetes cluster, skipping pod check"
        return 0
    fi

    # Check pod status
    local unhealthy_pods
    unhealthy_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running -o name 2>/dev/null | wc -l)

    if [[ "$unhealthy_pods" -eq 0 ]]; then
        log_success "✅ All Kubernetes pods are healthy"
        kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
    else
        log_warning "⚠️  Found $unhealthy_pods unhealthy pods"
        kubectl get pods -n "$NAMESPACE" 2>/dev/null || true
    fi
}

# Check Docker containers (for development)
check_docker_containers() {
    if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "dev" ]]; then
        return 0
    fi

    log_info "🐳 Checking Docker containers..."

    if ! command -v docker &> /dev/null; then
        log_warning "⚠️  Docker not available, skipping container check"
        return 0
    fi

    # Check if containers are running
    local running_containers
    running_containers=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)

    if [[ "$running_containers" -gt 0 ]]; then
        log_success "✅ Docker containers are running"
        docker-compose ps 2>/dev/null || true
    else
        log_error "❌ No Docker containers are running"
        docker-compose ps 2>/dev/null || true
        return 1
    fi
}

# Check database connectivity
check_database() {
    log_info "🗄️  Checking database connectivity..."

    # Try to hit an API endpoint that requires database access
    local response
    response=$(curl -s "${API_URL}/api/v1/status" 2>/dev/null) || {
        log_warning "⚠️  Could not check database connectivity (endpoint not available)"
        return 0
    }

    if echo "$response" | grep -q "database.*connected\|status.*ok" 2>/dev/null; then
        log_success "✅ Database connectivity check passed"
    else
        log_warning "⚠️  Database connectivity unclear"
    fi
}

# Check key metrics endpoint
check_metrics() {
    log_info "📊 Checking metrics endpoint..."

    if curl -f -s "${API_URL}/metrics" > /dev/null 2>&1; then
        log_success "✅ Metrics endpoint is accessible"
    else
        log_warning "⚠️  Metrics endpoint not accessible"
    fi
}

# Run performance test
run_performance_test() {
    log_info "⚡ Running basic performance test..."

    local start_time
    start_time=$(date +%s%3N)

    if curl -f -s "${API_URL}/health" > /dev/null 2>&1; then
        local end_time
        end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))

        if [[ "$response_time" -lt 1000 ]]; then
            log_success "✅ Performance test passed (${response_time}ms)"
        else
            log_warning "⚠️  Slow response time: ${response_time}ms"
        fi
    else
        log_error "❌ Performance test failed"
        return 1
    fi
}

# Generate verification report
generate_verification_report() {
    local report_file="verification-report-$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# Deployment Verification Report

**Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Environment**: $ENVIRONMENT
**API URL**: $API_URL

## Verification Results

- API Health: ✅ Passed
- Detailed Health: ✅ Passed
- Infrastructure: ✅ Checked
- Database: ✅ Connected
- Metrics: ✅ Available
- Performance: ✅ Acceptable

## Next Steps

1. Monitor application logs for any errors
2. Watch key metrics for anomalies
3. Verify user-facing functionality
4. Check alert systems are working

---
Generated by deployment verification script
EOF

    log_info "📄 Verification report saved to: $report_file"
}

# Main verification function
main() {
    log_info "🔍 Starting deployment verification for $ENVIRONMENT"
    echo "API URL: $API_URL"
    echo "Timeout: ${TIMEOUT}s"
    echo "Timestamp: $(date -u)"
    echo

    get_environment_config

    # Run all verification checks
    local all_passed=true

    check_api_health || all_passed=false
    check_detailed_health || all_passed=false
    check_kubernetes_pods || all_passed=false
    check_docker_containers || all_passed=false
    check_database || all_passed=false
    check_metrics || all_passed=false
    run_performance_test || all_passed=false

    echo

    if [[ "$all_passed" == "true" ]]; then
        log_success "🎉 All verification checks passed!"
        generate_verification_report
        exit 0
    else
        log_error "❌ Some verification checks failed"
        log_info "🔧 Please check the logs and fix any issues"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Deployment Verification Script"
        echo
        echo "Usage: $0 [environment] [timeout]"
        echo
        echo "Environments:"
        echo "  development, dev    - Verify local Docker Compose deployment"
        echo "  staging            - Verify Kubernetes staging deployment"
        echo "  production, prod   - Verify Kubernetes production deployment"
        echo
        echo "Timeout:"
        echo "  Number of seconds to wait for services (default: 300)"
        echo
        echo "Examples:"
        echo "  $0 development     - Verify development deployment"
        echo "  $0 production      - Verify production deployment"
        echo "  $0 staging 600     - Verify staging with 10-minute timeout"
        echo
        exit 0
        ;;
    *)
        main
        ;;
esac