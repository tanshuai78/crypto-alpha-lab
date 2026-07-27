.PHONY: install test test-verbose fmt lint smoke check

install:
	uv sync --all-extras

test:
	PYTHONPATH=src uv run pytest -q

test-verbose:
	PYTHONPATH=src uv run pytest -v

lint:
	uv run ruff check src tests

fmt:
	uv run ruff format src tests

check: lint test
	@echo "All checks passed."

smoke:
	PYTHONPATH=src uv run python -m compileall src -q
	PYTHONPATH=src uv run python -c "from configs.base import *; print('configs OK')"
	PYTHONPATH=src uv run python -c "from risk.limits import RiskLimits; r = RiskLimits(); assert r.live_trading_enabled is False; print('risk gate OK')"
