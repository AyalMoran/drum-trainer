export interface VelocityTargets {
  accent: number;
  tap: number;
  tolerance: number;
}

export interface TimingConfig {
  ok_ms: number;
  good_ms: number;
  bad_ms: number;
}

export interface Drill {
  id: string;
  name: string;
  tempo_bpm: number;
  subdivision: number;
  beats_per_bar: number;
  bars: number;
  stickings: string[];
  accents: number[];
  velocity_targets: VelocityTargets;
  timing: TimingConfig;
  created_by?: string;
  created_at?: string;
}

export interface SessionCreate {
  drill_id: string;
  input_type: 'midi' | 'audio';
  client_latency_ms?: number;
}

export interface Session {
  id: string;
  user_id?: string;
  drill_id: string;
  started_at: string;
  client_latency_ms?: number;
  input_type: 'midi' | 'audio';
  status: 'active' | 'completed';
}

export interface HitEvent {
  t: number;
  type: 'midi' | 'audio';
  note?: number;
  velocity?: number;
  seq?: number;
  pcm?: string;
}

export interface HitFeedback {
  type: 'hit_feedback';
  slot_idx: number;
  delta_ms: number;
  velocity?: number;
  velocity_target?: number;
  timing_score: number;
  dyn_score: number;
  rolling: {
    timing: number;
    dynamics: number;
    diamond: number;
  };
}

export interface SessionStart {
  type: 'session_start';
  session_id: string;
  drill: {
    id: string;
    name: string;
    tempo_bpm: number;
    subdivision: number;
    beats_per_bar: number;
    bars: number;
  };
  server_start_time: string;
}

export interface CalibrationUpdate {
  type: 'calibration_update';
  client_offset_ms: number;
}

export interface ErrorMessage {
  type: 'error';
  message: string;
}

export type WebSocketMessage = HitFeedback | SessionStart | CalibrationUpdate | ErrorMessage;
