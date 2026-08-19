/**
 * broadcastStore.ts — Zustand store tracking live and recent healing broadcasts.
 *
 * Populated by `HEALING_BROADCAST_STARTED` WebSocket events. Used by
 * WorldEmanation and other visualization components to render active
 * ripples, flight arcs, and telemetry.
 */
import { create } from 'zustand';

export interface BroadcastEvent {
  id: string;
  target?: string;
  location?: string;
  lat?: number;
  lon?: number;
  frequency_hz?: number;
  frequencies?: number[];
  duration_minutes?: number;
  audio_muted?: boolean;
  receivedAt: number;
  expiresAt: number;
}

export type NewBroadcastInput = Omit<BroadcastEvent, 'id' | 'receivedAt' | 'expiresAt'> & {
  id?: string;
  receivedAt?: number;
  expiresAt?: number;
};

interface BroadcastState {
  recentBroadcasts: BroadcastEvent[];
  push: (event: NewBroadcastInput) => void;
  prune: () => void;
  clear: () => void;
}

const MAX_BROADCASTS = 20;
const DEFAULT_DURATION_MINUTES = 5;

export const useBroadcastStore = create<BroadcastState>((set) => ({
  recentBroadcasts: [],

  push: (event) => {
    const now = Date.now();
    const receivedAt = event.receivedAt ?? now;
    const duration = event.duration_minutes ?? DEFAULT_DURATION_MINUTES;
    const expiresAt = event.expiresAt ?? (receivedAt + Math.max(1, duration) * 60_000);
    const id = event.id ?? `bc_${now}_${Math.random().toString(36).slice(2, 8)}`;

    const fullEvent: BroadcastEvent = {
      ...event,
      id,
      receivedAt,
      expiresAt,
    };

    // Filter out already expired ones, prepend new event, and cap at MAX_BROADCASTS
    set((state) => {
      const active = state.recentBroadcasts.filter((b) => b.expiresAt > now && b.id !== id);
      return {
        recentBroadcasts: [fullEvent, ...active].slice(0, MAX_BROADCASTS),
      };
    });
  },

  prune: () => {
    const now = Date.now();
    set((state) => ({
      recentBroadcasts: state.recentBroadcasts.filter((b) => b.expiresAt > now),
    }));
  },

  clear: () => {
    set({ recentBroadcasts: [] });
  },
}));
