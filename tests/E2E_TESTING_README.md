# WebAgent E2E Testing Framework

## 🎯 Overview

This comprehensive E2E testing framework validates all critical functionality, security, and enterprise features of the WebAgent platform. Designed with SaaS best practices, security requirements, and multi-tenant considerations.

## 🏗️ Test Architecture

### Test Categories

#### ⚠️ Critical Path Tests
- **Reader → Planner → Actor** handoff validation
- Complex website parsing accuracy
- Error recovery and resilience
- Performance thresholds (< 2s parse, < 5s plan, < 30s execute)
- Concurrent execution (50+ simultaneous workflows)

#### 🔒 Security & Compliance Tests
- **RBAC/ABAC** permission boundaries across 5+ role combinations
- **Zero-knowledge encryption** with HSM integration
- **Tenant isolation** and cross-tenant access prevention
- **Session security** with fixation protection
- **Input validation** (XSS/SQLi prevention)
- **Audit log immutability** and tamper detection

#### 💰 Revenue-Critical Billing Tests
- **Feature gating** at 80%/100% usage limits
- **Subscription lifecycle** management
- **Prorated billing** calculations
- **Stripe integration** and webhook processing
- **Usage tracking** accuracy
- **Conversion tracking** and revenue attribution

#### ⚡ Performance & Scalability Tests
- **500+ concurrent agents** under peak load
- **HSM latency** at 100+ req/sec
- **Auto-scaling** threshold validation
- **Database performance** under load
- **Queue saturation** recovery

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
poetry install
poetry run playwright install

# Set up test database
createdb webagent_e2e_test
poetry run alembic upgrade head

# Start test services
docker-compose -f docker-compose.test.yml up -d
```

### Running Tests

#### Critical Path Tests (30 minutes)
```bash
python tests/run_critical_e2e_tests.py --suite critical_path
```

#### Security Tests (45 minutes)
```bash
python tests/run_critical_e2e_tests.py --suite security --verbose
```

#### Performance Tests (60 minutes)
```bash
python tests/run_critical_e2e_tests.py --suite performance --include-load
```

#### Complete Test Suite (120 minutes)
```bash
python tests/run_critical_e2e_tests.py --suite all --parallel --include-load
```

## 📊 Test Execution Metrics

### Success Criteria

| Test Suite | Required Success Rate | Timeout | Critical for Launch |
|------------|----------------------|---------|-------------------|
| Critical Path | 100% | 30 min | ✅ YES |
| Security | 100% | 45 min | ✅ YES |
| Performance | 90% | 60 min | ⚠️ PARTIAL |
| Billing | 100% | 30 min | ✅ YES |

### Performance Thresholds

| Component | P50 Latency | P95 Latency | P99 Latency | Error Rate |
|-----------|-------------|-------------|-------------|------------|
| Reader | < 2s | < 5s | < 8s | < 10% |
| Planner | < 5s | < 10s | < 15s | < 15% |
| Actor | < 15s | < 30s | < 60s | < 20% |
| HSM | < 25ms | < 100ms | < 200ms | < 1% |
| Database | < 10ms | < 100ms | < 500ms | < 2% |

## 🔧 Test Configuration

### Environment Configuration

```json
{
  "test_environment": {
    "database_url": "postgresql://webagent_test:password@localhost:5432/webagent_e2e_test",
    "redis_url": "redis://localhost:6379/15",
    "api_base_url": "http://localhost:8000",
    "frontend_url": "http://localhost:3000"
  },
  "test_execution": {
    "parallel_execution": true,
    "max_workers": 4,
    "timeout_seconds": 3600,
    "retry_failed_tests": true,
    "max_retries": 2
  }
}
```

### Test Data Management

```python
# Test users with different roles
TEST_USERS = {
    "admin": {"role": "system_admin", "tenant": "e2e-enterprise"},
    "manager": {"role": "tenant_admin", "tenant": "e2e-enterprise"},
    "user": {"role": "basic_user", "tenant": "e2e-basic"},
    "auditor": {"role": "security_manager", "tenant": "e2e-compliance"}
}

# Test websites for different complexity levels
TEST_WEBSITES = {
    "simple_form": {"complexity": "low", "timeout": 30},
    "spa_application": {"complexity": "high", "timeout": 60},
    "e_commerce": {"complexity": "high", "timeout": 90}
}
```

## 📁 Test Structure

```
tests/
├── e2e/
│   ├── test_agent_execution_critical.py      # Core workflow tests
│   ├── test_security_compliance_critical.py  # Security validation
│   ├── test_subscription_billing_critical.py # Revenue tests
│   └── test_performance_load_critical.py     # Performance tests
├── conftest.py                               # Test fixtures
├── e2e_config.json                          # Test configuration
├── e2e_comprehensive_runner.py              # Test orchestration
└── run_critical_e2e_tests.py               # Test execution
```

## 🏃‍♂️ CI/CD Integration

### GitHub Actions Workflow

```yaml
name: WebAgent Critical E2E Tests
on:
  push: [main, develop]
  pull_request: [main]
  schedule: ['0 2 * * *']  # Daily at 2 AM UTC

jobs:
  critical-path-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Run Critical Tests
        run: python tests/run_critical_e2e_tests.py --suite critical_path
```

### Test Execution Frequency

- **Pre-commit**: Critical path tests (15 minutes)
- **PR validation**: Critical + Security tests (60 minutes)
- **Daily**: Complete test suite (120 minutes)
- **Release**: Complete suite + Load tests (180 minutes)

## 📈 Monitoring & Reporting

### Test Metrics Dashboard

- **Test execution trends** (success rate over time)
- **Performance regression detection**
- **Flaky test identification**
- **Coverage analysis** by component

### Alerting

- **Slack notifications** for test failures
- **Email reports** for daily test results
- **PagerDuty integration** for critical failures

## 🔍 Test Development Guidelines

### Writing New Tests

1. **Follow naming convention**: `test_[component]_[scenario]_[expected_outcome]`
2. **Add appropriate markers**: `@pytest.mark.critical`, `@pytest.mark.security`
3. **Include performance assertions**: Response time and error rate thresholds
4. **Document test purpose**: Clear docstring explaining what's being validated

### Example Test Structure

```python
@pytest.mark.asyncio
@pytest.mark.critical
async def test_reader_parser_complex_spa(self, test_db, test_users_db):
    """
    ⚠️ CRITICAL: Test Reader component with complex SPA.
    
    Validates parsing accuracy and performance for dynamic content.
    """
    # Arrange
    user = test_users_db["user"]
    url = "https://complex-spa-example.com"
    
    # Act
    start_time = time.time()
    result = await web_parser_service.parse_webpage_async(
        test_db, None, url, {"dynamic_content": True}
    )
    duration = time.time() - start_time
    
    # Assert
    assert result.success, "Parse should succeed"
    assert duration < 5.0, f"Parse took {duration:.2f}s, expected < 5s"
    assert len(result.interactive_elements) >= 5
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database connection errors**
   ```bash
   # Reset test database
   dropdb webagent_e2e_test
   createdb webagent_e2e_test
   poetry run alembic upgrade head
   ```

2. **Browser automation failures**
   ```bash
   # Reinstall browsers
   poetry run playwright install --force
   ```

3. **Port conflicts**
   ```bash
   # Check for conflicting processes
   lsof -i :8000
   lsof -i :3000
   ```

### Debug Mode

```bash
# Run with verbose output and screenshots
python tests/run_critical_e2e_tests.py \
  --suite critical_path \
  --verbose \
  --generate-report
```

## 📊 Test Reports

### Artifacts Generated

- **HTML Reports**: Visual test results with screenshots
- **JSON Reports**: Machine-readable test data
- **JUnit XML**: CI/CD integration format
- **Performance Metrics**: Response times and throughput
- **Security Scan Results**: Vulnerability assessments

### Report Locations

```
tests/artifacts/
├── critical_e2e_20240620_143022/
│   ├── report.html
│   ├── report.json
│   ├── junit.xml
│   ├── screenshots/
│   └── videos/
└── performance_metrics.json
```

## 🎯 Success Metrics

### Key Performance Indicators

- **False positive rate**: < 2%
- **Critical defect escape rate**: 0%
- **Test coverage**: 95%+ of user journeys
- **Mean time to test failure detection**: < 5 minutes

### Quality Gates

- ✅ All critical path tests must pass
- ✅ Security tests must have 100% success rate
- ✅ Performance tests must meet latency thresholds
- ✅ Billing tests must validate revenue-critical flows

## 🔗 Related Documentation

- [WebAgent Architecture Overview](../docs/architecture/README.md)
- [Security Implementation Guide](../SECURITY.md)
- [Deployment Guide](../docs/deployment/README.md)
- [API Documentation](../docs/api/README.md)

---

**Contact**: For questions about the E2E testing framework, reach out to the QA team or create an issue in the repository.