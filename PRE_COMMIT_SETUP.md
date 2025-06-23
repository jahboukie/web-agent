# 🚀 WebAgent Pre-Commit Testing Pipeline Setup

This document provides complete setup instructions for a robust pre-commit testing pipeline that ensures **100% green commits** by automatically checking code quality, running tests, and preventing secrets from being committed.

## 📋 Overview

The pre-commit framework will automatically run these checks **in order** when you run `git commit`:

1. **Code Formatting & Linting**
   - Python: Black (formatting) + Ruff (linting) + MyPy (type checking)
   - JavaScript/TypeScript: Prettier (formatting) + ESLint (linting)
   - General: Remove trailing whitespace, check file formats

2. **Security & Secrets Detection**
   - Detect-secrets: Scan for API keys, passwords, tokens
   - Bandit: Python security vulnerability scanning
   - Check for large files and merge conflicts

3. **Testing Suite**
   - Unit Tests: pytest (Python backend)
   - Frontend Tests: npm test (React/TypeScript)
   - E2E Tests: Critical end-to-end validation

## 🛠 Installation Steps

### 1. Install Dependencies

```bash
# Install Python dependencies (if using Poetry)
poetry install --with dev

# OR install with pip
pip install pre-commit black isort ruff mypy bandit detect-secrets pytest

# Install Node.js dependencies for frontend
cd aura
npm install
cd ..
```

### 2. Install Pre-Commit Hooks

```bash
# Install pre-commit framework into your git repository
pre-commit install

# Install pre-push hooks (optional, for additional checks)
pre-commit install --hook-type pre-push

# Test the installation
pre-commit --version
```

### 3. Initialize Secrets Baseline

```bash
# Create initial secrets baseline (allows existing "secrets" like config examples)
detect-secrets scan --baseline .secrets.baseline

# If you have existing secrets that are OK (like config examples), run:
detect-secrets audit .secrets.baseline
```

### 4. One-Time Setup Commands

```bash
# Run pre-commit on all files (first time setup)
pre-commit run --all-files

# This will:
# - Format all Python files with Black
# - Lint all files with Ruff and ESLint
# - Fix any auto-fixable issues
# - Show you any manual fixes needed
```

## 📁 Files Created

The setup includes these configuration files:

- `.pre-commit-config.yaml` - Main pre-commit configuration
- `.secrets.baseline` - Allowed "secrets" baseline for detect-secrets
- `pyproject.toml` - Updated with tool configurations (Black, Ruff, MyPy, etc.)

## 🔄 How Developers Use This

### Normal Workflow

```bash
# 1. Make your code changes
vim app/api/endpoints/auth.py

# 2. Add files to staging
git add .

# 3. Commit (pre-commit runs automatically)
git commit -m "feat: add user authentication endpoint"

# If pre-commit passes ✅
# Your commit succeeds and code is pushed with confidence!

# If pre-commit fails ❌
# Fix the issues shown and try again
git add .  # Add the fixes
git commit -m "feat: add user authentication endpoint"
```

### What Happens During `git commit`:

1. **Formatting (Auto-fix)** 🔧
   ```
   black...........................(no files to check)Skipped
   prettier........................Fixed
   - Fixed 3 files (automatically added to commit)
   ```

2. **Linting (Must pass)** 🔍
   ```
   ruff............................Passed
   eslint..........................Passed
   mypy............................Passed
   ```

3. **Security (Must pass)** 🔒
   ```
   detect-secrets..................Passed
   bandit..........................Passed
   ```

4. **Testing (Must pass)** 🧪
   ```
   pytest..........................Passed
   frontend-tests..................Passed
   e2e-critical....................Passed
   ```

### Emergency Bypass (Use Sparingly!)

If you absolutely need to commit without running pre-commit hooks:

```bash
# Skip ALL pre-commit hooks (emergency only!)
git commit -m "emergency fix" --no-verify

# Skip specific hook types
SKIP=pytest git commit -m "docs: update README"
SKIP=ruff,mypy git commit -m "wip: work in progress"
```

**⚠️ Warning:** Bypassed commits may break the build pipeline!

## 🛠 Customization Options

### Skip Slow Tests Locally

```bash
# Skip E2E tests during development (faster commits)
SKIP=e2e-critical git commit -m "feat: quick iteration"

# Only run formatting and linting
SKIP=pytest,frontend-tests,e2e-critical git commit -m "docs: update"
```

### Update Hook Versions

```bash
# Update all hook versions to latest
pre-commit autoupdate

# Update specific hook
pre-commit autoupdate --repo https://github.com/psf/black
```

### Disable Specific Hooks

Edit `.pre-commit-config.yaml` and comment out unwanted hooks:

```yaml
# - repo: https://github.com/pre-commit/mirrors-mypy
#   rev: v1.9.0
#   hooks:
#     - id: mypy  # Disabled type checking
```

## 🎯 Test Commands Reference

### Manual Testing Commands

```bash
# Run specific hook manually
pre-commit run black --all-files
pre-commit run ruff --all-files
pre-commit run pytest --all-files

# Run all hooks manually (without committing)
pre-commit run --all-files

# Test specific files
pre-commit run --files app/api/endpoints/auth.py

# Run only linting (skip tests)
pre-commit run --hook-stage manual black ruff eslint
```

### Project-Specific Test Commands

```bash
# Backend tests
pytest -v tests/

# Frontend tests  
cd aura && npm test -- --watchAll=false

# E2E tests
python tests/run_critical_e2e_tests.py

# Full validation
python validate_end_to_end.py
```

## 🚨 Troubleshooting

### Common Issues

1. **Hook installation failed**
   ```bash
   # Reinstall hooks
   pre-commit uninstall
   pre-commit install
   ```

2. **Dependencies missing**
   ```bash
   # Reinstall environment
   poetry install --with dev
   # OR
   pip install -r requirements.txt
   ```

3. **Secrets detected**
   ```bash
   # Review detected secrets
   detect-secrets audit .secrets.baseline
   
   # Add false positive to baseline
   detect-secrets scan --baseline .secrets.baseline
   ```

4. **Type checking errors**
   ```bash
   # Install missing type stubs
   mypy --install-types
   ```

### Performance Optimization

```bash
# Cache tool installations for faster subsequent runs
export PRE_COMMIT_HOME=~/.cache/pre-commit

# Run hooks in parallel (if supported)
pre-commit run --all-files --parallel
```

## ✅ Verification

After setup, verify everything works:

```bash
# 1. Make a small change
echo "# Test" >> README.md

# 2. Try to commit
git add README.md
git commit -m "test: verify pre-commit setup"

# 3. You should see all hooks running and passing
# 4. If successful, your commit goes through
# 5. If any hook fails, fix the issues and try again
```

## 🎉 Success!

Your WebAgent project now has enterprise-grade commit quality checks! Every commit that passes this pipeline is guaranteed to:

- ✅ Follow consistent code style
- ✅ Pass all linting checks  
- ✅ Have no security vulnerabilities
- ✅ Pass all tests
- ✅ Contain no accidentally committed secrets

**Happy coding with confidence!** 🚀