This is a monorepo for Python and JavaScript tools and utilities for working with localization files,
primarily built for internal use at Mozilla.

To get a new development environment set up,
clone this repo and run the following commands in the repo root:

```
uv sync --dev --all-packages --all-extras
uv run pytest

npm install
npm test
```

Formatting and styling uses Ruff & Mypy for Python,
and ESLint & Prettier for JavaScript.
