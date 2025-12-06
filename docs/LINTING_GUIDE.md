# Code Quality & Linting

This project uses automated code formatting and linting to maintain consistent code quality.

## Tools

- **Black**: Code formatter (PEP 8 compliant)
- **Ruff**: Fast Python linter
- **isort**: Import sorting
- **pre-commit**: Git hooks framework

## Setup

The pre-commit hooks are already installed. To ensure they're active:

```bash
pre-commit install
```

## Usage

### Automatic (on every commit)

Pre-commit hooks automatically run when you commit:

```bash
git commit -m "Your message"
```

The hooks will:
1. Format code with Black (100-char line length)
2. Lint with Ruff and fix auto-fixable issues
3. Sort imports with isort
4. Clean up trailing whitespace and EOF markers

If hooks modify files, your commit will be aborted. Review the changes and re-commit:

```bash
git add .
git commit -m "Your message"
```

### Manual

Format all files in the repo:

```bash
# Black formatting
black wbs/ house_wbs/ manage.py

# Ruff linting
ruff check --fix wbs/ house_wbs/ manage.py

# isort imports
isort wbs/ house_wbs/ manage.py
```

Run all hooks on all files:

```bash
pre-commit run --all-files
```

## Configuration

- **pyproject.toml**: Black, Ruff, and isort settings
- **.pre-commit-config.yaml**: Pre-commit hooks configuration
- **.flake8**: Additional linting settings

## Django-specific Rules

The configuration includes Django-aware linting (DJ prefix). Common rules:

- `DJ001`: Avoid `Model.objects.get()` without error handling
- `DJ003`: Use `settings.AUTH_USER_MODEL` instead of hardcoding User model

For more info: [Ruff Django rules](https://docs.astral.sh/ruff/rules/#django-dj)

## Tips

1. **IDE Integration**: Most editors (VS Code, PyCharm) support Black and Ruff. Install extensions for real-time feedback.
2. **Exceptions**: Use `# noqa: E501` to ignore specific lines (sparingly).
3. **Git Bypass**: To skip pre-commit hooks (not recommended): `git commit --no-verify`

## Troubleshooting

If pre-commit installation fails, try:

```bash
pip install pre-commit
pre-commit install
```

If hooks timeout, increase the timeout in `.pre-commit-config.yaml`.
