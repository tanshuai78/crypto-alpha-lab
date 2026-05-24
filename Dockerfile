FROM ghcr.io/astral-sh/uv:python3.11-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files to optimize build caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy the rest of the application code
COPY . .

# Install the project itself
RUN uv sync --frozen

# Set PYTHONPATH to search in src/
ENV PYTHONPATH=src

# Default daemon command
CMD ["uv", "run", "python", "scripts/run_extreme_funding_watchlist.py", "--forever", "--data-root", "data"]
