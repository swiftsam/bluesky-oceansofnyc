# Contributing to Oceans of NYC

## Development Setup

### Install Development Dependencies

```bash
uv sync --extra dev
```

This installs:
- **ruff**: Fast Python linter and formatter (replaces Black, Flake8, isort)
- **mypy**: Static type checker
- **pre-commit**: Git hook framework

### Pre-commit Hooks

Pre-commit hooks automatically run linting and formatting checks before each commit.

**Install hooks:**
```bash
uv run pre-commit install
```

**Run manually on all files:**
```bash
uv run pre-commit run --all-files
```

**Run on staged files only:**
```bash
git add <files>
uv run pre-commit run
```

## Code Quality Tools

### Ruff (Linter & Formatter)

Ruff is an extremely fast Python linter and formatter that replaces multiple tools:
- Black (formatting)
- Flake8 (linting)
- isort (import sorting)
- pyupgrade (syntax modernization)
- And many more...

**Run ruff manually:**
```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

**Configuration:** See `[tool.ruff]` section in [pyproject.toml](pyproject.toml)

### Mypy (Type Checker)

Mypy performs static type checking to catch type-related bugs.

**Run mypy manually:**
```bash
uv run mypy .
```

**Configuration:** See `[tool.mypy]` section in [pyproject.toml](pyproject.toml)

**Note:** Type checking is configured with moderate strictness. You may see warnings about missing type annotations, which can be addressed incrementally.

## Workflow

1. Make your changes
2. Pre-commit hooks run automatically when you commit
3. If hooks fail, they'll auto-fix what they can
4. Review the changes and re-commit
5. If issues can't be auto-fixed, address them manually

## Common Issues

### Pre-commit Hook Failures

**Import order issues:** Ruff will auto-fix these.

**Unused arguments:** Either use the argument or prefix with `_` (e.g., `_plate`)

**Type errors:** Add proper type hints or fix type inconsistencies.

### Bypassing Hooks (Not Recommended)

Only in emergencies:
```bash
git commit --no-verify
```

## IDE Integration

### VS Code

Install the Ruff extension for real-time linting:
1. Install "Ruff" extension by Astral Software
2. Ruff will automatically use the [pyproject.toml](pyproject.toml) configuration

### PyCharm

1. Go to Settings → Tools → External Tools
2. Add Ruff as an external tool
3. Configure file watcher for automatic formatting
