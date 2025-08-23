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
  
  // Metronome state
  const [isMetronomePlaying, setIsMetronomePlaying] = useState(false);
  const [currentBeat, setCurrentBeat] = useState(0);
  const [currentSubdivision, setCurrentSubdivision] = useState(0);
  
  // Tempo customization state
  const [customTempoBpm, setCustomTempoBpm] = useState<number | null>(null);
  const [showTempoCustomization, setShowTempoCustomization] = useState(false);
  
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

  // Handle WebSocket messages for metronome updates
  useEffect(() => {
    if (!isConnected || !currentSession) return;
    
    const ws = useDrumTrainerStore.getState().ws;
    if (!ws) return;
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'metronome_state') {
          setIsMetronomePlaying(message.is_playing);
          setCurrentBeat(message.current_beat);
          setCurrentSubdivision(message.current_subdivision);
        } else if (message.type === 'metronome_tick') {
          setCurrentBeat(message.beat);
          setCurrentSubdivision(message.subdivision);
          
          // Play click sound for immediate audio feedback
          playClickSound(message.is_downbeat, message.is_beat);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.addEventListener('message', handleMessage);
    
    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [isConnected, currentSession]);

  // Simple click sound generation
  const playClickSound = (isDownbeat: boolean, isBeat: boolean) => {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Different frequencies for different beat types
      if (isDownbeat) {
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime); // Higher pitch for downbeat
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      } else if (isBeat) {
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime); // Medium pitch for beat
        gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      } else {
        oscillator.frequency.setValueAtTime(400, audioContext.currentTime); // Lower pitch for subdivision
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      }
      
      // Envelope for click sound
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch (error) {
      console.log('Audio context not available:', error);
    }
  };

  const handleStartSession = async (inputType: 'midi' | 'audio') => {
    if (!selectedDrill) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Always start with default tempo, tempo customization is in metronome section
      const session = await createSession(selectedDrill.id, inputType);
      connectWebSocket(session.id);
      
      // Reset custom tempo to default when starting new session
      setCustomTempoBpm(null);
      setShowTempoCustomization(false);
    } catch (error) {
      setError('Failed to start session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopSession = () => {
    clearSession();
  };

  // Metronome control functions
  const handleStartMetronome = () => {
    if (!currentSession || !isConnected) return;
    
    const ws = useDrumTrainerStore.getState().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const metronomeMessage = {
        t: performance.now(),
        type: 'metronome_control' as const,
        metronome_action: 'start' as const
      };
      ws.send(JSON.stringify(metronomeMessage));
    }
  };

  const handleStopMetronome = () => {
    if (!currentSession || !isConnected) return;
    
    const ws = useDrumTrainerStore.getState().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const metronomeMessage = {
        t: performance.now(),
        type: 'metronome_control' as const,
        metronome_action: 'stop' as const
      };
      ws.send(JSON.stringify(metronomeMessage));
    }
  };

  const handleResetMetronome = () => {
    if (!currentSession || !isConnected) return;
    
    const ws = useDrumTrainerStore.getState().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const metronomeMessage = {
        t: performance.now(),
        type: 'metronome_control' as const,
        metronome_action: 'reset' as const
      };
      ws.send(JSON.stringify(metronomeMessage));
    }
  };

  // Update metronome tempo
  const handleUpdateMetronomeTempo = () => {
    if (!currentSession || !isConnected) return;
    
    const ws = useDrumTrainerStore.getState().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const metronomeMessage = {
        t: performance.now(),
        type: 'metronome_control' as const,
        metronome_action: 'update_tempo' as const,
        custom_tempo_bpm: customTempoBpm
      };
      ws.send(JSON.stringify(metronomeMessage));
      
      // Close the tempo customization panel
      setShowTempoCustomization(false);
    }
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

            {/* Metronome Controls */}
            <div className="metronome-section">
              <h3>Metronome</h3>
              
              {/* Tempo Customization */}
              <div className="tempo-customization">
                <div className="tempo-header">
                  <span className="tempo-label">
                    Tempo: <strong>{customTempoBpm || selectedDrill?.tempo_bpm} BPM</strong>
                    {customTempoBpm && (
                      <span className="default-tempo-note"> (Default: {selectedDrill?.tempo_bpm} BPM)</span>
                    )}
                  </span>
                  <button 
                    onClick={() => setShowTempoCustomization(!showTempoCustomization)}
                    className="btn btn-outline btn-sm"
                  >
                    {showTempoCustomization ? 'Done' : 'Adjust Tempo'}
                  </button>
                </div>
                
                {showTempoCustomization && (
                  <div className="tempo-input-group">
                    <label htmlFor="custom-tempo">Set Tempo (BPM):</label>
                    <div className="tempo-input-container">
                      <input
                        id="custom-tempo"
                        type="number"
                        min="40"
                        max="300"
                        value={customTempoBpm || selectedDrill?.tempo_bpm || ''}
                        onChange={(e) => {
                          const value = parseInt(e.target.value);
                          setCustomTempoBpm(isNaN(value) ? null : value);
                        }}
                        className="tempo-input"
                      />
                      <span className="tempo-unit">BPM</span>
                    </div>
                    <div className="tempo-presets">
                      <button 
                        onClick={() => setCustomTempoBpm((selectedDrill?.tempo_bpm || 120) - 20)}
                        className="btn btn-outline btn-xs"
                        disabled={(selectedDrill?.tempo_bpm || 120) <= 60}
                      >
                        -20
                      </button>
                      <button 
                        onClick={() => setCustomTempoBpm((selectedDrill?.tempo_bpm || 120) - 10)}
                        className="btn btn-outline btn-xs"
                        disabled={(selectedDrill?.tempo_bpm || 120) <= 50}
                      >
                        -10
                      </button>
                      <button 
                        onClick={() => setCustomTempoBpm(selectedDrill?.tempo_bpm || null)}
                        className="btn btn-outline btn-xs"
                      >
                        Default
                      </button>
                      <button 
                        onClick={() => setCustomTempoBpm((selectedDrill?.tempo_bpm || 120) + 10)}
                        className="btn btn-outline btn-xs"
                        disabled={(selectedDrill?.tempo_bpm || 120) >= 290}
                      >
                        +10
                      </button>
                      <button 
                        onClick={() => setCustomTempoBpm((selectedDrill?.tempo_bpm || 120) + 20)}
                        className="btn btn-outline btn-xs"
                        disabled={(selectedDrill?.tempo_bpm || 120) >= 280}
                      >
                        +20
                      </button>
                    </div>
                    
                    <button 
                      onClick={handleUpdateMetronomeTempo}
                      disabled={!isConnected}
                      className="btn btn-primary btn-sm"
                    >
                      Apply Tempo
                    </button>
                  </div>
                )}
              </div>
              
              <div className="metronome-controls">
                <button 
                  onClick={handleStartMetronome} 
                  disabled={!isConnected || isMetronomePlaying}
                  className="btn btn-primary"
                >
                  Start Metronome
                </button>
                <button 
                  onClick={handleStopMetronome} 
                  disabled={!isConnected || !isMetronomePlaying}
                  className="btn btn-secondary"
                >
                  Stop Metronome
                </button>
                <button 
                  onClick={handleResetMetronome} 
                  disabled={!isConnected}
                  className="btn btn-outline"
                >
                  Reset
                </button>
              </div>
              
              {/* Metronome Status */}
              <div className="metronome-status">
                <div className="status-item">
                  <span className="status-label">Status:</span>
                  <span className={`status-value ${isMetronomePlaying ? 'playing' : 'stopped'}`}>
                    {isMetronomePlaying ? 'Playing' : 'Stopped'}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Beat:</span>
                  <span className="status-value">{currentBeat + 1}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Subdivision:</span>
                  <span className="status-value">{currentSubdivision + 1}</span>
                </div>
              </div>
              
              {/* Visual Beat Indicator */}
              {isMetronomePlaying && (
                <div className="beat-indicator">
                  <div className="beat-grid">
                    {Array.from({ length: selectedDrill?.beats_per_bar || 4 }, (_, i) => (
                      <div 
                        key={i} 
                        className={`beat-dot ${i === currentBeat ? 'active' : ''}`}
                      />
                    ))}
                  </div>
                  <div className="subdivision-grid">
                    {Array.from({ length: selectedDrill?.subdivision || 4 }, (_, i) => (
                      <div 
                        key={i} 
                        className={`subdivision-dot ${i === currentSubdivision ? 'active' : ''}`}
                      />
                    ))}
                  </div>
                </div>
              )}
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
                
                {/* Table Headers */}
                <div className="hit-table-headers">
                  <div className="hit-header">Position</div>
                  <div className="hit-header">Timing</div>
                  <div className="hit-header">Velocity</div>
                  <div className="hit-header">Timing Score</div>
                  <div className="hit-header">Dynamics Score</div>
                  <div className="hit-header">Target Velocity</div>
                  <div className="hit-header">Beat Info</div>
                  <div className="hit-header">Quality</div>
                </div>
                
                {/* Hit List */}
                <div className="hit-list">
                  {hitHistory.slice(-15).reverse().map((hit, index) => {
                    // Calculate beat and subdivision info
                    const beat = Math.floor(hit.slot_idx / (selectedDrill?.subdivision || 4)) + 1;
                    const subdivision = (hit.slot_idx % (selectedDrill?.subdivision || 4)) + 1;
                    
                    // Determine timing quality
                    const timingQuality = hit.timing_score >= 0.9 ? 'Perfect' : 
                                       hit.timing_score >= 0.7 ? 'Good' : 
                                       hit.timing_score >= 0.5 ? 'OK' : 'Poor';
                    
                    // Determine dynamics quality
                    const dynamicsQuality = hit.dyn_score >= 0.9 ? 'Perfect' : 
                                          hit.dyn_score >= 0.7 ? 'Good' : 
                                          hit.dyn_score >= 0.5 ? 'OK' : 'Poor';
                    
                    // Overall quality
                    const overallQuality = (hit.timing_score + hit.dyn_score) / 2;
                    const qualityClass = overallQuality >= 0.9 ? 'perfect' : 
                                       overallQuality >= 0.7 ? 'good' : 
                                       overallQuality >= 0.5 ? 'ok' : 'poor';
                    
                    return (
                      <div key={index} className={`hit-item ${qualityClass}`}>
                        <div className="hit-cell position">
                          <div className="slot-info">
                            <span className="slot-number">Slot {hit.slot_idx}</span>
                            <span className="beat-info">Beat {beat}.{subdivision}</span>
                          </div>
                        </div>
                        
                        <div className="hit-cell timing">
                          <div className="timing-detail">
                            <span className="delta-ms">{hit.delta_ms > 0 ? '+' : ''}{hit.delta_ms.toFixed(1)}ms</span>
                            <span className="timing-quality">{timingQuality}</span>
                          </div>
                        </div>
                        
                        <div className="hit-cell velocity">
                          <div className="velocity-detail">
                            <span className="actual-velocity">{hit.velocity || 'N/A'}</span>
                            {hit.velocity_target && (
                              <span className="target-velocity">→ {hit.velocity_target}</span>
                            )}
                          </div>
                        </div>
                        
                        <div className="hit-cell timing-score">
                          <div className="score-bar">
                            <div className="score-fill" style={{width: `${hit.timing_score * 100}%`}}></div>
                            <span className="score-text">{(hit.timing_score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        
                        <div className="hit-cell dynamics-score">
                          <div className="score-bar">
                            <div className="score-fill" style={{width: `${hit.dyn_score * 100}%`}}></div>
                            <span className="score-text">{(hit.dyn_score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        
                        <div className="hit-cell target-velocity">
                          <span className="target-value">{hit.velocity_target || 'N/A'}</span>
                        </div>
                        
                        <div className="hit-cell beat-info">
                          <div className="beat-detail">
                            <span className="beat-number">{beat}</span>
                            <span className="subdivision-number">.{subdivision}</span>
                          </div>
                        </div>
                        
                        <div className="hit-cell quality">
                          <span className={`quality-badge ${qualityClass}`}>
                            {overallQuality >= 0.9 ? '⭐' : 
                             overallQuality >= 0.7 ? '✓' : 
                             overallQuality >= 0.5 ? '○' : '✗'}
                            {overallQuality >= 0.9 ? ' Perfect' : 
                             overallQuality >= 0.7 ? ' Good' : 
                             overallQuality >= 0.5 ? ' OK' : ' Poor'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Summary Stats */}
                <div className="hit-summary">
                  <div className="summary-item">
                    <span className="summary-label">Total Hits:</span>
                    <span className="summary-value">{hitHistory.length}</span>
                  </div>
                  <div className="summary-item">
                    <span className="summary-label">Avg Timing Score:</span>
                    <span className="summary-value">
                      {(hitHistory.reduce((sum, hit) => sum + hit.timing_score, 0) / hitHistory.length * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="summary-label">Avg Dynamics Score:</span>
                    <span className="summary-value">
                      {(hitHistory.reduce((sum, hit) => sum + hit.dyn_score, 0) / hitHistory.length * 100).toFixed(1)}%
                    </span>
                  </div>
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
