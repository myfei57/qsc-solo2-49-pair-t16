"""Mutable strip tracking state."""

from __future__ import annotations

from dataclasses import dataclass

#: Gain deviation, per unit, mapped onto sag in millimetres.
SAG_PER_GAIN_POINT = 10.0

#: Largest single marker correction, in millimetres, applied in one step.
MAX_CORRECTION = 5.0

#: Cumulative signed correction may use at most this share of the odometer.
CORRECTION_TRAVEL_RATIO = 0.02

#: Reconcile allowance, in millimetres, before any travel has accumulated.
CORRECTION_FLOOR = 5.0


@dataclass(slots=True)
class StripState:
    track: float = 0.0
    seam_id: str = ""
    running: bool = True
    tail_dirty: bool = True
    speed: float = 0.0
    travel: float = 0.0
    correction_total: float = 0.0

    def correction_band(self) -> float:
        """Absolute signed-correction budget backed by the odometer."""

        return max(CORRECTION_FLOOR, self.travel * CORRECTION_TRAVEL_RATIO)

    def correction_allowance(self) -> float:
        """Headroom still open before the cumulative budget is exhausted."""

        return self.correction_band() - abs(self.correction_total)
