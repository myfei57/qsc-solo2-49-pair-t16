"""Seam position tracking, measured-marker correction and its snapshot."""

from __future__ import annotations

from ..domain.events import Event
from ..domain.kinds import EventKind
from ..domain.records import TrackCorrection, TrackSnapshot, utcnow
from ..store.keys import KEY_TRACK
from ..store.snapshot import save_json
from .errors import StripError, StripErrorCode

#: Minimum reconciliation allowance, in line-length units, regardless of travel.
TRACK_CORRECTION_FLOOR = 0.5

#: Additional correction allowance accumulated per unit of measured travel.
TRACK_CORRECTION_RATE = 0.02


class TrackOps:
    """Mixed into :class:`~linecontrol.strip.strip.Strip`."""

    def track_update(self, position: float) -> TrackSnapshot:
        self.data.track = float(position)
        self._reset_track_account()
        return self._persist()

    def track_refresh(self, position: float, seam_id: str) -> TrackSnapshot:
        """Move the track point onto a freshly generated seam."""

        self.data.track = float(position)
        self.data.seam_id = seam_id
        self._reset_track_account()
        snapshot = self._persist()
        self.bus.publish(
            Event(
                kind=EventKind.TRACK,
                source="strip",
                message=seam_id,
                payload=float(position),
            )
        )
        return snapshot

    def track_correct(
        self,
        measured: float,
        floor: float = TRACK_CORRECTION_FLOOR,
        rate: float = TRACK_CORRECTION_RATE,
        marker: str = "",
    ) -> TrackCorrection:
        """Reconcile the tracked seam with a physical marker position.

        The correction is accepted only when the signed net drift remains
        within the mileage-backed allowance.  A successful correction updates
        the physical track position, while mileage and signed net drift remain
        accounted from the weld seam until the next seam refresh.
        """

        if not self.shear_permit():
            raise StripError(StripErrorCode.TRACK_STALE, "weld track stale")
        measured = float(measured)
        previous = self.data.track
        delta = measured - previous
        net_correction = self.data.track_correction + delta
        limit = self.track_correction_limit(floor, rate)
        if abs(net_correction) > limit:
            raise StripError(
                StripErrorCode.TRACK_CORRECTION_LIMIT,
                (
                    f"net track correction {net_correction:.3f} exceeds mileage "
                    f"allowance {limit:.3f}"
                ),
            )

        self.data.track = measured
        self.data.track_correction = net_correction
        self.data.track_correction_total += abs(delta)
        self.data.track_corrections += 1
        self._persist()
        result = TrackCorrection(
            position=measured,
            previous_position=previous,
            delta=delta,
            mileage=self.data.track_mileage,
            correction_total=self.data.track_correction_total,
            net_correction=net_correction,
            limit=limit,
            marker=marker,
        )
        self.bus.publish(
            Event(
                kind=EventKind.TRACK,
                source="strip",
                message=marker or "corrected",
                payload=delta,
            )
        )
        return result

    correct_track = track_correct

    def track_position(self) -> float:
        return self.data.track

    def track_mileage(self) -> float:
        """Measured travel accumulated since the last weld seam anchor."""

        return self.data.track_mileage

    def track_correction(self) -> float:
        """Signed net correction amount accounted since the last seam anchor."""

        return self.data.track_correction

    def track_correction_total(self) -> float:
        """Absolute correction mileage accounted on this line instance."""

        return self.data.track_correction_total

    def track_correction_count(self) -> int:
        return self.data.track_corrections

    def track_correction_limit(
        self,
        floor: float = TRACK_CORRECTION_FLOOR,
        rate: float = TRACK_CORRECTION_RATE,
    ) -> float:
        return float(floor) + float(rate) * self.data.track_mileage

    def seam_id(self) -> str:
        return self.data.seam_id

    def shear_permit(self) -> bool:
        return self.data.seam_id != "" and self.data.track > 0

    def restore_track(self, snapshot: TrackSnapshot) -> None:
        self.data.track = snapshot.position
        self.data.seam_id = snapshot.seam_id
        self.data.travel = snapshot.travel
        self.data.track_mileage = snapshot.mileage()
        self.data.track_correction = snapshot.track_correction
        self.data.track_correction_total = snapshot.track_correction_total
        self.data.track_corrections = snapshot.track_corrections

    def _reset_track_account(self) -> None:
        self.data.track_mileage = 0.0
        self.data.track_correction = 0.0

    def _persist(self) -> TrackSnapshot:
        snapshot = TrackSnapshot(
            position=self.data.track,
            seam_id=self.data.seam_id,
            travel=self.data.travel,
            track_mileage=self.data.track_mileage,
            track_correction=self.data.track_correction,
            track_correction_total=self.data.track_correction_total,
            track_corrections=self.data.track_corrections,
            saved=utcnow(),
        )
        save_json(self.store, KEY_TRACK, snapshot)
        return snapshot
