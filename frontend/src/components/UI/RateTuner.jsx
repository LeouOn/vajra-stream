/**
 * Rate Tuner — multi-dial radionics rate configuration panel.
 * Combines RateDial components with presets, custom saving,
 * broadcasting, and live analysis feedback.
 * @component
 */
import React, { useState, useCallback } from 'react';
import { Sliders, Save, RotateCcw, Search, Star, Play, Square, Zap, ChevronDown, X, Bookmark } from 'lucide-react';
import RateDial from './RateDial';
import { useRateStore, RATE_PRESETS } from '../../stores/rateStore';
import { useUIStore } from '../../stores/uiStore';
import { audioFeedback } from '../../utils/audioFeedback';

const COLORS = ['#8a2be2', '#00bfff', '#ffd700'];

const RateTuner = ({ className = '' }) => {
  const {
    currentRate,
    updateRateValue,
    setRateName,
    setRateCategory,
    setRateDescription,
    saveRate,
    rateHistory,
    customRates,
    searchQuery,
    setSearchQuery,
    searchResults,
    isTuning,
    autoTune,
    setAutoTune,
    loadRate
  } = useRateStore();
  
  const { addToast } = useUIStore();
  
  const [showPresets, setShowPresets] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [numDials, setNumDials] = useState(currentRate.values.length);
  
  const handleValueChange = useCallback((index, value) => {
    updateRateValue(index, value);
  }, [updateRateValue]);
  
  const handlePresetSelect = useCallback((preset) => {
    const rate = {
      values: preset.values,
      name: preset.name,
      category: preset.id,
      description: `${preset.name} rate preset`
    };
    loadRate(rate);
    setNumDials(preset.values.length);
    setShowPresets(false);
    audioFeedback.playSuccess();
    addToast({
      type: 'success',
      title: 'Preset Loaded',
      message: `${preset.name} rate loaded into tuner`,
      duration: 2000
    });
  }, [loadRate, addToast]);
  
  const handleSave = useCallback(() => {
    saveRate();
    audioFeedback.playSuccess();
    addToast({
      type: 'success',
      title: 'Rate Saved',
      message: `"${currentRate.name || 'Unnamed Rate'}" saved to your collection`,
      duration: 3000
    });
  }, [saveRate, currentRate.name, addToast]);
  
  const handleReset = useCallback(() => {
    loadRate({
      values: Array(numDials).fill(50),
      name: '',
      description: '',
      category: ''
    });
    audioFeedback.playClick();
  }, [loadRate, numDials]);
  
  const handleLoadRate = useCallback((rate) => {
    loadRate(rate);
    audioFeedback.playSuccess();
  }, [loadRate]);
  
  const handleAddDial = useCallback(() => {
    if (numDials >= 5) {
      audioFeedback.playError();
      return;
    }
    const newValues = [...currentRate.values, 50];
    loadRate({ ...currentRate, values: newValues });
    setNumDials(numDials + 1);
    audioFeedback.playClick();
  }, [numDials, currentRate, loadRate]);
  
  const handleRemoveDial = useCallback(() => {
    if (numDials <= 2) {
      audioFeedback.playError();
      return;
    }
    const newValues = currentRate.values.slice(0, -1);
    loadRate({ ...currentRate, values: newValues });
    setNumDials(numDials - 1);
    audioFeedback.playClick();
  }, [numDials, currentRate, loadRate]);
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-vajra-purple flex items-center gap-2">
          <Sliders className="w-5 h-5" />
          Rate Tuner
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            onMouseEnter={() => audioFeedback.playTick()}
            className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            title="Reset to defaults"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleSave}
            onMouseEnter={() => audioFeedback.playTick()}
            className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-yellow-400 transition-colors"
            title="Save rate"
          >
            <Bookmark className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Rate Name */}
      <div>
        <input
          type="text"
          value={currentRate.name}
          onChange={(e) => setRateName(e.target.value)}
          placeholder="Rate name..."
          className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
        />
      </div>
      
      {/* Dials - Responsive Grid */}
      <div className="grid grid-cols-3 gap-3 justify-items-center">
        {currentRate.values.slice(0, numDials).map((value, index) => (
          <RateDial
            key={index}
            value={value}
            onChange={(val) => handleValueChange(index, val)}
            label={`Dial ${index + 1}`}
            color={COLORS[index % COLORS.length]}
            size={90}
          />
        ))}
      </div>
      
      {/* Dial count controls */}
      <div className="flex justify-center gap-2">
        <button
          onClick={handleRemoveDial}
          onMouseEnter={() => audioFeedback.playTick()}
          disabled={numDials <= 2}
          className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
        >
          - Remove Dial
        </button>
        <span className="text-xs text-gray-500 self-center">{numDials} dials</span>
        <button
          onClick={handleAddDial}
          onMouseEnter={() => audioFeedback.playTick()}
          disabled={numDials >= 5}
          className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
        >
          + Add Dial
        </button>
      </div>
      
      {/* Rate display */}
      <div className="bg-gray-900/50 rounded-lg p-3 text-center">
        <div className="text-xs text-gray-500 mb-1">Rate Value</div>
        <div className="text-xl font-bold text-white font-mono tracking-wider">
          {currentRate.values.join(' - ')}
        </div>
      </div>
      
      {/* Presets */}
      <div>
        <button
          onClick={() => {
            setShowPresets(!showPresets);
            audioFeedback.playClick();
          }}
          onMouseEnter={() => audioFeedback.playTick()}
          className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <span className="flex items-center gap-2">
            <Star className="w-4 h-4 text-yellow-400" />
            Rate Presets
          </span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showPresets ? 'rotate-180' : ''}`} />
        </button>
        {showPresets && (
          <div className="grid grid-cols-2 gap-2 mt-2">
            {RATE_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handlePresetSelect(preset)}
                onMouseEnter={() => audioFeedback.playTick()}
                className="flex items-center gap-2 px-3 py-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg text-sm text-gray-300 hover:text-white transition-colors text-left"
              >
                <span>{preset.icon}</span>
                <div>
                  <div className="font-medium">{preset.name}</div>
                  <div className="text-xs text-gray-500 font-mono">{preset.values.join('-')}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Auto-tune toggle */}
      <div className="flex items-center justify-between bg-gray-800/50 rounded-lg p-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span className="text-sm text-gray-300">Auto-Tune</span>
        </div>
        <button
          onClick={() => {
            setAutoTune(!autoTune);
            audioFeedback.playClick();
          }}
          onMouseEnter={() => audioFeedback.playTick()}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            autoTune ? 'bg-purple-600' : 'bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              autoTune ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
      
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search rates..."
          className="w-full bg-gray-700/50 border border-gray-600 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
        />
        {searchQuery && (
          <button
            onClick={() => {
              setSearchQuery('');
              audioFeedback.playClick();
            }}
            onMouseEnter={() => audioFeedback.playTick()}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      
      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {searchResults.map((rate, i) => (
            <button
              key={rate.id || i}
              onClick={() => {
                handleLoadRate(rate);
                setSearchQuery('');
              }}
              onMouseEnter={() => audioFeedback.playTick()}
              className="w-full flex items-center justify-between px-3 py-2 bg-gray-700/30 hover:bg-gray-600/30 rounded-lg text-sm text-left transition-colors"
            >
              <div>
                <div className="text-white font-medium">{rate.name || 'Unnamed'}</div>
                {rate.category && <div className="text-xs text-gray-500">{rate.category}</div>}
              </div>
              <div className="text-xs font-mono text-gray-400">{rate.values?.join('-')}</div>
            </button>
          ))}
        </div>
      )}
      
      {/* History toggle */}
      <div>
        <button
          onClick={() => {
            setShowHistory(!showHistory);
            audioFeedback.playClick();
          }}
          onMouseEnter={() => audioFeedback.playTick()}
          className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <span>History ({rateHistory.length})</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showHistory ? 'rotate-180' : ''}`} />
        </button>
        {showHistory && (
          <div className="space-y-1 mt-2 max-h-40 overflow-y-auto">
            {rateHistory.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-4">No rate history yet</p>
            ) : (
              rateHistory.slice(0, 10).map((rate, i) => (
                <button
                  key={rate.id || i}
                  onClick={() => handleLoadRate(rate)}
                  onMouseEnter={() => audioFeedback.playTick()}
                  className="w-full flex items-center justify-between px-3 py-2 bg-gray-700/20 hover:bg-gray-600/30 rounded text-xs text-left transition-colors"
                >
                  <span className="text-gray-300">{rate.name || rate.values.join('-')}</span>
                  <span className="text-gray-500 font-mono">{rate.values.join('-')}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
      
      {/* Saved rates */}
      <div>
        <button
          onClick={() => {
            setShowSaved(!showSaved);
            audioFeedback.playClick();
          }}
          onMouseEnter={() => audioFeedback.playTick()}
          className="w-full flex items-center justify-between px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
        >
          <span className="flex items-center gap-2">
            <Bookmark className="w-4 h-4" />
            Saved ({customRates.length})
          </span>
          <ChevronDown className={`w-4 h-4 transition-transform ${showSaved ? 'rotate-180' : ''}`} />
        </button>
        {showSaved && (
          <div className="space-y-1 mt-2 max-h-40 overflow-y-auto">
            {customRates.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-4">No saved rates yet</p>
            ) : (
              customRates.map((rate, i) => (
                <button
                  key={rate.id || i}
                  onClick={() => handleLoadRate(rate)}
                  onMouseEnter={() => audioFeedback.playTick()}
                  className="w-full flex items-center justify-between px-3 py-2 bg-gray-700/20 hover:bg-gray-600/30 rounded text-xs text-left transition-colors"
                >
                  <div>
                    <span className="text-gray-300">{rate.name || 'Unnamed'}</span>
                    {rate.category && <span className="text-gray-500 ml-2">({rate.category})</span>}
                  </div>
                  <span className="text-gray-500 font-mono">{rate.values.join('-')}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RateTuner;
