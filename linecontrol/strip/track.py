"""Seam position tracking and its snapshot."""

from __future__ import annotations

from ..domain.events import Event
from ..domain.kinds import EventKind
from ..domain.records import TrackSnapshot, utcnow
from ..store.keys import KEY_TRACK
from ..store.snapshot import save_json
from .errors import StripError, StripErrorCode
from .state import MAX_CORRECTION


class TrackOps:
    """Mixed into :class:`~linecontrol.strip.strip.Strip`."""

    def track_update(self, position: float) -> TrackSnapshot:
        self.data.track = float(position)
        self._reset_corrections()
        return self._persist()

    def track_refresh(self, position: float, seam_id: str) -> TrackSnapshot:
        """Move the track point onto a freshly generated seam."""

        self.data.track = float(position)
        self.data.seam_id = seam_id
        self._reset_corrections()
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

    def track_correct(self, measured: float) -> TrackSnapshot:
        """Snap the track point onto a field-measured marker.

        The correction is reconciled against the odometer before anything is
        touched: a single move larger than :data:`MAX_CORRECTION`, or one that
        would push the cumulative signed correction past the travel-backed
        budget, is rejected so a bad marker cannot drag the downstream shear
        band. The physical travel counter is never rewritten.
        """

        if not self.shear_permit():
            raise StripError(StripErrorCode.TRACK_STALE, "no seam tracked to correct")
        delta = float(measured) - self.data.track
        if abs(delta) > MAX_CORRECTION:
            raise StripError(
                StripErrorCode.TRACK_CORRECTION_LARGE,
                f"marker correction {delta:+.3f} outside +/-{MAX_CORRECTION:g}",
            )
        next_total = self.data.correction_total + delta
        if abs(next_total) > self.data.correction_band():
            raise StripError(
                StripErrorCode.TRACK_RECONCILE_EXCEEDED,
                "cumulative marker correction "
                f"{next_total:+.3f} exceeds odometer budget +/-"
                f"{self.data.correction_band():.3f}",
            )
        self.data.track = float(measured)
        self.data.correction_total = next_total
        snapshot = self._persist()
        self.bus.publish(
            Event(
                kind=EventKind.TRACK,
                source="strip",
                message="corrected",
                payload=delta,
            )
        )
        return snapshot

    def track_position(self) -> float:
        return self.data.track

    def seam_id(self) -> str:
        return self.data.seam_id

    def correction_total(self) -> float:
        return self.data.correction_total

    def correction_band(self) -> float:
        return self.data.correction_band()

    def correction_allowance(self) -> float:
        return self.data.correction_allowance()

    def shear_permit(self) -> bool:
        return self.data.seam_id != "" and self.data.track > 0

    def restore_track(self, snapshot: TrackSnapshot) -> None:
        self.data.track = snapshot.position
        self.data.seam_id = snapshot.seam_id
        self.data.correction_total = snapshot.correction_total

    def _reset_corrections(self) -> None:
        """Clear the ledger when the track is re-homed onto a new seam."""

        self.data.correction_total = 0.0

    def _persist(self) -> TrackSnapshot:
        snapshot = TrackSnapshot(
            position=self.data.track,
            seam_id=self.data.seam_id,
            correction_total=self.data.correction_total,
            saved=utcnow(),
        )
        save_json(self.store, KEY_TRACK, snapshot)
        return snapshot
