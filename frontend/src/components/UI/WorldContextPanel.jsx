/**
 * World Context Panel — real-world event and crisis monitor.
 * Displays GDACS disasters, ReliefWeb crises, and RSS news for
 * blessing targeting. Create populations from current events.
 * @component
 */
import React, { useState, useEffect } from 'react';
import { Globe, AlertTriangle, Heart, Moon, Sun, Compass, RefreshCw, Loader2, Radio } from 'lucide-react';
const SEVERITY_COLORS = {
  critical: 'text-red-400 bg-red-950/40 border-red-500/30',
  high: 'text-orange-400 bg-orange-950/40 border-orange-500/30',
  medium: 'text-yellow-400 bg-yellow-950/40 border-yellow-500/30',
  low: 'text-green-400 bg-green-950/40 border-green-500/30',
};

export default function WorldContextPanel() {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchContext = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/operator/world-context`);
      if (res.ok) {
        const data = await res.json();
        setContext(data);
      } else {
        setError('Unable to fetch world context');
      }
    } catch {
      setError('Network error — operator may be offline');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchContext();
    const interval = setInterval(fetchContext, 300000); // every 5 min
    return () => clearInterval(interval);
  }, []);

  if (loading && !context) {
    return (
      <div className="bg-gray-900 rounded-lg border border-indigo-500/30 p-4">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading world context...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-indigo-500/30 overflow-hidden">
      <div className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 p-3 border-b border-emerald-500/20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-emerald-300">World Context</h3>
        </div>
        <button onClick={fetchContext} className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Refresh">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error ? (
        <div className="p-4 text-center text-gray-500 text-xs">{error}</div>
      ) : context ? (
        <div className="p-3 space-y-3">
          {/* Celestial timing */}
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 bg-gray-800 px-2.5 py-1.5 rounded-lg border border-gray-700">
              <Compass className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-gray-300">{context.planetary_hour || '?'} hour</span>
            </div>
            <div className="flex items-center gap-1.5 bg-gray-800 px-2.5 py-1.5 rounded-lg border border-gray-700">
              <Sun className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-gray-300">{context.day_ruler || '?'} day</span>
            </div>
          </div>

          {/* Summary */}
          {context.summary && (
            <div className="text-xs text-gray-400 bg-gray-800/50 rounded-lg p-2.5 border border-gray-700/50 leading-relaxed">
              {context.summary}
            </div>
          )}

          {/* Events */}
          {context.events && context.events.length > 0 && (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {context.events.slice(0, 8).map((evt, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 p-2 rounded-lg border text-xs ${SEVERITY_COLORS[evt.severity] || SEVERITY_COLORS.medium}`}
                >
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <div className="font-medium truncate">{evt.title}</div>
                    {evt.location && (
                      <div className="text-[10px] opacity-70 mt-0.5">{evt.location}</div>
                    )}
                  </div>
                  <span className="text-[10px] uppercase font-mono flex-shrink-0 opacity-60">{evt.severity}</span>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {(!context.events || context.events.length === 0) && (
            <div className="text-center py-6 text-gray-500 text-xs">
              <Heart className="w-6 h-6 mx-auto mb-2 opacity-30" />
              No active crises detected. The world is at peace in this moment.
            </div>
          )}

          {/* Operator note */}
          <div className="text-[10px] text-gray-600 italic text-center pt-1 border-t border-gray-800">
            Context auto-refreshes every 5 min · Data from GDACS & ReliefWeb
          </div>
        </div>
      ) : null}
    </div>
  );
}
