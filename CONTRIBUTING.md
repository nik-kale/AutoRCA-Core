# Contributing to AutoRCA-Core

Thank you for your interest in contributing to AutoRCA-Core! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- pip

### Setting Up Your Development Environment

1. **Fork and clone the repository**

```bash
git clone https://github.com/nik-kale/AutoRCA-Core.git
cd AutoRCA-Core
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Verify installation**

```bash
autorca --help
pytest
```

## Development Workflow

### Creating a Feature Branch

```bash
git checkout -b <type>/<short-description>
```

Branch types:
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `perf/` - Performance improvements
- `test/` - Test additions/updates
- `chore/` - Maintenance tasks

### Making Changes

1. **Write clean, well-documented code**
   - Follow PEP 8 style guidelines
   - Add docstrings to functions and classes
   - Comment complex logic

2. **Add tests**
   - Unit tests for new functionality
   - Integration tests for complex features
   - Maintain or improve test coverage

3. **Run quality checks**

```bash
# Format code
black autorca_core

# Check linting
ruff check autorca_core

# Run type checking
mypy autorca_core

# Run tests
pytest --cov=autorca_core
```

### Committing Changes

Use conventional commit messages:

```
<type>: <description>

[optional body]
```

Examples:
- `feat: add Anthropic Claude LLM integration`
- `fix: resolve glob pattern bug in file loading`
- `docs: update README with installation instructions`

### Submitting a Pull Request

1. **Push your branch**

```bash
git push origin <type>/<short-description>
```

2. **Create a Pull Request**
   - Use the PR template provided
   - Fill out all sections completely
   - Link related issues
   - Ensure all CI checks pass

3. **Address review feedback**
   - Respond to all comments
   - Make requested changes
   - Re-request review when ready

## Code Quality Standards

### Style Guidelines

- **Line length**: 100 characters max
- **Imports**: Standard library → third-party → local, alphabetically sorted
- **Type hints**: Use where helpful, especially for public APIs
- **Docstrings**: Google-style format

### Testing Guidelines

- **Coverage**: Aim for >80% test coverage
- **Test naming**: `test_<function_name>_<scenario>`
- **Assertions**: Use descriptive messages
- **Fixtures**: Reuse common test data

### Documentation Guidelines

- **README**: Keep up-to-date with examples
- **Docstrings**: Explain purpose, args, returns, raises
- **Comments**: Explain "why", not "what"
- **Examples**: Provide working code samples

## Project Structure

```
AutoRCA-Core/
├── autorca_core/           # Main package
│   ├── cli/                # Command-line interface
│   ├── ingestion/          # Data loading
│   ├── model/              # Data models
│   ├── graph_engine/       # Graph construction
│   ├── reasoning/          # RCA logic
│   └── outputs/            # Report generation
├── tests/                  # Test suite
├── examples/               # Example data and scripts
└── docs/                   # Documentation
```

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/nik-kale/AutoRCA-Core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nik-kale/AutoRCA-Core/discussions)
- **Email**: nik@example.com

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AutoRCA-Core! 🚀

