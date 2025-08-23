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
  midiAccess: any | null;
  midiInputs: any[];
  
  // Countdown state
  isCountdownActive: boolean;
  
  // Actions
  setDrills: (drills: Drill[]) => void;
  selectDrill: (drill: Drill) => void;
  createSession: (drillId: string, inputType: 'midi' | 'audio', customTempoBpm?: number) => Promise<Session>;
  connectWebSocket: (sessionId: string) => void;
  disconnectWebSocket: () => void;
  addHitFeedback: (feedback: HitFeedback) => void;
  setMidiAccess: (access: any) => void;
  setMidiInputs: (inputs: any[]) => void;
  setCountdownActive: (active: boolean) => void;
  clearSession: () => void;
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
  isCountdownActive: false,
  
  // Actions
  setDrills: (drills) => set({ drills }),
  
  selectDrill: (drill) => set({ selectedDrill: drill }),
  
  createSession: async (drillId: string, inputType: 'midi' | 'audio', customTempoBpm?: number) => {
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
          custom_tempo_bpm: customTempoBpm, // Pass custom tempo if provided
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
    const { isCountdownActive } = get();
    if (!isCountdownActive) {
      set((state) => ({
        hitHistory: [...state.hitHistory, feedback],
        currentRolling: feedback.rolling,
      }));
    }
  },
  
  setMidiAccess: (access) => set({ midiAccess: access }),
  
  setMidiInputs: (inputs) => set({ midiInputs: inputs }),
  
  setCountdownActive: (active) => set({ isCountdownActive: active }),
  
  clearSession: () => {
    const { disconnectWebSocket } = get();
    disconnectWebSocket();
    set({
      currentSession: null,
      sessionId: null,
      hitHistory: [],
      currentRolling: null,
      isCountdownActive: false,
    });
  },
}));

// Helper function to play click sounds
function playClick(isDownbeat: boolean, isBeat: boolean) {
  // Create audio context for click sounds
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  
  // Create oscillator for click sound
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  
  // Different frequencies for downbeat vs regular beat
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
}
