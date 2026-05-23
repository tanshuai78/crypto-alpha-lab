from __future__ import annotations

from enum import Enum


class IntentState(str, Enum):
    CREATED = "CREATED"
    MAKER_SENT = "MAKER_SENT"
    MAKER_PARTIAL = "MAKER_PARTIAL"
    CANCEL_PENDING = "CANCEL_PENDING"
    HEDGE_SENT = "HEDGE_SENT"
    HEDGED = "HEDGED"
    ROLLBACK_SENT = "ROLLBACK_SENT"
    UNKNOWN_REMOTE_STATE = "UNKNOWN_REMOTE_STATE"
    CLOSED = "CLOSED"
    FAILED_SAFE = "FAILED_SAFE"


_VALID_TRANSITIONS = {
    IntentState.CREATED: {
        IntentState.MAKER_SENT,
        IntentState.UNKNOWN_REMOTE_STATE,
        IntentState.FAILED_SAFE,
    },
    IntentState.MAKER_SENT: {
        IntentState.MAKER_PARTIAL,
        IntentState.CANCEL_PENDING,
        IntentState.HEDGE_SENT,
        IntentState.ROLLBACK_SENT,
        IntentState.UNKNOWN_REMOTE_STATE,
        IntentState.CLOSED,
        IntentState.FAILED_SAFE,
    },
    IntentState.MAKER_PARTIAL: {
        IntentState.CANCEL_PENDING,
        IntentState.HEDGE_SENT,
        IntentState.ROLLBACK_SENT,
        IntentState.FAILED_SAFE,
    },
    IntentState.CANCEL_PENDING: {
        IntentState.HEDGE_SENT,
        IntentState.ROLLBACK_SENT,
        IntentState.UNKNOWN_REMOTE_STATE,
        IntentState.FAILED_SAFE,
    },
    IntentState.HEDGE_SENT: {
        IntentState.HEDGED,
        IntentState.ROLLBACK_SENT,
        IntentState.FAILED_SAFE,
    },
    IntentState.HEDGED: {
        IntentState.CLOSED,
    },
    IntentState.ROLLBACK_SENT: {
        IntentState.CLOSED,
        IntentState.FAILED_SAFE,
    },
    IntentState.UNKNOWN_REMOTE_STATE: {
        IntentState.HEDGE_SENT,
        IntentState.ROLLBACK_SENT,
        IntentState.FAILED_SAFE,
    },
    IntentState.CLOSED: set(),
    IntentState.FAILED_SAFE: set(),
}


class IntentStateMachine:
    def __init__(self, initial_state: IntentState = IntentState.CREATED):
        self.state = initial_state

    def transition(self, next_state: IntentState) -> IntentState:
        allowed = _VALID_TRANSITIONS[self.state]
        if next_state not in allowed:
            raise ValueError(f"Invalid state transition: {self.state} -> {next_state}")
        self.state = next_state
        return self.state
