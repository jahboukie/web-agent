#!/bin/bash

# WebAgent E2E Test Execution Script
# Comprehensive test runner for local development and CI/CD

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_ROOT/tests/reports"
LOGS_DIR="$PROJECT_ROOT/logs"

# Default values
TEST_CATEGORIES=""
ENVIRONMENT="local"
PARALLEL=false
CLEANUP=true
VERBOSE=false
DOCKER_COMPOSE_FILE="docker-compose.yml"
FRONTEND_BUILD=true
PERFORMANCE_TESTS=false

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

# Help function
show_help() {
    cat << EOF
WebAgent E2E Test Runner

Usage: $0 [OPTIONS]

OPTIONS:
    -c, --categories CATEGORIES    Comma-separated test categories to run
                                  (core_functionality, subscription_billing,
                                   enterprise_security, authentication_security,
                                   performance_load)
    -e, --environment ENV         Test environment (local, staging, production)
    -p, --parallel               Run tests in parallel
    --no-cleanup                 Skip cleanup after tests
    --no-frontend-build          Skip frontend build
    --performance                Include performance tests
    -v, --verbose                Verbose output
    -h, --help                   Show this help message

EXAMPLES:
    # Run all critical tests
    $0 -c core_functionality,enterprise_security

    # Run full test suite with performance tests
    $0 --performance

    # Run tests in parallel with verbose output
    $0 -p -v

    # Run specific category without cleanup
    $0 -c subscription_billing --no-cleanup

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--categories)
            TEST_CATEGORIES="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --no-frontend-build)
            FRONTEND_BUILD=false
            shift
            ;;
        --performance)
            PERFORMANCE_TESTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Create necessary directories
mkdir -p "$REPORTS_DIR" "$LOGS_DIR"

# Cleanup function
cleanup() {
    if [ "$CLEANUP" = true ]; then
        log_info "Cleaning up test environment..."

        # Stop Docker services
        cd "$PROJECT_ROOT"
        docker-compose -f "$DOCKER_COMPOSE_FILE" down --volumes --remove-orphans 2>/dev/null || true

        # Kill any remaining processes
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        pkill -f "npm run dev" 2>/dev/null || true
        pkill -f "npm run preview" 2>/dev/null || true

        log_success "Cleanup completed"
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required but not installed"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry is required but not installed"
        exit 1
    fi

    log_success "All prerequisites are available"
}

# Setup test environment
setup_environment() {
    log_info "Setting up test environment..."

    cd "$PROJECT_ROOT"

    # Start supporting services
    log_info "Starting PostgreSQL and Redis..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres redis

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U postgres; do sleep 2; done' || {
        log_error "PostgreSQL failed to start"
        exit 1
    }

    timeout 60 bash -c 'until docker-compose exec -T redis redis-cli ping | grep -q PONG; do sleep 2; done' || {
        log_error "Redis failed to start"
        exit 1
    }

    # Install Python dependencies
    log_info "Installing Python dependencies..."
    poetry install --with dev

    # Install Playwright browsers
    log_info "Installing Playwright browsers..."
    poetry run playwright install --with-deps chromium firefox webkit

    # Run database migrations
    log_info "Running database migrations..."
    poetry run alembic upgrade head

    # Install frontend dependencies and build
    if [ "$FRONTEND_BUILD" = true ]; then
        log_info "Installing frontend dependencies..."
        cd "$PROJECT_ROOT/aura"
        npm ci

        log_info "Building frontend..."
        npm run build
        cd "$PROJECT_ROOT"
    fi

    log_success "Test environment setup completed"
}

# Start application services
start_services() {
    log_info "Starting application services..."

    cd "$PROJECT_ROOT"

    # Start backend server
    log_info "Starting backend server..."
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOGS_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!

    # Wait for backend to be ready
    log_info "Waiting for backend to be ready..."
    timeout 60 bash -c 'until curl -f http://localhost:8000/health &>/dev/null; do sleep 2; done' || {
        log_error "Backend failed to start"
        cat "$LOGS_DIR/backend.log"
        exit 1
    }

    # Start frontend server
    if [ "$FRONTEND_BUILD" = true ]; then
        log_info "Starting frontend server..."
        cd "$PROJECT_ROOT/aura"
        npm run preview -- --port 3000 --host 0.0.0.0 > "$LOGS_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!

        # Wait for frontend to be ready
        log_info "Waiting for frontend to be ready..."
        timeout 60 bash -c 'until curl -f http://localhost:3000 &>/dev/null; do sleep 2; done' || {
            log_error "Frontend failed to start"
            cat "$LOGS_DIR/frontend.log"
            exit 1
        }
        cd "$PROJECT_ROOT"
    fi

    log_success "Application services started successfully"
}

# Run E2E tests
run_tests() {
    log_info "Running E2E tests..."

    cd "$PROJECT_ROOT"

    # Prepare test command
    TEST_CMD="poetry run python tests/e2e_test_runner.py"

    # Add categories if specified
    if [ -n "$TEST_CATEGORIES" ]; then
        TEST_CMD="$TEST_CMD --categories $TEST_CATEGORIES"
    fi

    # Add performance tests if requested
    if [ "$PERFORMANCE_TESTS" = true ]; then
        if [ -n "$TEST_CATEGORIES" ]; then
            TEST_CMD="$TEST_CMD,performance_load"
        else
            TEST_CMD="$TEST_CMD --categories performance_load"
        fi
    fi

    # Set environment variables
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/webagent"
    export ASYNC_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webagent"
    export REDIS_URL="redis://localhost:6379/15"
    export API_BASE_URL="http://localhost:8000"
    export FRONTEND_URL="http://localhost:3000"
    export SECRET_KEY="test-secret-key-for-e2e-testing-only"
    export DEBUG="true"
    export ENVIRONMENT="test"

    # Run tests with appropriate options
    if [ "$VERBOSE" = true ]; then
        TEST_CMD="$TEST_CMD --verbose"
    fi

    if [ "$PARALLEL" = true ]; then
        TEST_CMD="$TEST_CMD --parallel"
    fi

    log_info "Executing: $TEST_CMD"

    # Execute tests
    if eval "$TEST_CMD"; then
        log_success "E2E tests completed successfully"
        return 0
    else
        log_error "E2E tests failed"
        return 1
    fi
}

# Generate test report summary
generate_summary() {
    log_info "Generating test summary..."

    # Find the latest test report
    LATEST_REPORT=$(find "$REPORTS_DIR" -name "e2e_test_report_*.json" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

    if [ -n "$LATEST_REPORT" ] && [ -f "$LATEST_REPORT" ]; then
        log_info "Test report available at: $LATEST_REPORT"

        # Extract key metrics using jq if available
        if command -v jq &> /dev/null; then
            echo ""
            echo "=== TEST EXECUTION SUMMARY ==="
            jq -r '
                "Overall Status: " + (if .overall_success then "PASS" else "FAIL" end) +
                "\nTotal Duration: " + .execution_summary.total_duration_formatted +
                "\nCategories: " + (.category_metrics.successful_categories | tostring) + "/" + (.category_metrics.total_categories | tostring) + " passed" +
                "\nTests: " + (.test_metrics.passed_tests | tostring) + "/" + (.test_metrics.total_tests | tostring) + " passed" +
                "\nSuccess Rate: " + ((.test_metrics.test_success_rate * 100) | floor | tostring) + "%"
            ' "$LATEST_REPORT"
            echo "================================"
        fi

        # Open HTML report if available
        HTML_REPORT="${LATEST_REPORT%.json}.html"
        if [ -f "$HTML_REPORT" ]; then
            log_info "HTML report available at: $HTML_REPORT"

            # Try to open in browser (macOS/Linux)
            if command -v open &> /dev/null; then
                open "$HTML_REPORT" 2>/dev/null || true
            elif command -v xdg-open &> /dev/null; then
                xdg-open "$HTML_REPORT" 2>/dev/null || true
            fi
        fi
    else
        log_warning "No test report found"
    fi
}

# Main execution
main() {
    log_info "Starting WebAgent E2E Test Execution"
    log_info "Environment: $ENVIRONMENT"
    log_info "Test Categories: ${TEST_CATEGORIES:-all}"
    log_info "Parallel Execution: $PARALLEL"
    log_info "Performance Tests: $PERFORMANCE_TESTS"

    # Execute test pipeline
    check_prerequisites
    setup_environment
    start_services

    # Run tests and capture exit code
    if run_tests; then
        TEST_EXIT_CODE=0
        log_success "All tests completed successfully!"
    else
        TEST_EXIT_CODE=1
        log_error "Some tests failed!"
    fi

    # Generate summary regardless of test outcome
    generate_summary

    # Exit with test result code
    exit $TEST_EXIT_CODE
}

# Execute main function
main "$@"
