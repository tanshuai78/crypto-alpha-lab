from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import TradeIntent
from .order_state_machine import IntentState


class ExecutionJournal:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS intents (
                    intent_id TEXT PRIMARY KEY,
                    strategy_type TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    leg_a_json TEXT NOT NULL,
                    leg_b_json TEXT NOT NULL,
                    target_base_qty REAL NOT NULL,
                    max_notional_usdt REAL NOT NULL,
                    close_only_on_rollback INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT NOT NULL,
                    order_id TEXT,
                    leg_name TEXT NOT NULL,
                    exchange_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    client_order_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reduce_only INTEGER NOT NULL,
                    post_only INTEGER NOT NULL,
                    raw_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT NOT NULL,
                    order_id TEXT,
                    filled_qty REAL NOT NULL,
                    avg_price REAL,
                    raw_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS state_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def record_intent(self, intent: TradeIntent) -> None:
        payload = asdict(intent)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO intents (
                    intent_id, strategy_type, execution_mode, status,
                    leg_a_json, leg_b_json, target_base_qty, max_notional_usdt,
                    close_only_on_rollback, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.intent_id,
                    intent.strategy_type,
                    intent.execution_mode,
                    intent.status,
                    json.dumps(payload["leg_a"]),
                    json.dumps(payload["leg_b"]),
                    intent.target_base_qty,
                    intent.max_notional_usdt,
                    int(intent.close_only_on_rollback),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def transition_state(self, intent_id: str, to_state: IntentState, reason: str) -> None:
        with self._connect() as conn:
            current = conn.execute(
                "SELECT status FROM intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            from_state = current["status"] if current else None
            conn.execute(
                """
                INSERT INTO state_transitions (intent_id, from_state, to_state, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (intent_id, from_state, to_state.value, reason, datetime.utcnow().isoformat()),
            )
            conn.execute(
                "UPDATE intents SET status = ? WHERE intent_id = ?",
                (to_state.value, intent_id),
            )
            conn.commit()

    def record_order(
        self,
        intent_id: str,
        order_id: str | None,
        leg_name: str,
        exchange: str,
        symbol: str,
        side: str,
        order_type: str,
        client_order_id: str,
        status: str,
        reduce_only: bool,
        post_only: bool,
        raw: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    intent_id, order_id, leg_name, exchange_name, symbol, side, order_type,
                    client_order_id, status, reduce_only, post_only, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id,
                    order_id,
                    leg_name,
                    exchange,
                    symbol,
                    side,
                    order_type,
                    client_order_id,
                    status,
                    int(reduce_only),
                    int(post_only),
                    json.dumps(raw or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def record_fill(
        self,
        intent_id: str,
        order_id: str | None,
        filled_qty: float,
        avg_price: float | None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fills (intent_id, order_id, filled_qty, avg_price, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id,
                    order_id,
                    filled_qty,
                    avg_price,
                    json.dumps(raw or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def record_recovery_action(self, intent_id: str, action: str, details: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO recovery_actions (intent_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (intent_id, action, details, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def list_active_intents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM intents
                WHERE status NOT IN (?, ?)
                ORDER BY created_at ASC
                """,
                (IntentState.CLOSED.value, IntentState.FAILED_SAFE.value),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_state_transitions(self, intent_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM state_transitions
                WHERE intent_id = ?
                ORDER BY id ASC
                """,
                (intent_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_recovery_actions(self, intent_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM recovery_actions
                WHERE intent_id = ?
                ORDER BY id ASC
                """,
                (intent_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def build_restart_snapshot(self) -> dict[str, Any]:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "active_intents": self.list_active_intents(),
        }

    def get_intent(self, intent_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
        return dict(row) if row else None
