# Drum Trainer

A real-time drum timing and dynamics analysis application that provides instant feedback on your drumming performance.

## Features

- **Real-time MIDI Analysis**: Connect your electronic drum kit or MIDI controller for instant timing feedback
- **Diamond Scoring System**: Four-axis scoring (timing accuracy, timing consistency, dynamics accuracy, dynamics consistency)
- **Pre-built Drills**: Includes paradiddles, single stroke rolls, and double stroke rolls at various tempos
- **Live Feedback**: See your performance metrics update in real-time as you play
- **WebSocket Streaming**: Low-latency communication between frontend and backend

## Architecture

The application follows a Python-first architecture with a lightweight React frontend:

- **Backend**: FastAPI with WebSocket support for real-time communication
- **Analyzer**: Pure Python timing and dynamics analysis engine
- **Frontend**: React with WebMIDI support for device input
- **Communication**: WebSocket for low-latency bidirectional data flow

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- A MIDI device (electronic drum kit, MIDI controller, etc.)

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the backend server**:
   ```bash
   cd app
   python main.py
   ```
   
   The API will be available at `http://localhost:8000`

3. **Test the analyzer** (optional):
   ```bash
   python test_analyzer.py
   ```

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```
   
   The frontend will be available at `http://localhost:3000`

## Usage

1. **Connect MIDI Device**: Connect your electronic drum kit or MIDI controller to your computer
2. **Select a Drill**: Choose from the available rudiments and tempos
3. **Start Session**: Click "Start MIDI Session" to begin practicing
4. **Play**: Hit your drums/controller and see real-time feedback
5. **Review**: Monitor your timing accuracy, dynamics, and overall diamond score

## API Endpoints

### HTTP Endpoints

- `GET /v1/drills` - List all available drills
- `GET /v1/drills/{drill_id}` - Get specific drill details
- `POST /v1/session` - Create a new practice session
- `GET /v1/session/{session_id}` - Get session information
- `POST /v1/take/{session_id}/finalize` - Complete session and get final metrics

### WebSocket Endpoints

- `WS /v1/stream/{session_id}` - Real-time streaming for hit analysis

## Data Models

### Drill Structure

```json
{
  "id": "paradiddle_120",
  "name": "Single Paradiddle",
  "tempo_bpm": 120,
  "subdivision": 4,
  "beats_per_bar": 4,
  "bars": 4,
  "stickings": ["R", "L", "R", "R", "L", "R", "L", "L"],
  "accents": [1, 0, 0, 0, 1, 0, 0, 0],
  "velocity_targets": {
    "accent": 100,
    "tap": 40,
    "tolerance": 15
  },
  "timing": {
    "ok_ms": 20,
    "good_ms": 10,
    "bad_ms": 40
  }
}
```

### Hit Feedback

```json
{
  "type": "hit_feedback",
  "slot_idx": 37,
  "delta_ms": -12.4,
  "velocity": 93,
  "velocity_target": 100,
  "timing_score": 0.86,
  "dyn_score": 0.78,
  "rolling": {
    "timing": 0.83,
    "dynamics": 0.80,
    "diamond": 0.81
  }
}
```

## Diamond Scoring System

The diamond score combines four performance metrics using a weighted geometric mean:

1. **Timing Accuracy** (35%): How close your hits are to the grid
2. **Timing Consistency** (25%): How consistent your timing is (lower variance = higher score)
3. **Dynamics Accuracy** (25%): How well you match target velocities
4. **Dynamics Consistency** (15%): How consistent your dynamics are

## Development

### Project Structure

```
drum-trainer/
├── app/                    # Python backend
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── models.py          # Pydantic data models
│   └── analyzer.py        # Core analysis engine
├── frontend/              # React frontend
│   ├── src/
│   │   ├── App.tsx        # Main application component
│   │   ├── store.ts       # Zustand state management
│   │   └── types.ts       # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt        # Python dependencies
├── test_analyzer.py       # Analyzer test script
└── README.md
```

### Adding New Drills

To add new drills, modify the `seed_default_drills()` function in `app/main.py`:

```python
new_drill = Drill(
    id="your_drill_id",
    name="Your Drill Name",
    tempo_bpm=140,
    subdivision=4,
    beats_per_bar=4,
    bars=4,
    stickings=["R", "L", "R", "L"],
    accents=[1, 0, 1, 0],
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
```

### Testing

Run the analyzer test:
```bash
python test_analyzer.py
```

Run the backend tests (when implemented):
```bash
pytest
```

## Roadmap

- [ ] Audio input support with onset detection
- [ ] Metronome with visual countdown
- [ ] Advanced visualization (scatter plots, velocity bars)
- [ ] Session history and progress tracking
- [ ] User accounts and drill customization
- [ ] Export performance data
- [ ] Mobile app support
