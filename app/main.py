import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .models import Drill, SessionCreate, Session, HitEvent, HitFeedback, DrillList, MetronomeState, MetronomeTick, DrillTempoUpdate
from .analyzer import DrumAnalyzer

# In-memory storage for MVP (replace with database later)
drills_db: Dict[str, Drill] = {}
sessions_db: Dict[str, Session] = {}
analyzers_db: Dict[str, DrumAnalyzer] = {}
metronomes_db: Dict[str, 'Metronome'] = {}

class Metronome:
    """Metronome class for generating click sounds and timing"""
    
    def __init__(self, drill: Drill, custom_tempo_bpm: Optional[int] = None):
        self.drill = drill
        self.custom_tempo_bpm = custom_tempo_bpm
        self.is_playing = False
        self.current_beat = 0
        self.current_subdivision = 0
        self.start_time = None
        self.task = None
        
    @property
    def effective_tempo(self) -> int:
        """Get the effective tempo (custom or default)"""
        return self.custom_tempo_bpm if self.custom_tempo_bpm is not None else self.drill.tempo_bpm
        
    async def start(self, websocket: WebSocket):
        """Start the metronome"""
        if self.is_playing:
            return
            
        self.is_playing = True
        self.current_beat = 0
        self.current_subdivision = 0
        self.start_time = time.time()
        
        # Start the metronome task
        self.task = asyncio.create_task(self._run_metronome(websocket))
        
    async def stop(self):
        """Stop the metronome"""
        self.is_playing = False
        if self.task:
            self.task.cancel()
            self.task = None
            
    async def reset(self):
        """Reset the metronome to initial state"""
        await self.stop()
        self.current_beat = 0
        self.current_subdivision = 0
        
    async def update_tempo(self, new_tempo_bpm: int):
        """Update the metronome tempo dynamically"""
        print(f"Updating metronome tempo from {self.effective_tempo} to {new_tempo_bpm} BPM")
        
        if self.is_playing:
            # If metronome is playing, restart it with new tempo
            await self.stop()
            self.custom_tempo_bpm = new_tempo_bpm
            print(f"Metronome stopped and tempo updated to {new_tempo_bpm} BPM")
            # Note: User needs to start again with new tempo
        else:
            # If not playing, just update the tempo
            self.custom_tempo_bpm = new_tempo_bpm
            print(f"Metronome tempo updated to {new_tempo_bpm} BPM")
        
        # Update the analyzer grid with new tempo
        await self._update_analyzer_grid()
    
    async def _update_analyzer_grid(self):
        """Update the analyzer grid when tempo changes"""
        # Find the analyzer for this session
        session_id = None
        for sid, metronome in metronomes_db.items():
            if metronome == self:
                session_id = sid
                break
        
        if session_id and session_id in analyzers_db:
            analyzer = analyzers_db[session_id]
            # Update analyzer with new tempo
            analyzer.update_tempo(self.effective_tempo)
            print(f"Analyzer updated for new tempo: {self.effective_tempo} BPM")
        
    async def _run_metronome(self, websocket: WebSocket):
        """Main metronome loop"""
        tempo = self.effective_tempo
        subdivision = self.drill.subdivision
        beats_per_bar = self.drill.beats_per_bar
        
        # Calculate intervals
        beat_interval = 60.0 / tempo  # seconds per beat
        subdivision_interval = beat_interval / subdivision  # seconds per subdivision
        
        try:
            while self.is_playing:
                # Calculate current position
                elapsed = time.time() - self.start_time
                total_subdivisions = int(elapsed / subdivision_interval)
                
                # Update beat and subdivision counters
                self.current_subdivision = total_subdivisions % subdivision
                self.current_beat = (total_subdivisions // subdivision) % beats_per_bar
                
                # Send tick information
                tick = MetronomeTick(
                    beat=self.current_beat,
                    subdivision=self.current_subdivision,
                    is_downbeat=(self.current_beat == 0),
                    is_beat=(self.current_subdivision == 0)
                )
                
                try:
                    await websocket.send_json(tick.model_dump())
                except:
                    # WebSocket might be closed
                    break
                
                # Wait for next subdivision
                await asyncio.sleep(subdivision_interval)
                
        except asyncio.CancelledError:
            # Task was cancelled (normal when stopping)
            pass
        except Exception as e:
            print(f"Metronome error: {e}")
        finally:
            self.is_playing = False

app = FastAPI(
    title="Drum Trainer API",
    description="Real-time drum timing and dynamics analysis",
    version="0.1.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0"
    }

# Seed some default drills
def seed_default_drills():
    """Seed the database with some default drills"""
    paradiddle = Drill(
        id="paradiddle_120",
        name="Single Paradiddle",
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
            "perfect_pct": 0.1,  # 10% of subdivision = perfect
            "ok_pct": 0.25,      # 25% of subdivision = ok
            "poor_pct": 0.4      # 40% of subdivision = poor
        }
    )
    
    singles = Drill(
        id="singles_140",
        name="Single Stroke Roll",
        tempo_bpm=140,
        subdivision=4,
        beats_per_bar=4,
        bars=4,
        stickings=["R", "L", "R", "L", "R", "L", "R", "L"],
        accents=[1, 0, 1, 0, 1, 0, 1, 0],
        velocity_targets={
            "accent": 95,
            "tap": 35,
            "tolerance": 20
        },
        timing={
            "perfect_pct": 0.1,  # 10% of subdivision = perfect
            "ok_pct": 0.25,      # 25% of subdivision = ok
            "poor_pct": 0.4      # 40% of subdivision = poor
        }
    )
    
    doubles = Drill(
        id="doubles_100",
        name="Double Stroke Roll",
        tempo_bpm=100,
        subdivision=4,
        beats_per_bar=4,
        bars=4,
        stickings=["R", "R", "L", "L", "R", "R", "L", "L"],
        accents=[1, 0, 1, 0, 1, 0, 1, 0],
        velocity_targets={
            "accent": 90,
            "tap": 30,
            "tolerance": 25
        },
        timing={
            "perfect_pct": 0.1,  # 10% of subdivision = perfect
            "ok_pct": 0.25,      # 25% of subdivision = ok
            "poor_pct": 0.4      # 40% of subdivision = poor
        }
    )
    
    drills_db[paradiddle.id] = paradiddle
    drills_db[singles.id] = singles
    drills_db[doubles.id] = doubles

# Seed drills on startup
seed_default_drills()

@app.get("/")
async def root():
    return {"message": "Drum Trainer API", "version": "0.1.0"}

@app.get("/v1/drills", response_model=DrillList)
async def get_drills():
    """Get all available drills"""
    return DrillList(
        drills=list(drills_db.values()),
        total=len(drills_db)
    )

@app.get("/v1/drills/{drill_id}", response_model=Drill)
async def get_drill(drill_id: str):
    """Get a specific drill by ID"""
    if drill_id not in drills_db:
        raise HTTPException(status_code=404, detail="Drill not found")
    return drills_db[drill_id]

@app.post("/v1/session", response_model=Session)
async def create_session(session_data: SessionCreate):
    """Create a new practice session"""
    if session_data.drill_id not in drills_db:
        raise HTTPException(status_code=404, detail="Drill not found")
    
    # Create session with custom tempo if provided
    session_id = str(uuid.uuid4())
    session = Session(
        id=session_id,
        drill_id=session_data.drill_id,
        started_at=datetime.now(timezone.utc),
        client_latency_ms=session_data.client_latency_ms,
        input_type=session_data.input_type,
        custom_tempo_bpm=session_data.custom_tempo_bpm
    )
    
    # Store session
    sessions_db[session_id] = session
    
    # Create analyzer for this session
    drill = drills_db[session_data.drill_id]
    client_offset = session_data.client_latency_ms or 0.0
    analyzer = DrumAnalyzer(drill, client_offset)
    analyzers_db[session_id] = analyzer
    
    return session

@app.get("/v1/session/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get session information"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions_db[session_id]

@app.websocket("/v1/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time drum analysis"""
    await websocket.accept()
    
    # Validate session
    if session_id not in sessions_db:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    if session_id not in analyzers_db:
        await websocket.close(code=4004, reason="Analyzer not found")
        return
    
    session = sessions_db[session_id]
    analyzer = analyzers_db[session_id]
    drill = drills_db[session.drill_id]
    
    # Create metronome for this session
    metronome = Metronome(drill, session.custom_tempo_bpm)
    metronomes_db[session_id] = metronome
    
    try:
        # Send session start info
        await websocket.send_json({
            "type": "session_start",
            "session_id": session_id,
            "drill": {
                "id": drill.id,
                "name": drill.name,
                "tempo_bpm": drill.tempo_bpm,
                "custom_tempo_bpm": session.custom_tempo_bpm,
                "effective_tempo_bpm": metronome.effective_tempo,
                "subdivision": drill.subdivision,
                "beats_per_bar": drill.beats_per_bar,
                "bars": drill.bars
            },
            "server_start_time": datetime.now(timezone.utc).isoformat()
        })
        
        # Send initial metronome state
        metronome_state = MetronomeState(
            is_playing=False,
            current_beat=0,
            current_subdivision=0,
            tempo_bpm=metronome.effective_tempo,
            subdivision=drill.subdivision,
            beats_per_bar=drill.beats_per_bar
        )
        await websocket.send_json(metronome_state.model_dump())
        
        # Main message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Validate message
                try:
                    hit_event = HitEvent(**message)
                except ValidationError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Invalid message format: {str(e)}"
                    })
                    continue
                
                # Process based on type
                if hit_event.type == "midi":
                    try:
                        feedback = analyzer.process_midi_hit(hit_event)
                        await websocket.send_json(feedback.model_dump())
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Error processing MIDI hit: {str(e)}"
                        })
                
                elif hit_event.type == "audio":
                    # TODO: Implement audio processing
                    feedback = analyzer.process_audio_frame(hit_event)
                    if feedback:
                        await websocket.send_json(feedback.model_dump())
                
                elif hit_event.type == "metronome_control":
                    # Handle metronome control
                    if hit_event.metronome_action == "start":
                        await metronome.start(websocket)
                    elif hit_event.metronome_action == "stop":
                        await metronome.stop()
                    elif hit_event.metronome_action == "reset":
                        await metronome.reset()
                    elif hit_event.metronome_action == "update_tempo" and hit_event.custom_tempo_bpm is not None:
                        await metronome.update_tempo(hit_event.custom_tempo_bpm)
                    
                    # Send updated metronome state
                    metronome_state = MetronomeState(
                        is_playing=metronome.is_playing,
                        current_beat=metronome.current_beat,
                        current_subdivision=metronome.current_subdivision,
                        tempo_bpm=metronome.effective_tempo,  # Use effective tempo instead of drill tempo
                        subdivision=drill.subdivision,
                        beats_per_bar=drill.beats_per_bar
                    )
                    await websocket.send_json(metronome_state.model_dump())
                
                elif hit_event.type == "calibration":
                    # Handle latency calibration
                    if "client_offset_ms" in message:
                        new_offset = message["client_offset_ms"]
                        analyzer.update_client_offset(new_offset)
                        await websocket.send_json({
                            "type": "calibration_update",
                            "client_offset_ms": new_offset
                        })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"Error in WebSocket for session {session_id}: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
    finally:
        # Clean up metronome
        if session_id in metronomes_db:
            await metronomes_db[session_id].stop()
            del metronomes_db[session_id]

@app.post("/v1/take/{session_id}/finalize")
async def finalize_take(session_id: str):
    """Finalize a session and get final metrics"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_id not in analyzers_db:
        raise HTTPException(status_code=404, detail="Analyzer not found")
    
    # Get final metrics
    analyzer = analyzers_db[session_id]
    metrics = analyzer.get_final_metrics()
    
    # Update session status
    sessions_db[session_id].status = "completed"
    
    # Clean up analyzer
    del analyzers_db[session_id]
    
    return {
        "session_id": session_id,
        "metrics": metrics.model_dump(),
        "finished_at": datetime.now(timezone.utc).isoformat()
    }

@app.delete("/v1/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session and clean up resources"""
    if session_id in sessions_db:
        del sessions_db[session_id]
    
    if session_id in analyzers_db:
        del analyzers_db[session_id]
    
    if session_id in metronomes_db:
        await metronomes_db[session_id].stop()
        del metronomes_db[session_id]
    
    return {"message": "Session cleared"}

@app.post("/v1/drills/{drill_id}/tempo")
async def update_drill_tempo(drill_id: str, tempo_update: DrillTempoUpdate):
    """Update the default tempo of a drill"""
    if drill_id not in drills_db:
        raise HTTPException(status_code=404, detail="Drill not found")
    
    drill = drills_db[drill_id]
    
    # Create updated drill with new tempo
    updated_drill = Drill(
        **drill.model_dump(),
        tempo_bpm=tempo_update.new_tempo_bpm
    )
    
    # Update the drill in the database
    drills_db[drill_id] = updated_drill
    
    return {
        "message": f"Drill tempo updated to {tempo_update.new_tempo_bpm} BPM",
        "drill": updated_drill
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
