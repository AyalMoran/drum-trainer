import React, { useEffect, useState, useRef } from 'react';
import { useDrumTrainerStore } from './store';
import { Drill } from './types';
import GradientText from './components/GradientText';
import './App.css';

function App() {
  const {
    drills,
    selectedDrill,
    currentSession,
    isConnected,
    hitHistory,
    currentRolling,
    midiAccess,
    midiInputs,
    setDrills,
    selectDrill,
    createSession,
    connectWebSocket,
    clearSession,
    setMidiAccess,
    setMidiInputs,
  } = useDrumTrainerStore();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Refs to prevent duplicate effect runs
  const drillsFetchedRef = useRef(false);
  const midiSetupRef = useRef(false);
  
  // Keyboard simulation for MIDI drum strokes
  const keyboardMidiMap = useRef(new Map([
    ['KeyA', { note: 36, name: 'Bass Drum' }],      // A key = Bass Drum
    ['KeyS', { note: 38, name: 'Snare Drum' }],     // S key = Snare Drum
    ['KeyD', { note: 42, name: 'Closed Hi-Hat' }],  // D key = Hi-Hat
    ['KeyF', { note: 46, name: 'Open Hi-Hat' }],    // F key = Open Hi-Hat
    ['KeyG', { note: 49, name: 'Crash Cymbal' }],   // G key = Crash
    ['KeyH', { note: 51, name: 'Ride Cymbal' }],    // H key = Ride
    ['KeyJ', { note: 45, name: 'Tom 1' }],          // J key = Tom 1
    ['KeyK', { note: 47, name: 'Tom 2' }],          // K key = Tom 2
    ['KeyL', { note: 48, name: 'Tom 3' }],          // L key = Tom 3
    ['Space', { note: 36, name: 'Bass Drum' }],     // Space = Bass Drum (alternative)
  ]));

  // Load drills on component mount - only run once
  useEffect(() => {
    // Prevent duplicate requests using ref
    if (drillsFetchedRef.current) return;
    drillsFetchedRef.current = true;
    
    const fetchDrills = async () => {
      try {
        const response = await fetch('/v1/drills');
        if (response.ok) {
          const data = await response.json();
          setDrills(data.drills || []);
        } else {
          setError(`Failed to load drills: ${response.status} ${response.statusText}`);
        }
      } catch (error) {
        console.error('Error fetching drills:', error);
        setError('Failed to load drills');
      }
    };

    fetchDrills();
  }, []); // Empty dependency array - only run once

  // Setup MIDI access - only run once
  useEffect(() => {
    // Prevent duplicate setup using ref
    if (midiSetupRef.current) return;
    midiSetupRef.current = true;
    
    const setupMIDI = async () => {
      try {
        if ('requestMIDIAccess' in navigator) {
          const access = await navigator.requestMIDIAccess();
          setMidiAccess(access);
          
          const inputs = Array.from(access.inputs.values());
          setMidiInputs(inputs);
          
          // Setup MIDI message handlers
          inputs.forEach(input => {
            input.onmidimessage = (event) => {
              // Only handle note-on messages with velocity > 0
              if (event.data && event.data[0] === 0x90 && event.data[2] > 0) {
                const hitEvent = {
                  t: performance.now(),
                  type: 'midi' as const,
                  note: event.data[1],
                  velocity: event.data[2],
              };
                
                // Send to WebSocket if connected
                if (isConnected && currentSession) {
                  const ws = useDrumTrainerStore.getState().ws;
                  if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify(hitEvent));
                  }
                }
              }
            };
          });
        }
      } catch (error) {
        console.error('Error setting up MIDI:', error);
        setError('Failed to setup MIDI access');
      }
    };

    setupMIDI();
  }, []); // Empty dependency array - only run once

  // Setup keyboard event listeners for MIDI simulation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      handleKeyboardMidi(event);
    };

    // Add event listener
    document.addEventListener('keydown', handleKeyDown);
    
    // Cleanup function
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [currentSession, isConnected]); // Re-run when session status changes

  const handleStartSession = async (inputType: 'midi' | 'audio') => {
    if (!selectedDrill) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const session = await createSession(selectedDrill.id, inputType);
      connectWebSocket(session.id);
    } catch (error) {
      setError('Failed to start session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopSession = () => {
    clearSession();
  };

  // Handle keyboard events to simulate MIDI drum strokes
  const handleKeyboardMidi = (event: KeyboardEvent) => {
    // Only handle if we have an active session
    if (!currentSession || !isConnected) return;
    
    const keyInfo = keyboardMidiMap.current.get(event.code);
    if (!keyInfo) return;
    
    // Prevent default behavior for drum keys
    event.preventDefault();
    
    // Simulate MIDI note-on event
    const hitEvent = {
      t: performance.now(),
      type: 'midi' as const,
      note: keyInfo.note,
      velocity: 80, // Medium velocity for keyboard hits
    };
    
    // Send to WebSocket if connected
    const ws = useDrumTrainerStore.getState().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(hitEvent));
      console.log(`🎵 Keyboard MIDI: ${keyInfo.name} (Note ${keyInfo.note})`);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>
          <GradientText 
            colors={["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"]}
            animationSpeed={4}
            className="text-6xl font-bold"
          >
            Drum Trainer
          </GradientText>
        </h1>
        <p>Real-time timing and dynamics analysis</p>
      </header>

      <div className="app-container">
        {/* Sidebar */}
        <aside className="sidebar">
          <h2>Select a Drill</h2>
          <div className="drill-grid">
            {drills.map((drill) => (
              <div
                key={drill.id}
                className={`drill-card ${selectedDrill?.id === drill.id ? 'selected' : ''}`}
                onClick={() => selectDrill(drill)}
              >
                <h3>{drill.name}</h3>
                <p>{drill.tempo_bpm} BPM</p>
                <p>{drill.subdivision} subdivisions</p>
                <p>{drill.bars} bars</p>
              </div>
            ))}
          </div>

          {selectedDrill && (
            <div className="session-controls">
              <h3>Start Practice Session</h3>
              <div className="button-group">
                <button
                  onClick={() => handleStartSession('midi')}
                  disabled={isLoading}
                  className="btn btn-primary"
                >
                  {isLoading ? 'Starting...' : 'Start MIDI Session'}
                </button>
                <button
                  onClick={() => handleStartSession('audio')}
                  disabled={isLoading}
                  className="btn btn-secondary"
                >
                  {isLoading ? 'Starting...' : 'Start Audio Session'}
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main className="main-content">
        {error && (
          <div className="error-message">
            {error}
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {!currentSession ? (
          <div className="welcome-section">
            <h2>Welcome to Drum Trainer</h2>
            <p>Select a drill from the sidebar to begin your practice session.</p>
            <div className="welcome-features">
              <div className="feature-card">
                <h3>🎯 Real-time Analysis</h3>
                <p>Get instant feedback on timing and dynamics</p>
              </div>
              <div className="feature-card">
                <h3>🎵 Multiple Inputs</h3>
                <p>Support for MIDI and audio input</p>
              </div>
              <div className="feature-card">
                <h3>📊 Performance Tracking</h3>
                <p>Monitor your progress with detailed metrics</p>
              </div>
              <div className="feature-card">
                <h3>⌨️ Keyboard Controls</h3>
                <p>Use keyboard to simulate drum hits during practice</p>
                <div className="keyboard-controls">
                  <div className="key-row">
                    <span className="key">A</span> Bass Drum
                    <span className="key">S</span> Snare
                    <span className="key">D</span> Hi-Hat
                  </div>
                  <div className="key-row">
                    <span className="key">F</span> Open Hi-Hat
                    <span className="key">G</span> Crash
                    <span className="key">H</span> Ride
                  </div>
                  <div className="key-row">
                    <span className="key">J</span> Tom 1
                    <span className="key">K</span> Tom 2
                    <span className="key">L</span> Tom 3
                  </div>
                  <div className="key-row">
                    <span className="key">Space</span> Bass Drum
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="practice-section">
            <div className="session-info">
              <h2>Practice Session</h2>
              <p>Drill: {selectedDrill?.name}</p>
              <p>Status: {isConnected ? 'Connected' : 'Connecting...'}</p>
              <button onClick={handleStopSession} className="btn btn-danger">
                Stop Session
              </button>
            </div>

            {currentRolling && (
              <div className="rolling-scores">
                <h3>Current Scores</h3>
                <div className="score-grid">
                  <div className="score-item">
                    <span className="score-label">Timing</span>
                    <span className="score-value">{(currentRolling.timing * 100).toFixed(1)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Dynamics</span>
                    <span className="score-value">{(currentRolling.dynamics * 100).toFixed(1)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Diamond</span>
                    <span className="score-value">{(currentRolling.diamond * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            )}

            {hitHistory.length > 0 && (
              <div className="hit-history">
                <h3>Recent Hits</h3>
                <div className="hit-list">
                  {hitHistory.slice(-10).reverse().map((hit, index) => (
                    <div key={index} className="hit-item">
                      <span>Slot {hit.slot_idx}</span>
                      <span>{hit.delta_ms > 0 ? '+' : ''}{hit.delta_ms.toFixed(1)}ms</span>
                      <span>Vel: {hit.velocity}</span>
                      <span>Timing: {(hit.timing_score * 100).toFixed(0)}%</span>
                      <span>Dyn: {(hit.dyn_score * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        </main>
      </div>
    </div>
  );
}

export default App;
