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
    custom_tempo_bpm: Optional[int] = Field(None, ge=40, le=300)  # Allow custom tempo

class Session(BaseModel):
    id: str
    user_id: Optional[str] = None
    drill_id: str
    started_at: datetime
    client_latency_ms: Optional[float] = None
    input_type: Literal["midi", "audio"]
    status: Literal["active", "completed"] = "active"
    custom_tempo_bpm: Optional[int] = None  # Store the custom tempo used

class HitEvent(BaseModel):
    t: float  # client monotonic time in ms
    type: Literal["midi", "audio", "metronome_control"]
    note: Optional[int] = None  # for MIDI
    velocity: Optional[int] = None  # for MIDI
    seq: Optional[int] = None  # for audio
    pcm: Optional[str] = None  # base64 encoded PCM for audio
    metronome_action: Optional[Literal["start", "stop", "reset", "update_tempo"]] = None  # for metronome control
    custom_tempo_bpm: Optional[int] = Field(None, ge=40, le=300)  # for tempo updates

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

class MetronomeControl(BaseModel):
    action: Literal["start", "stop", "reset"]
    session_id: str

class MetronomeState(BaseModel):
    type: Literal["metronome_state"] = "metronome_state"
    is_playing: bool
    current_beat: int
    current_subdivision: int
    tempo_bpm: int
    subdivision: int
    beats_per_bar: int

class MetronomeTick(BaseModel):
    type: Literal["metronome_tick"] = "metronome_tick"
    beat: int
    subdivision: int
    is_downbeat: bool
    is_beat: bool

class DrillTempoUpdate(BaseModel):
    drill_id: str
    new_tempo_bpm: int = Field(..., ge=40, le=300)