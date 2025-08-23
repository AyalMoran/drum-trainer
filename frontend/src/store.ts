import { create } from 'zustand';
import { Drill, Session, HitFeedback, WebSocketMessage } from './types';

interface DrumTrainerState {
  // Drills
  drills: Drill[];
  selectedDrill: Drill | null;
  
  // Session
  currentSession: Session | null;
  sessionId: string | null;
  
  // WebSocket
  ws: WebSocket | null;
  isConnected: boolean;
  
  // Real-time data
  hitHistory: HitFeedback[];
  currentRolling: {
    timing: number;
    dynamics: number;
    diamond: number;
  } | null;
  
  // MIDI
  midiAccess: WebMidi.MIDIAccess | null;
  midiInputs: WebMidi.MIDIInput[];
  
  // Metronome
  isMetronomePlaying: boolean;
  currentBeat: number;
  currentSubdivision: number;
  metronomeInterval: number | null;
  
  // Actions
  setDrills: (drills: Drill[]) => void;
  selectDrill: (drill: Drill) => void;
  createSession: (drillId: string, inputType: 'midi' | 'audio') => Promise<Session>;
  connectWebSocket: (sessionId: string) => void;
  disconnectWebSocket: () => void;
  addHitFeedback: (feedback: HitFeedback) => void;
  setMidiAccess: (access: WebMidi.MIDIAccess) => void;
  setMidiInputs: (inputs: WebMidi.MIDIInput[]) => void;
  clearSession: () => void;
  startMetronome: () => void;
  stopMetronome: () => void;
  resetMetronome: () => void;
}

export const useDrumTrainerStore = create<DrumTrainerState>((set, get) => ({
  // Initial state
  drills: [],
  selectedDrill: null,
  currentSession: null,
  sessionId: null,
  ws: null,
  isConnected: false,
  hitHistory: [],
  currentRolling: null,
  midiAccess: null,
  midiInputs: [],
  
  // Metronome
  isMetronomePlaying: false,
  currentBeat: 0,
  currentSubdivision: 0,
  metronomeInterval: null,
  
  // Actions
  setDrills: (drills) => set({ drills }),
  
  selectDrill: (drill) => set({ selectedDrill: drill }),
  
  createSession: async (drillId, inputType) => {
    try {
      const response = await fetch('/api/v1/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          drill_id: drillId,
          input_type: inputType,
          client_latency_ms: 0, // Will be calibrated later
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create session');
      }
      
      const session: Session = await response.json();
      set({ currentSession: session, sessionId: session.id });
      return session;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  },
  
  connectWebSocket: (sessionId) => {
    const { disconnectWebSocket } = get();
    disconnectWebSocket();
    
    const ws = new WebSocket(`ws://localhost:8000/v1/stream/${sessionId}`);
    
    ws.onopen = () => {
      set({ ws, isConnected: true });
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        const { addHitFeedback } = get();
        
        if (message.type === 'hit_feedback') {
          addHitFeedback(message);
        } else if (message.type === 'session_start') {
          console.log('Session started:', message);
        } else if (message.type === 'calibration_update') {
          console.log('Calibration updated:', message);
        } else if (message.type === 'error') {
          console.error('WebSocket error:', message.message);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onclose = () => {
      set({ ws: null, isConnected: false });
      console.log('WebSocket disconnected');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      set({ ws: null, isConnected: false });
    };
  },
  
  disconnectWebSocket: () => {
    const { ws } = get();
    if (ws) {
      ws.close();
    }
    set({ ws: null, isConnected: false });
  },
  
  addHitFeedback: (feedback) => {
    set((state) => ({
      hitHistory: [...state.hitHistory, feedback],
      currentRolling: feedback.rolling,
    }));
  },
  
  setMidiAccess: (access) => set({ midiAccess: access }),
  
  setMidiInputs: (inputs) => set({ midiInputs: inputs }),
  
  clearSession: () => {
    const { disconnectWebSocket } = get();
    disconnectWebSocket();
    set({
      currentSession: null,
      sessionId: null,
      hitHistory: [],
      currentRolling: null,
    });
  },
}));
