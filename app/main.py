import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .models import Drill, SessionCreate, Session, HitEvent, HitFeedback, DrillList
from .analyzer import DrumAnalyzer

# In-memory storage for MVP (replace with database later)
drills_db: Dict[str, Drill] = {}
sessions_db: Dict[str, Session] = {}
analyzers_db: Dict[str, DrumAnalyzer] = {}

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
            "ok_ms": 20,
            "good_ms": 10,
            "bad_ms": 40
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
            "ok_ms": 25,
            "good_ms": 15,
            "bad_ms": 50
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
            "ok_ms": 30,
            "good_ms": 20,
            "bad_ms": 60
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
    # Validate drill exists
    if session_data.drill_id not in drills_db:
        raise HTTPException(status_code=404, detail="Drill not found")
    
    # Create session
    session_id = str(uuid.uuid4())
    session = Session(
        id=session_id,
        drill_id=session_data.drill_id,
        started_at=datetime.now(timezone.utc),
        client_latency_ms=session_data.client_latency_ms,
        input_type=session_data.input_type
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
    
    try:
        # Send session start info
        drill = drills_db[session.drill_id]
        await websocket.send_json({
            "type": "session_start",
            "session_id": session_id,
            "drill": {
                "id": drill.id,
                "name": drill.name,
                "tempo_bpm": drill.tempo_bpm,
                "subdivision": drill.subdivision,
                "beats_per_bar": drill.beats_per_bar,
                "bars": drill.bars
            },
            "server_start_time": datetime.now(timezone.utc).isoformat()
        })
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
