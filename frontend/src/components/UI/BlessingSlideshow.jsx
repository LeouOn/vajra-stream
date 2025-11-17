/**
 * Compassionate Blessing Slideshow Component
 *
 * Cycles through photographs of beings, overlaying mantras and
 * positive intentions for rapid blessing transmission.
 *
 * Like a high-speed prayer wheel for visual witness samples.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, Heart, Sparkles, Users, Clock, SkipForward, Info } from 'lucide-react';

const API_BASE = 'http://localhost:8001/api/v1';

const BlessingSlideshow = ({ className = '', onSessionChange = null }) => {
  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Configuration state
  const [directoryPath, setDirectoryPath] = useState('');
  const [selectedMantra, setSelectedMantra] = useState('chenrezig');
  const [customMantra, setCustomMantra] = useState('');
  const [selectedIntentions, setSelectedIntentions] = useState(['love', 'healing', 'peace']);
  const [dedication, setDedication] = useState('May all beings benefit');
  const [repetitionsPerPhoto, setRepetitionsPerPhoto] = useState(108);
  const [displayDuration, setDisplayDuration] = useState(2000);
  const [loopMode, setLoopMode] = useState(true);
  const [rngSessionId, setRngSessionId] = useState('');

  // Current slide state
  const [currentSlide, setCurrentSlide] = useState(null);
  const [currentImage, setCurrentImage] = useState(null);
  const [stats, setStats] = useState(null);

  // Overlay animation state
  const [mantraOpacity, setMantraOpacity] = useState(0);
  const [intentionIndex, setIntentionIndex] = useState(0);
  const [repetitionCount, setRepetitionCount] = useState(0);

  // Available mantras and intentions
  const [mantras, setMantras] = useState([]);
  const [intentions, setIntentions] = useState([]);

  const slideTimer = useRef(null);
  const mantraTimer = useRef(null);
  const intentionTimer = useRef(null);

  // Load mantras and intentions on mount
  useEffect(() => {
    loadMantras();
    loadIntentions();
  }, []);

  const loadMantras = async () => {
    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/info/mantras`);
      const data = await response.json();
      setMantras(data);
    } catch (error) {
      console.error('Failed to load mantras:', error);
    }
  };

  const loadIntentions = async () => {
    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/info/intentions`);
      const data = await response.json();
      setIntentions(data);
    } catch (error) {
      console.error('Failed to load intentions:', error);
    }
  };

  // Create session
  const createSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          directory_path: directoryPath,
          intention_set: {
            primary_mantra: selectedMantra,
            custom_mantra: selectedMantra === 'custom' ? customMantra : null,
            intentions: selectedIntentions,
            dedication: dedication,
            repetitions_per_photo: repetitionsPerPhoto
          },
          loop_mode: loopMode,
          display_duration_ms: displayDuration,
          recursive: false,
          rng_session_id: rngSessionId || null
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setIsActive(true);
        setRepetitionCount(0);
        console.log('Blessing slideshow created:', data);

        // Notify parent if callback provided
        if (onSessionChange) {
          onSessionChange(data.session_id, true);
        }

        // Load first slide
        await loadCurrentSlide(data.session_id);
        startAutoAdvance();
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  // Load current slide
  const loadCurrentSlide = async (sid) => {
    const id = sid || sessionId;
    if (!id) return;

    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/slide/current/${id}`);
      if (response.ok) {
        const data = await response.json();
        setCurrentSlide(data);

        // Load image
        const imgResponse = await fetch(
          `${API_BASE}/blessing-slideshow/photo/${id}/${data.session.current_index}`
        );
        if (imgResponse.ok) {
          const blob = await imgResponse.blob();
          const imageUrl = URL.createObjectURL(blob);
          setCurrentImage(imageUrl);
        }

        // Reset animation counters
        setRepetitionCount(0);
        setIntentionIndex(0);
      }
    } catch (error) {
      console.error('Failed to load slide:', error);
    }
  };

  // Advance to next slide
  const advanceSlide = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${API_BASE}/blessing-slideshow/slide/advance/${sessionId}?record_blessing=true`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        await loadCurrentSlide(sessionId);
        await loadStats();
      }
    } catch (error) {
      console.error('Failed to advance slide:', error);
    }
  };

  // Load stats
  const loadStats = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/session/${sessionId}/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  // Pause session
  const pauseSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/blessing-slideshow/session/${sessionId}/pause`, {
        method: 'POST'
      });
      setIsPaused(true);
      stopAutoAdvance();
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  };

  // Resume session
  const resumeSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/blessing-slideshow/session/${sessionId}/resume`, {
        method: 'POST'
      });
      setIsPaused(false);
      startAutoAdvance();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  };

  // Stop session
  const stopSession = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/blessing-slideshow/session/${sessionId}/stop`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }

      setIsActive(false);
      setIsPaused(false);
      stopAutoAdvance();

      // Notify parent
      if (onSessionChange) {
        onSessionChange(null, false);
      }
    } catch (error) {
      console.error('Failed to stop:', error);
    }
  };

  // Auto-advance timer
  const startAutoAdvance = () => {
    if (slideTimer.current) clearTimeout(slideTimer.current);

    slideTimer.current = setTimeout(async () => {
      await advanceSlide();
      if (isActive && !isPaused) {
        startAutoAdvance();
      }
    }, displayDuration);
  };

  const stopAutoAdvance = () => {
    if (slideTimer.current) {
      clearTimeout(slideTimer.current);
      slideTimer.current = null;
    }
  };

  // Mantra pulsing animation
  useEffect(() => {
    if (!isActive || isPaused || !currentSlide) return;

    // Pulse mantra text
    const pulseMantra = () => {
      setMantraOpacity(prev => (prev === 0 ? 1 : 0));
      setRepetitionCount(prev => {
        const next = prev + 1;
        return next >= repetitionsPerPhoto ? 0 : next;
      });
    };

    // Fast pulsing (subliminal effect)
    mantraTimer.current = setInterval(pulseMantra, 100); // 10 Hz

    return () => {
      if (mantraTimer.current) clearInterval(mantraTimer.current);
    };
  }, [isActive, isPaused, currentSlide, repetitionsPerPhoto]);

  // Intention cycling
  useEffect(() => {
    if (!isActive || isPaused || !currentSlide) return;

    const cycleIntentions = () => {
      setIntentionIndex(prev => (prev + 1) % selectedIntentions.length);
    };

    // Cycle intentions every 500ms
    intentionTimer.current = setInterval(cycleIntentions, 500);

    return () => {
      if (intentionTimer.current) clearInterval(intentionTimer.current);
    };
  }, [isActive, isPaused, currentSlide, selectedIntentions]);

  // Toggle intention selection
  const toggleIntention = (intention) => {
    if (selectedIntentions.includes(intention)) {
      setSelectedIntentions(prev => prev.filter(i => i !== intention));
    } else {
      setSelectedIntentions(prev => [...prev, intention]);
    }
  };

  // Format duration
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`bg-gray-800 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-pink-900/50 to-purple-900/50 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart className="w-6 h-6 text-pink-400" />
            <h2 className="text-xl font-bold text-white">Blessing Slideshow</h2>
          </div>
          {isActive && (
            <div className="flex items-center gap-2 text-sm">
              <Sparkles className="w-4 h-4 text-yellow-400 animate-pulse" />
              <span className="text-yellow-400">Blessings Flowing</span>
            </div>
          )}
        </div>
      </div>

      {/* Configuration (when not active) */}
      {!isActive && (
        <div className="p-6 space-y-6">
          {/* Directory Path */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Photo Directory Path
            </label>
            <input
              type="text"
              value={directoryPath}
              onChange={(e) => setDirectoryPath(e.target.value)}
              placeholder="/path/to/photos"
              className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
            />
            <p className="text-xs text-gray-400 mt-1">
              Directory containing photos of beings to bless
            </p>
          </div>

          {/* Mantra Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Primary Mantra
            </label>
            <select
              value={selectedMantra}
              onChange={(e) => setSelectedMantra(e.target.value)}
              className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
            >
              {mantras.map(mantra => (
                <option key={mantra.type} value={mantra.type}>
                  {mantra.name}
                </option>
              ))}
            </select>
            {selectedMantra === 'custom' && (
              <input
                type="text"
                value={customMantra}
                onChange={(e) => setCustomMantra(e.target.value)}
                placeholder="Enter custom mantra or phrase"
                className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 mt-2 focus:border-purple-500 focus:outline-none"
              />
            )}
          </div>

          {/* Intentions */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Intentions (select multiple)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {intentions.map(intention => (
                <button
                  key={intention.type}
                  onClick={() => toggleIntention(intention.type)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedIntentions.includes(intention.type)
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {intention.name}
                </button>
              ))}
            </div>
          </div>

          {/* Settings Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Repetitions per Photo
              </label>
              <input
                type="number"
                value={repetitionsPerPhoto}
                onChange={(e) => setRepetitionsPerPhoto(parseInt(e.target.value))}
                min="1"
                max="10000"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Display Duration (ms)
              </label>
              <input
                type="number"
                value={displayDuration}
                onChange={(e) => setDisplayDuration(parseInt(e.target.value))}
                min="100"
                max="60000"
                step="100"
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Dedication */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Dedication
            </label>
            <textarea
              value={dedication}
              onChange={(e) => setDedication(e.target.value)}
              rows="2"
              className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none resize-none"
            />
          </div>

          {/* Options */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={loopMode}
                onChange={(e) => setLoopMode(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-300">Loop continuously</span>
            </label>
          </div>

          {/* RNG Integration */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              RNG Session ID (optional)
            </label>
            <input
              type="text"
              value={rngSessionId}
              onChange={(e) => setRngSessionId(e.target.value)}
              placeholder="Link with RNG monitoring"
              className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none text-sm"
            />
          </div>

          {/* Start Button */}
          <button
            onClick={createSession}
            disabled={!directoryPath}
            className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 disabled:from-gray-700 disabled:to-gray-700 text-white py-3 px-4 rounded-lg font-semibold transition-all transform hover:scale-105 disabled:scale-100 flex items-center justify-center gap-2"
          >
            <Heart className="w-5 h-5" />
            Begin Blessing Transmission
          </button>
        </div>
      )}

      {/* Active Slideshow */}
      {isActive && currentSlide && (
        <div>
          {/* Image Display with Overlay */}
          <div className="relative bg-black aspect-video">
            {currentImage && (
              <img
                src={currentImage}
                alt="Being to bless"
                className="w-full h-full object-contain"
              />
            )}

            {/* Mantra Overlay (pulsing) */}
            <div
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
              style={{
                opacity: mantraOpacity,
                transition: 'opacity 50ms'
              }}
            >
              <div className="text-center px-4">
                <div className="text-4xl md:text-6xl font-bold text-white drop-shadow-lg" style={{
                  textShadow: '0 0 20px rgba(255,255,255,0.8), 0 0 40px rgba(255,255,255,0.5)'
                }}>
                  {currentSlide.overlay.mantra_text.split('|')[0]}
                </div>
              </div>
            </div>

            {/* Intention Flash (rotating) */}
            {currentSlide.overlay.intentions.length > 0 && (
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                <div className="text-xl md:text-2xl font-semibold text-center text-white animate-pulse">
                  {currentSlide.overlay.intentions[intentionIndex % currentSlide.overlay.intentions.length]}
                </div>
              </div>
            )}

            {/* Repetition Counter */}
            <div className="absolute top-4 right-4 bg-black/60 px-3 py-1 rounded-full">
              <div className="text-sm font-mono text-yellow-400">
                {repetitionCount} / {currentSlide.overlay.mantra_repetitions}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-800">
              <div
                className="h-full bg-gradient-to-r from-pink-500 to-purple-500 transition-all"
                style={{
                  width: `${currentSlide.progress.percentage}%`
                }}
              />
            </div>
          </div>

          {/* Controls */}
          <div className="p-4 bg-gray-900 border-t border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-300">
                  {currentSlide.photo.filename}
                </span>
              </div>
              <div className="text-sm text-gray-400">
                {currentSlide.progress.current} / {currentSlide.progress.total}
              </div>
            </div>

            <div className="flex gap-2">
              {!isPaused ? (
                <button
                  onClick={pauseSession}
                  className="flex-1 bg-amber-600 hover:bg-amber-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                >
                  <Pause className="w-4 h-4" />
                  Pause
                </button>
              ) : (
                <button
                  onClick={resumeSession}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  Resume
                </button>
              )}

              <button
                onClick={advanceSlide}
                disabled={isPaused}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center gap-2"
              >
                <SkipForward className="w-4 h-4" />
              </button>

              <button
                onClick={stopSession}
                className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center gap-2"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            </div>
          </div>

          {/* Stats */}
          {stats && (
            <div className="p-4 bg-gray-900 border-t border-gray-700">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-400">Photos Blessed</div>
                  <div className="text-xl font-bold text-white">
                    {stats.photos_blessed}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Total Mantras</div>
                  <div className="text-xl font-bold text-purple-400">
                    {stats.total_mantras_repeated.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Duration</div>
                  <div className="text-xl font-bold text-white">
                    {formatDuration(stats.session_duration)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Avg/Photo</div>
                  <div className="text-xl font-bold text-white">
                    {formatDuration(stats.average_time_per_photo)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Final Stats (after stop) */}
      {!isActive && stats && sessionId && (
        <div className="p-6 bg-gradient-to-br from-purple-900/30 to-pink-900/30">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            Session Complete - Merit Dedication
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-gray-800/50 p-3 rounded-lg">
              <div className="text-xs text-gray-400">Total Photos Blessed</div>
              <div className="text-2xl font-bold text-white">{stats.photos_blessed}</div>
            </div>
            <div className="bg-gray-800/50 p-3 rounded-lg">
              <div className="text-xs text-gray-400">Total Mantras</div>
              <div className="text-2xl font-bold text-purple-400">
                {stats.total_mantras_repeated.toLocaleString()}
              </div>
            </div>
          </div>
          <div className="bg-gray-800/50 p-4 rounded-lg text-center">
            <p className="text-white italic mb-2">{dedication}</p>
            <p className="text-sm text-gray-400">
              སེམས་ཅན་ཐམས་ཅད་བདེ་བ་དང་བདེ་བའི་རྒྱུ་དང་ལྡན་པར་གྱུར་ཅིག<br />
              May all sentient beings have happiness and the causes of happiness
            </p>
          </div>
        </div>
      )}

      {/* Info Panel */}
      <div className="p-4 bg-purple-900/20 border-t border-purple-500/30">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <p className="mb-1">
              <strong className="text-purple-400">Blessing Slideshow</strong> - Rapid transmission of mantras and positive intentions.
            </p>
            <p>
              Each photo receives {repetitionsPerPhoto} mantra repetitions plus cycling intentions.
              Like a high-speed prayer wheel for visual witness samples.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlessingSlideshow;
