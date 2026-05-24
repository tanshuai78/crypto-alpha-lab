FROM python:3.11-slim

# Install system compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for super fast and cached package management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency definition files first (including README.md to satisfy hatchling metadata validation)
COPY pyproject.toml uv.lock README.md ./

# Install project dependencies into the system python environment
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the rest of the application code
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=src

# Run command
CMD ["python", "scripts/run_extreme_funding_watchlist.py", "--forever", "--data-root", "data"]
