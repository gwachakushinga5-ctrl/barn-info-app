from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


def _now():
    return datetime.now(timezone.utc)


class Farmer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    phone: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=_now)


class Barn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    barn_code: str = Field(unique=True, index=True)
    farmer_id: Optional[int] = Field(default=None, foreign_key="farmer.id")
    farmer_name: str = Field(default="")
    location_text: str = Field(default="", index=True)
    capacity_kg: float = Field(default=500.0)
    created_at: datetime = Field(default_factory=_now)


class Reading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    barn_id: int = Field(foreign_key="barn.id", index=True)
    taken_at: datetime = Field(default_factory=_now, index=True)
    stage: str = Field(index=True)
    temp_c: float
    humidity_pct: Optional[float] = Field(default=None)
    load_kg: Optional[float] = Field(default=None)
    heat_source: str = Field(default="")
    notes: str = Field(default="")
    status: str = Field(default="OK", index=True)
    reasons: str = Field(default="")
    risk_score: int = Field(default=0)
