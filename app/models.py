from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
import json

class VelocityTargets(BaseModel):
    accent: int = Field(..., ge=0, le=127)
    tap: int = Field(..., ge=0, le=127)
    tolerance: int = Field(..., ge=0, le=127)

class TimingConfig(BaseModel):
    ok_ms: int = Field(..., ge=0)
    good_ms: int = Field(..., ge=0)
    bad_ms: int = Field(..., ge=0)

class Drill(BaseModel):
    id: str
    name: str
    tempo_bpm: int = Field(..., ge=40, le=300)
    subdivision: int = Field(..., ge=1, le=16)
    beats_per_bar: int = Field(..., ge=1, le=16)
    bars: int = Field(..., ge=1, le=32)
    stickings: List[str] = Field(..., min_items=1)
    accents: List[int] = Field(..., min_items=1)
    velocity_targets: VelocityTargets
    timing: TimingConfig
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SessionCreate(BaseModel):
    drill_id: str
    input_type: Literal["midi", "audio"]
    client_latency_ms: Optional[float] = None

class Session(BaseModel):
    id: str
    user_id: Optional[str] = None
    drill_id: str
    started_at: datetime
    client_latency_ms: Optional[float] = None
    input_type: Literal["midi", "audio"]
    status: Literal["active", "completed"] = "active"

class HitEvent(BaseModel):
    t: float  # client monotonic time in ms
    type: Literal["midi", "audio"]
    note: Optional[int] = None  # for MIDI
    velocity: Optional[int] = None  # for MIDI
    seq: Optional[int] = None  # for audio
    pcm: Optional[str] = None  # base64 encoded PCM for audio

class HitFeedback(BaseModel):
    type: Literal["hit_feedback"] = "hit_feedback"
    slot_idx: int
    delta_ms: float
    velocity: Optional[int] = None
    velocity_target: Optional[int] = None
    timing_score: float
    dyn_score: float
    rolling: Dict[str, float]

class TakeMetrics(BaseModel):
    timing_mean: float
    timing_std: float
    dynamics_target: float
    dynamics_std: float
    diamond_score: float
    total_hits: int
    missed_slots: int

class Take(BaseModel):
    id: str
    session_id: str
    finished_at: datetime
    metrics: TakeMetrics

class DrillList(BaseModel):
    drills: List[Drill]
    total: int

class SessionList(BaseModel):
    sessions: List[Session]
    total: int