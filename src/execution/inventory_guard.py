from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

try:
    from configs.base import (
        INVENTORY_GUARD_FORCE_DELEVERAGE_RATIO,
        INVENTORY_GUARD_PAUSE_RATIO,
        INVENTORY_GUARD_WARNING_RATIO,
    )
except ModuleNotFoundError:
    from configs.base import (  # type: ignore[no-redef]
        INVENTORY_GUARD_FORCE_DELEVERAGE_RATIO,
        INVENTORY_GUARD_PAUSE_RATIO,
        INVENTORY_GUARD_WARNING_RATIO,
    )


class GuardStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    PAUSED = "PAUSED"
    FORCE_DELEVERAGING = "FORCE_DELEVERAGING"
    RECOVERY = "RECOVERY"


@dataclass
class InventoryAssessment:
    status: GuardStatus
    gross_exposure_usdt: float
    net_delta_usdt: float
    ratio: float
    reason: str


class InventoryGuard:
    def __init__(
        self,
        warning_ratio: float = INVENTORY_GUARD_WARNING_RATIO,
        pause_ratio: float = INVENTORY_GUARD_PAUSE_RATIO,
        force_deleverage_ratio: float = INVENTORY_GUARD_FORCE_DELEVERAGE_RATIO,
    ):
        self.warning_ratio = warning_ratio
        self.pause_ratio = pause_ratio
        self.force_deleverage_ratio = force_deleverage_ratio
        self._recovery_latched = False

    def assess(
        self,
        *,
        spot_qty: float,
        spot_mark: float,
        perp_qty: float,
        perp_mark: float,
        orphan_intent_count: int = 0,
        unknown_remote_count: int = 0,
    ) -> InventoryAssessment:
        spot_notional = spot_qty * spot_mark
        perp_notional = perp_qty * perp_mark
        gross = max(abs(spot_notional), abs(perp_notional), 1e-9)
        net_delta = abs(spot_notional - perp_notional)
        ratio = net_delta / gross

        if self._recovery_latched:
            return InventoryAssessment(
                status=GuardStatus.RECOVERY,
                gross_exposure_usdt=gross,
                net_delta_usdt=net_delta,
                ratio=ratio,
                reason=(
                    "recovery lock active"
                    if orphan_intent_count == 0 and unknown_remote_count == 0
                    else "recovery lock active with unresolved journal state"
                ),
            )

        if ratio > self.force_deleverage_ratio:
            self._recovery_latched = True
            return InventoryAssessment(
                GuardStatus.FORCE_DELEVERAGING,
                gross,
                net_delta,
                ratio,
                "net delta exceeded force deleverage threshold",
            )

        if ratio > self.pause_ratio:
            return InventoryAssessment(
                GuardStatus.PAUSED,
                gross,
                net_delta,
                ratio,
                "net delta exceeded pause threshold",
            )

        if ratio > self.warning_ratio:
            return InventoryAssessment(
                GuardStatus.WARNING,
                gross,
                net_delta,
                ratio,
                "net delta exceeded warning threshold",
            )

        return InventoryAssessment(
            GuardStatus.HEALTHY,
            gross,
            net_delta,
            ratio,
            "inventory balanced",
        )

    def clear_recovery(
        self,
        *,
        inventory_ok_count: int,
        min_inventory_ok_count: int,
        orphan_intent_count: int,
        unknown_remote_count: int,
    ) -> bool:
        if not self._recovery_latched:
            return True
        if inventory_ok_count < min_inventory_ok_count:
            return False
        if orphan_intent_count > 0 or unknown_remote_count > 0:
            return False
        self._recovery_latched = False
        return True

    def allow_intent(self, intent) -> bool:
        if not self._recovery_latched:
            return True
        return bool(intent.leg_a.reduce_only and intent.leg_b.reduce_only)
