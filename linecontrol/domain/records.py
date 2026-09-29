"""Persisted and in-flight process records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .events import utcnow


def _stamp(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return utcnow()


@dataclass(frozen=True, slots=True)
class Confirm:
    """Outcome of a strip head alignment check."""

    ok: bool = False
    position: float = 0.0
    at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "position": self.position, "at": self.at.isoformat()}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Confirm":
        return cls(
            ok=bool(raw.get("ok", False)),
            position=float(raw.get("position", 0.0)),
            at=_stamp(raw.get("at")),
        )


@dataclass(frozen=True, slots=True)
class WeldRecord:
    """A completed weld seam."""

    seam_id: str = ""
    position: float = 0.0
    tension: float = 0.0
    heat_input: float = 0.0
    at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seam_id": self.seam_id,
            "position": self.position,
            "tension": self.tension,
            "heat_input": self.heat_input,
            "at": self.at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WeldRecord":
        return cls(
            seam_id=str(raw.get("seam_id", "")),
            position=float(raw.get("position", 0.0)),
            tension=float(raw.get("tension", 0.0)),
            heat_input=float(raw.get("heat_input", 0.0)),
            at=_stamp(raw.get("at")),
        )


@dataclass(frozen=True, slots=True)
class TensionSnapshot:
    value: float = 0.0
    gain: float = 1.0
    saved: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "gain": self.gain, "saved": self.saved.isoformat()}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TensionSnapshot":
        return cls(
            value=float(raw.get("value", 0.0)),
            gain=float(raw.get("gain", 1.0)),
            saved=_stamp(raw.get("saved")),
        )


@dataclass(frozen=True, slots=True)
class AcidSnapshot:
    level: float = 0.0
    offset: float = 0.0
    saved: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "offset": self.offset, "saved": self.saved.isoformat()}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AcidSnapshot":
        return cls(
            level=float(raw.get("level", 0.0)),
            offset=float(raw.get("offset", 0.0)),
            saved=_stamp(raw.get("saved")),
        )


@dataclass(frozen=True, slots=True)
class PumpSnapshot:
    running: bool = False
    saved: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"running": self.running, "saved": self.saved.isoformat()}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PumpSnapshot":
        return cls(running=bool(raw.get("running", False)), saved=_stamp(raw.get("saved")))


@dataclass(frozen=True, slots=True)
class TrackSnapshot:
    position: float = 0.0
    seam_id: str = ""
    saved: datetime = field(default_factory=utcnow)
    travel: float = 0.0
    track_mileage: float | None = None
    track_correction: float = 0.0
    track_correction_total: float = 0.0
    track_corrections: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "seam_id": self.seam_id,
            "travel": self.travel,
            "track_mileage": self.mileage(),
            "track_correction": self.track_correction,
            "track_correction_total": self.track_correction_total,
            "track_corrections": self.track_corrections,
            "saved": self.saved.isoformat(),
        }

    def mileage(self) -> float:
        return self.travel if self.track_mileage is None else self.track_mileage

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TrackSnapshot":
        travel = float(raw.get("travel", 0.0))
        mileage = float(raw["track_mileage"]) if "track_mileage" in raw else travel
        return cls(
            position=float(raw.get("position", 0.0)),
            seam_id=str(raw.get("seam_id", "")),
            travel=travel,
            track_mileage=mileage,
            track_correction=float(raw.get("track_correction", 0.0)),
            track_correction_total=float(raw.get("track_correction_total", 0.0)),
            track_corrections=int(raw.get("track_corrections") or 0),
            saved=_stamp(raw.get("saved")),
        )


@dataclass(frozen=True, slots=True)
class TrackCorrection:
    """Result of reconciling a track point against a measured marker."""

    position: float
    previous_position: float
    delta: float
    mileage: float
    correction_total: float
    net_correction: float
    limit: float
    marker: str = ""
    at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "previousPosition": self.previous_position,
            "delta": self.delta,
            "mileage": self.mileage,
            "correctionTotal": self.correction_total,
            "netCorrection": self.net_correction,
            "limit": self.limit,
            "marker": self.marker,
            "at": self.at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RinseSnapshot:
    active: bool = False
    saved: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {"active": self.active, "saved": self.saved.isoformat()}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RinseSnapshot":
        return cls(active=bool(raw.get("active", False)), saved=_stamp(raw.get("saved")))


@dataclass(frozen=True, slots=True)
class LatchSnapshot:
    interlock: bool = False
    alarm: bool = False
    saved: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interlock": self.interlock,
            "alarm": self.alarm,
            "saved": self.saved.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LatchSnapshot":
        return cls(
            interlock=bool(raw.get("interlock", False)),
            alarm=bool(raw.get("alarm", False)),
            saved=_stamp(raw.get("saved")),
        )
