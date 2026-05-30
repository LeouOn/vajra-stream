/**
 * Rate Dial — interactive SVG radionics rate knob (0–100).
 * Draggable dial with haptic audio feedback and value label.
 * @component
 * @param {{ value, onChange, label, min, max, step, size }} props
 */
import React, { useRef, useState, useCallback, useEffect, useId } from 'react';
import { audioFeedback } from '../../utils/audioFeedback';

const SWEEP_DEGREES = 270;
const START_ANGLE = 225;

const RateDial = ({
  value = 50,
  onChange,
  min = 0,
  max = 100,
  label = '',
  color = '#8a2be2',
  size = 120,
  disabled = false,
  showValue = true
}) => {
  const dialRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hovered, setHovered] = useState(false);
  const filterId = useId();

  const center = size / 2;
  const arcRadius = size / 2 - 15;
  const arcR = arcRadius * 0.9;

  const valueToAngle = useCallback((val) => {
    const normalized = (val - min) / (max - min);
    return START_ANGLE - normalized * SWEEP_DEGREES;
  }, [min, max]);

  const computeValueFromPointer = useCallback((clientX, clientY) => {
    if (!dialRef.current) return value;

    const rect = dialRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;

    const angle = Math.atan2(cy - clientY, clientX - cx) * (180 / Math.PI);
    const normalizedAngle = ((angle % 360) + 360) % 360;

    let sweep = ((START_ANGLE - normalizedAngle) % 360 + 360) % 360;

    if (sweep > SWEEP_DEGREES) {
      sweep = (sweep - SWEEP_DEGREES) < (360 - sweep) ? SWEEP_DEGREES : 0;
    }

    const normalized = sweep / SWEEP_DEGREES;
    return Math.round(min + normalized * (max - min));
  }, [min, max, value]);

  const handleInteraction = useCallback((clientX, clientY) => {
    if (disabled) return;
    const newValue = computeValueFromPointer(clientX, clientY);
    const clampedValue = Math.max(min, Math.min(max, newValue));
    if (onChange) {
      onChange(clampedValue);
    }
    audioFeedback.playDialAdjust(clampedValue, min, max);
  }, [disabled, onChange, computeValueFromPointer, min, max]);

  const handleMouseDown = useCallback((e) => {
    if (disabled) return;
    setIsDragging(true);
    handleInteraction(e.clientX, e.clientY);
  }, [disabled, handleInteraction]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    handleInteraction(e.clientX, e.clientY);
  }, [isDragging, handleInteraction]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e) => {
    if (disabled) return;
    e.preventDefault();
    const delta = e.deltaY > 0 ? -1 : 1;
    const step = (max - min) / 100;
    const newValue = Math.max(min, Math.min(max, value + delta * step));
    const roundedValue = Math.round(newValue);
    if (onChange) onChange(roundedValue);
    audioFeedback.playDialAdjust(roundedValue, min, max);
  }, [disabled, value, min, max, onChange]);

  const handleKeyDown = useCallback((e) => {
    if (disabled) return;
    let delta = 0;
    switch (e.key) {
      case 'ArrowUp':
      case 'ArrowRight':
        delta = 1;
        break;
      case 'ArrowDown':
      case 'ArrowLeft':
        delta = -1;
        break;
      case 'PageUp':
        delta = 10;
        break;
      case 'PageDown':
        delta = -10;
        break;
      case 'Home':
        if (onChange) onChange(min);
        audioFeedback.playDialAdjust(min, min, max);
        e.preventDefault();
        return;
      case 'End':
        if (onChange) onChange(max);
        audioFeedback.playDialAdjust(max, min, max);
        e.preventDefault();
        return;
      default:
        return;
    }
    e.preventDefault();
    const newValue = Math.max(min, Math.min(max, value + delta));
    if (onChange) onChange(newValue);
    audioFeedback.playDialAdjust(newValue, min, max);
  }, [disabled, value, min, max, onChange]);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const valueNormalized = (value - min) / (max - min);
  const needleAngle = valueToAngle(value);
  const needleRad = (needleAngle * Math.PI) / 180;

  const needleX = center + arcRadius * 0.8 * Math.cos(needleRad);
  const needleY = center - arcRadius * 0.8 * Math.sin(needleRad);

  const startRad = (START_ANGLE * Math.PI) / 180;
  const startX = center + arcR * Math.cos(startRad);
  const startY = center - arcR * Math.sin(startRad);

  const endRad = ((START_ANGLE - SWEEP_DEGREES) * Math.PI) / 180;
  const bgEndX = center + arcR * Math.cos(endRad);
  const bgEndY = center - arcR * Math.sin(endRad);

  const activeEndX = center + arcR * Math.cos(needleRad);
  const activeEndY = center - arcR * Math.sin(needleRad);

  const sweepDeg = valueNormalized * SWEEP_DEGREES;
  const largeArc = sweepDeg > 180 ? 1 : 0;

  const tickMarks = [];
  for (let i = min; i <= max; i += 10) {
    const angle = valueToAngle(i);
    const rad = (angle * Math.PI) / 180;
    const isMajor = i % 20 === 0;
    const innerR = arcRadius * (isMajor ? 0.75 : 0.82);
    const outerR = arcRadius * 0.9;

    tickMarks.push({
      x1: center + innerR * Math.cos(rad),
      y1: center - innerR * Math.sin(rad),
      x2: center + outerR * Math.cos(rad),
      y2: center - outerR * Math.sin(rad),
      isMajor,
      value: i
    });
  }

  const glowRadius = 25 + valueNormalized * 20;

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        ref={dialRef}
        className={`relative cursor-pointer select-none ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        style={{ width: size, height: size }}
        onMouseDown={handleMouseDown}
        onWheel={handleWheel}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => {
          setHovered(true);
          audioFeedback.playTick();
        }}
        onMouseLeave={() => setHovered(false)}
        role="slider"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-label={label || `Rate dial: ${value}`}
        tabIndex={disabled ? -1 : 0}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="pointer-events-none"
        >
          <defs>
            <filter id={filterId}>
              <feGaussianBlur stdDeviation={hovered || isDragging ? 4 : 2} result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <path
            d={`M ${startX} ${startY} A ${arcR} ${arcR} 0 1 0 ${bgEndX} ${bgEndY}`}
            fill="none"
            stroke="#1f2937"
            strokeWidth={10}
            strokeLinecap="round"
          />

          {value > min && (
            <path
              d={`M ${startX} ${startY} A ${arcR} ${arcR} 0 ${largeArc} 0 ${activeEndX} ${activeEndY}`}
              fill="none"
              stroke={color}
              strokeWidth={10}
              strokeLinecap="round"
              filter={`url(#${filterId})`}
            />
          )}

          {tickMarks.map((tick, i) => (
            <line
              key={i}
              x1={tick.x1}
              y1={tick.y1}
              x2={tick.x2}
              y2={tick.y2}
              stroke={tick.isMajor ? '#6b7280' : '#4b5563'}
              strokeWidth={tick.isMajor ? 2.5 : 1.5}
            />
          ))}

          {tickMarks.filter(t => t.isMajor).map((tick, i) => {
            const labelR = arcRadius * 0.65;
            const angle = valueToAngle(tick.value);
            const rad = (angle * Math.PI) / 180;
            return (
              <text
                key={i}
                x={center + labelR * Math.cos(rad)}
                y={center - labelR * Math.sin(rad)}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#9ca3af"
                fontSize={9}
                fontFamily="monospace"
              >
                {tick.value}
              </text>
            );
          })}

          <line
            x1={center}
            y1={center}
            x2={needleX}
            y2={needleY}
            stroke={color}
            strokeWidth={2.5}
            strokeLinecap="round"
            filter={`url(#${filterId})`}
          />

          <circle
            cx={center}
            cy={center}
            r={6}
            fill={color}
            filter={`url(#${filterId})`}
          />
          <circle
            cx={center}
            cy={center}
            r={3}
            fill="#fff"
          />
        </svg>

        {(hovered || isDragging) && !disabled && (
          <div
            className="absolute rounded-full pointer-events-none transition-opacity"
            style={{
              left: center - glowRadius,
              top: center - glowRadius,
              width: glowRadius * 2,
              height: glowRadius * 2,
              background: `radial-gradient(circle, ${color}33 0%, transparent 70%)`
            }}
          />
        )}
      </div>

      {showValue && (
        <div className="text-center">
          <span className="text-lg font-bold text-white font-mono">{value}</span>
          {label && (
            <div className="text-xs text-gray-400 mt-0.5">{label}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default RateDial;
