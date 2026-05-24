FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any library needs compilation (e.g. pandas/pyarrow pre-built wheels might need it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY pyproject.toml ./

# Install project dependencies directly via pip (pip supports pyproject.toml out of the box in python 3.11)
RUN pip install --no-cache-dir .

# Copy the rest of the application code
COPY . .

# Install the application itself in editable mode
RUN pip install --no-cache-dir -e .

# Set PYTHONPATH
ENV PYTHONPATH=src

# Default daemon command
CMD ["python", "scripts/run_extreme_funding_watchlist.py", "--forever", "--data-root", "data"]
