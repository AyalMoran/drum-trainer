#!/usr/bin/env python3
"""
Test script for the DrumAnalyzer
"""

import time
from models import Drill, HitEvent
from analyzer import DrumAnalyzer

def test_analyzer():
    """Test the analyzer with a paradiddle drill"""
    
    # Create a paradiddle drill
    drill = Drill(
        id="test_paradiddle",
        name="Test Paradiddle",
        tempo_bpm=120,
        subdivision=4,
        beats_per_bar=4,
        bars=4,
        stickings=["R", "L", "R", "R", "L", "R", "L", "L"],
        accents=[1, 0, 0, 0, 1, 0, 0, 0],
        velocity_targets={
            "accent": 100,
            "tap": 40,
            "tolerance": 15
        },
        timing={
            "ok_ms": 20,
            "good_ms": 10,
            "bad_ms": 40
        }
    )
    
    # Create analyzer
    analyzer = DrumAnalyzer(drill, client_offset_ms=0.0)
    
    print(f"Drill: {drill.name} at {drill.tempo_bpm} BPM")
    print(f"Grid slots: {len(analyzer.grid_times)}")
    print(f"Grid duration: {(analyzer.grid_times[-1] - analyzer.grid_times[0]) / 1000:.2f} seconds")
    print()
    
    # Simulate some hits
    base_time = time.perf_counter() * 1000.0
    
    # Perfect timing hits
    perfect_hits = [
        (base_time + 1000 + 0, 100),    # First accent, perfect timing
        (base_time + 1000 + 125, 40),   # First tap, perfect timing
        (base_time + 1000 + 250, 40),   # Second tap, perfect timing
        (base_time + 1000 + 375, 40),   # Third tap, perfect timing
        (base_time + 1000 + 500, 100),  # Second accent, perfect timing
        (base_time + 1000 + 625, 40),   # Fourth tap, perfect timing
        (base_time + 1000 + 750, 40),   # Fifth tap, perfect timing
        (base_time + 1000 + 875, 40),   # Sixth tap, perfect timing
    ]
    
    print("Testing perfect timing hits:")
    for i, (hit_time, velocity) in enumerate(perfect_hits):
        hit = HitEvent(
            t=hit_time,
            type="midi",
            note=38,  # Snare drum
            velocity=velocity
        )
        
        feedback = analyzer.process_midi_hit(hit)
        print(f"  Hit {i+1}: Slot {feedback.slot_idx}, Delta: {feedback.delta_ms:+.1f}ms, "
              f"Timing: {feedback.timing_score:.2f}, Dynamics: {feedback.dyn_score:.2f}")
    
    print()
    print("Rolling scores:")
    print(f"  Timing: {feedback.rolling['timing']:.3f}")
    print(f"  Dynamics: {feedback.rolling['dynamics']:.3f}")
    print(f"  Diamond: {feedback.rolling['diamond']:.3f}")
    
    print()
    
    # Test some off-timing hits
    print("Testing off-timing hits:")
    off_timing_hits = [
        (base_time + 2000 + 50, 100),   # 50ms late accent
        (base_time + 2000 + 175 + 30, 40),  # 30ms early tap
        (base_time + 2000 + 300 + 60, 40),  # 60ms late tap
    ]
    
    for i, (hit_time, velocity) in enumerate(off_timing_hits):
        hit = HitEvent(
            t=hit_time,
            type="midi",
            note=38,
            velocity=velocity
        )
        
        feedback = analyzer.process_midi_hit(hit)
        print(f"  Off-hit {i+1}: Slot {feedback.slot_idx}, Delta: {feedback.delta_ms:+.1f}ms, "
              f"Timing: {feedback.timing_score:.2f}, Dynamics: {feedback.dyn_score:.2f}")
    
    print()
    print("Final rolling scores:")
    print(f"  Timing: {feedback.rolling['timing']:.3f}")
    print(f"  Dynamics: {feedback.rolling['dynamics']:.3f}")
    print(f"  Diamond: {feedback.rolling['diamond']:.3f}")
    
    # Get final metrics
    final_metrics = analyzer.get_final_metrics()
    print()
    print("Final metrics:")
    print(f"  Total hits: {final_metrics.total_hits}")
    print(f"  Timing mean: {final_metrics.timing_mean:+.1f}ms")
    print(f"  Timing std: {final_metrics.timing_std:.1f}ms")
    print(f"  Dynamics target: {final_metrics.dynamics_target:.3f}")
    print(f"  Dynamics std: {final_metrics.dynamics_std:.3f}")
    print(f"  Diamond score: {final_metrics.diamond_score:.3f}")
    print(f"  Missed slots: {final_metrics.missed_slots}")

if __name__ == "__main__":
    test_analyzer()
