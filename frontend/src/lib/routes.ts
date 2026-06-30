/**
 * Route registry — single source of truth for the top-level
 * navigation routes in the Vajra.Stream app.
 *
 * Both MainLayout (which renders the menu in the header) and
 * App.jsx (which renders the <Route> elements) import from
 * here. Adding a new route means adding one entry to ROUTES
 * and one component mapping in App.jsx; the menu picks it up
 * automatically.
 *
 * Each entry has:
 *   key:    URL slug used in <Route path> and as the menu key
 *   label:  Display text shown in the header menu
 *   icon:   The lucide-react icon component to render
 *
 * The component-to-route mapping (what React component renders
 * for each route) stays in App.jsx because each route has
 * different prop requirements (some need audioSpectrum, some
 * need sessions, etc.). Keeping that coupling in App.jsx where
 * the state lives avoids prop-drilling.
 *
 * ------------------------------------------------------------------
 * UI rework 2026-06-20 (12 → 7 grouped routes):
 *   Practice   — tabs: Sanctuary / 88 Buddhas / Meditation / Visualizer
 *   Operations — tabs: Operations / Broadcast
 *   Settings   — tabs: LLM Providers / TTS
 * Legacy flat routes (/sanctuary, /buddhas, /meditation, /visualizers,
 * /broadcast, /tts) redirect to their new grouped home via <Navigate>
 * in App.tsx so old bookmarks keep working.
 */
import {
  LayoutDashboard,
  Compass,
  Clock,
  FileText,
  BookOpen,
  Settings,
  Heart,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

export interface RouteEntry {
  key: string;
  label: string;
  icon: LucideIcon;
}

export const ROUTES: RouteEntry[] = [
  { key: 'command-center', label: 'Command Center', icon: LayoutDashboard },
  { key: 'practice', label: 'Practice', icon: Heart },
  { key: 'practices', label: 'Practice Library', icon: Sparkles },
  { key: 'astrology', label: 'Cosmic Clock', icon: Clock },
  { key: 'outlook', label: 'Outlook', icon: FileText },
  { key: 'operations', label: 'Operations', icon: Compass },
  { key: 'grimoire', label: 'Grimoire', icon: BookOpen },
  { key: 'settings', label: 'Settings', icon: Settings },
];

export const DEFAULT_ROUTE = 'command-center';

export function getRouteByKey(key: string): RouteEntry | undefined {
  return ROUTES.find((r) => r.key === key);
}
