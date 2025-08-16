import numpy as np
import time
from typing import List, Dict, Tuple, Optional
from .models import Drill, HitEvent, HitFeedback, TakeMetrics

class DrumAnalyzer:
    """Core analyzer for drum timing and dynamics"""
    
    def __init__(self, drill: Drill, client_offset_ms: float = 0.0):
        self.drill = drill
        self.client_offset_ms = client_offset_ms
        
        # Precompute grid times
        self.grid_times = self._compute_grid_times()
        
        # Rolling statistics
        self.deltas = []
        self.velocities = []
        self.hit_slots = set()
        
        # EWMA parameters for rolling scores
        self.alpha = 0.1  # smoothing factor
        
        # Current rolling scores
        self.rolling_timing_mean = 0.0
        self.rolling_timing_var = 0.0
        self.rolling_dyn_target = 0.0
        self.rolling_dyn_var = 0.0
        
    def _compute_grid_times(self) -> np.ndarray:
        """Compute the time grid for the drill"""
        # Convert BPM to milliseconds per beat
        ms_per_beat = 60000.0 / self.drill.tempo_bpm
        
        # Time per subdivision
        ms_per_subdivision = ms_per_beat / self.drill.subdivision
        
        # Total slots in the drill
        total_slots = self.drill.beats_per_bar * self.drill.bars * self.drill.subdivision
        
        # Create grid starting from current time
        start_time = time.perf_counter() * 1000.0 + 1000.0  # 1 second from now
        grid = np.array([start_time + i * ms_per_subdivision for i in range(total_slots)], dtype=np.float64)
        
        return grid
    
    def _find_nearest_slot(self, hit_time_ms: float) -> Tuple[int, float]:
        """Find the nearest grid slot and return (slot_index, delta_ms)"""
        # Convert client time to server time
        server_time = hit_time_ms + self.client_offset_ms
        
        # Find nearest slot
        slot_idx = int(np.argmin(np.abs(self.grid_times - server_time)))
        delta_ms = float(server_time - self.grid_times[slot_idx])
        
        return slot_idx, delta_ms
    
    def _calculate_timing_score(self, delta_ms: float) -> float:
        """Calculate timing score based on delta from grid"""
        abs_delta = abs(delta_ms)
        
        if abs_delta <= self.drill.timing.good_ms:
            return 1.0
        elif abs_delta <= self.drill.timing.ok_ms:
            # Linear interpolation between good and ok
            ratio = (self.drill.timing.ok_ms - abs_delta) / (self.drill.timing.ok_ms - self.drill.timing.good_ms)
            return 0.7 + 0.3 * ratio
        elif abs_delta <= self.drill.timing.bad_ms:
            # Linear interpolation between ok and bad
            ratio = (self.drill.timing.bad_ms - abs_delta) / (self.drill.timing.bad_ms - self.drill.timing.ok_ms)
            return 0.0 + 0.7 * ratio
        else:
            return 0.0
    
    def _calculate_dynamics_score(self, velocity: int, slot_idx: int) -> Tuple[float, int]:
        """Calculate dynamics score based on velocity vs target"""
        # Determine if this slot should be accented
        pattern_length = len(self.drill.accents)
        accent_value = self.drill.accents[slot_idx % pattern_length]
        
        if accent_value:
            target_velocity = self.drill.velocity_targets.accent
        else:
            target_velocity = self.drill.velocity_targets.tap
        
        # Calculate score based on how close velocity is to target
        tolerance = self.drill.velocity_targets.tolerance
        diff = abs(velocity - target_velocity)
        
        if diff <= tolerance:
            score = 1.0
        else:
            # Linear falloff beyond tolerance
            max_diff = 127  # MIDI velocity range
            score = max(0.0, 1.0 - (diff - tolerance) / (max_diff - tolerance))
        
        return score, target_velocity
    
    def _update_rolling_scores(self, timing_score: float, dyn_score: float):
        """Update rolling scores using EWMA"""
        # Update timing scores
        self.rolling_timing_mean = (1 - self.alpha) * self.rolling_timing_mean + self.alpha * timing_score
        self.rolling_timing_var = (1 - self.alpha) * self.rolling_timing_var + self.alpha * (1.0 - timing_score)
        
        # Update dynamics scores
        self.rolling_dyn_target = (1 - self.alpha) * self.rolling_dyn_target + self.alpha * dyn_score
        self.rolling_dyn_var = (1 - self.alpha) * self.rolling_dyn_var + self.alpha * (1.0 - dyn_score)
    
    def _calculate_diamond_score(self) -> float:
        """Calculate the diamond score using geometric mean of four axes"""
        # Ensure all scores are positive (avoid log(0))
        axes = np.array([
            max(1e-6, self.rolling_timing_mean),
            max(1e-6, 1.0 - self.rolling_timing_var),  # Invert variance (lower is better)
            max(1e-6, self.rolling_dyn_target),
            max(1e-6, 1.0 - self.rolling_dyn_var)      # Invert variance (lower is better)
        ], dtype=np.float64)
        
        # Weights for each axis
        weights = np.array([0.35, 0.25, 0.25, 0.15])
        
        # Geometric mean
        log_axes = np.log(axes)
        weighted_sum = np.sum(weights * log_axes)
        total_weight = np.sum(weights)
        
        diamond_score = float(np.exp(weighted_sum / total_weight))
        return diamond_score
    
    def process_midi_hit(self, hit: HitEvent) -> HitFeedback:
        """Process a MIDI hit event and return feedback"""
        if hit.type != "midi" or hit.velocity is None:
            raise ValueError("Invalid MIDI hit event")
        
        # Find nearest slot and calculate timing
        slot_idx, delta_ms = self._find_nearest_slot(hit.t)
        
        # Calculate scores
        timing_score = self._calculate_timing_score(delta_ms)
        dyn_score, target_velocity = self._calculate_dynamics_score(hit.velocity, slot_idx)
        
        # Store data for rolling calculations
        self.deltas.append(delta_ms)
        self.velocities.append(hit.velocity)
        self.hit_slots.add(slot_idx)
        
        # Update rolling scores
        self._update_rolling_scores(timing_score, dyn_score)
        
        # Calculate diamond score
        diamond_score = self._calculate_diamond_score()
        
        # Create feedback
        feedback = HitFeedback(
            type="hit_feedback",
            slot_idx=slot_idx,
            delta_ms=delta_ms,
            velocity=hit.velocity,
            velocity_target=target_velocity,
            timing_score=timing_score,
            dyn_score=dyn_score,
            rolling={
                "timing": float((self.rolling_timing_mean + (1.0 - self.rolling_timing_var)) / 2.0),
                "dynamics": float((self.rolling_dyn_target + (1.0 - self.rolling_dyn_var)) / 2.0),
                "diamond": diamond_score
            }
        )
        
        return feedback
    
    def process_audio_frame(self, hit: HitEvent) -> Optional[HitFeedback]:
        """Process an audio frame for onset detection (placeholder for now)"""
        # TODO: Implement onset detection
        # For now, return None to indicate no hit detected
        return None
    
    def get_final_metrics(self) -> TakeMetrics:
        """Get final metrics for the session"""
        if not self.deltas:
            return TakeMetrics(
                timing_mean=0.0,
                timing_std=0.0,
                dynamics_target=0.0,
                dynamics_std=0.0,
                diamond_score=0.0,
                total_hits=0,
                missed_slots=len(self.grid_times)
            )
        
        # Calculate final statistics
        timing_mean = float(np.mean(self.deltas))
        timing_std = float(np.std(self.deltas))
        
        # Calculate dynamics scores for all hits
        dyn_scores = []
        for i, velocity in enumerate(self.velocities):
            slot_idx = i  # This is simplified - in reality we'd track slot mapping
            score, _ = self._calculate_dynamics_score(velocity, slot_idx)
            dyn_scores.append(score)
        
        dynamics_target = float(np.mean(dyn_scores))
        dynamics_std = float(np.std(dyn_scores))
        
        # Calculate final diamond score
        final_diamond = self._calculate_diamond_score()
        
        # Count missed slots
        missed_slots = len(self.grid_times) - len(self.hit_slots)
        
        return TakeMetrics(
            timing_mean=timing_mean,
            timing_std=timing_std,
            dynamics_target=dynamics_target,
            dynamics_std=dynamics_std,
            diamond_score=final_diamond,
            total_hits=len(self.deltas),
            missed_slots=missed_slots
        )
    
    def update_client_offset(self, new_offset_ms: float):
        """Update the client offset for latency calibration"""
        self.client_offset_ms = new_offset_ms
