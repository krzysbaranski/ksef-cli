# Contributing to KSeF CLI

Thank you for your interest in contributing to KSeF CLI! This document provides guidelines and instructions for contributing to this project.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip
- git

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/krzysbaranski/ksef-cli.git
   cd ksef-cli
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Install production dependencies
   pip install -e .
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=ksef_cli --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_models.py
```

### Run specific test
```bash
pytest tests/test_models.py::TestAdres::test_adres_valid
```

## Code Quality

### Formatting

We use **Black** for code formatting:
```bash
# Check formatting
black --check ksef_cli/ tests/

# Auto-format code
black ksef_cli/ tests/
```

### Import Sorting

We use **isort** for import sorting:
```bash
# Check imports
isort --check-only ksef_cli/ tests/

# Auto-sort imports
isort ksef_cli/ tests/
```

### Linting

We use **flake8** for linting:
```bash
flake8 ksef_cli/ tests/
```

### Type Checking

We use **mypy** for type checking:
```bash
mypy ksef_cli/ --ignore-missing-imports
```

### Security Scanning

Run security checks before submitting:
```bash
# Check code security
bandit -r ksef_cli/

# Check dependencies
safety check
```

## Coding Standards

1. **PEP 8 Compliance**: Follow PEP 8 style guide
2. **Line Length**: Maximum 100 characters
3. **Type Hints**: Use type hints for all functions
4. **Docstrings**: Add docstrings for all public classes and functions
5. **Tests**: Write tests for all new features and bug fixes

## Pull Request Process

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and ensure:
   - All tests pass
   - Code is formatted with Black
   - Imports are sorted with isort
   - No flake8 warnings
   - Code coverage is maintained (>80%)

3. **Run the complete check**:
   ```bash
   # Format code
   black ksef_cli/ tests/
   isort ksef_cli/ tests/
   
   # Run tests
   pytest --cov=ksef_cli --cov-report=term-missing --cov-fail-under=80
   
   # Lint
   flake8 ksef_cli/ tests/
   
   # Type check
   mypy ksef_cli/ --ignore-missing-imports
   
   # Security
   bandit -r ksef_cli/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add feature description"
   ```

5. **Push to your fork** and submit a pull request

6. **Wait for review** - maintainers will review your PR

## Commit Message Format

We follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add support for multiple currencies
fix: correct VAT calculation rounding
docs: update installation instructions
```

## Testing Guidelines

- Write unit tests for all new functions and classes
- Write integration tests for CLI commands
- Aim for >80% code coverage
- Test edge cases and error conditions
- Use fixtures from `conftest.py` when possible

## Documentation

- Update README.md if you add new features
- Add docstrings to all public APIs
- Update examples if behavior changes
- Keep CONTRIBUTING.md up to date

## Getting Help

If you have questions or need help:

1. Check existing issues and pull requests
2. Create a new issue with your question
3. Join discussions in existing issues

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help newcomers learn and grow

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
