import React, { useEffect, useRef, useState } from 'react';

const AudioSpectrum = ({ spectrum, isPlaying, frequency }) => {
  const canvasRef = useRef();
  const animationRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });

  // Update canvas dimensions on resize
  useEffect(() => {
    const handleResize = () => {
      const container = canvasRef.current?.parentElement;
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: container.clientHeight
        });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Draw spectrum
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const { width, height } = dimensions;
    
    // Set canvas size
    canvas.width = width;
    canvas.height = height;
    
    const draw = () => {
      // Clear canvas with fade effect
      ctx.fillStyle = 'rgba(17, 24, 39, 0.1)'; // bg-gray-900 with transparency
      ctx.fillRect(0, 0, width, height);
      
      if (spectrum.length === 0) {
        // Draw placeholder when no spectrum data
        ctx.fillStyle = 'rgba(156, 163, 175, 0.3)'; // text-gray-400
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Waiting for audio data...', width / 2, height / 2);
        return;
      }
      
      // Calculate bar dimensions
      const barCount = Math.min(spectrum.length, 64); // Limit to 64 bars for performance
      const barWidth = width / barCount;
      const barSpacing = barWidth * 0.1; // 10% spacing
      const actualBarWidth = barWidth - barSpacing;
      
      // Draw spectrum bars
      for (let i = 0; i < barCount; i++) {
        const spectrumIndex = Math.floor((i / barCount) * spectrum.length);
        const value = spectrum[spectrumIndex] || 0;
        
        // Calculate bar height
        const barHeight = value * height * 0.8; // 80% of canvas height
        const x = i * barWidth + barSpacing / 2;
        const y = height - barHeight;
        
        // Create gradient for each bar
        const gradient = ctx.createLinearGradient(0, y, 0, height);
        
        // Color based on frequency range
        const hue = (i / barCount) * 0.8 + 0.1; // Cyan to purple range
        const saturation = 0.7 + value * 0.3; // More saturated with higher values
        const lightness = 0.4 + value * 0.2; // Brighter with higher values
        
        gradient.addColorStop(0, `hsla(${hue * 360}, ${saturation * 100}%, ${lightness * 100}%, 0.8)`);
        gradient.addColorStop(0.5, `hsla(${hue * 360}, ${saturation * 100}%, ${lightness * 100}%, 0.6)`);
        gradient.addColorStop(1, `hsla(${hue * 360}, ${saturation * 100}%, ${lightness * 100}%, 0.3)`);
        
        // Draw bar
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, actualBarWidth, barHeight);
        
        // Add glow effect for high values
        if (value > 0.7) {
          ctx.shadowColor = `hsla(${hue * 360}, ${saturation * 100}%, ${lightness * 100}%, 0.8)`;
          ctx.shadowBlur = 10;
          ctx.fillRect(x, y, actualBarWidth, barHeight);
          ctx.shadowBlur = 0;
        }
      }
      
      // Draw frequency indicator
      if (isPlaying && frequency) {
        ctx.fillStyle = 'rgba(0, 188, 212, 0.8)'; // vajra-cyan
        ctx.font = '14px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`${frequency.toFixed(1)} Hz`, 10, 25);
        
        // Draw frequency line on spectrum
        const freqIndex = Math.floor((frequency / 1000) * barCount); // Rough mapping
        if (freqIndex < barCount) {
          const lineX = freqIndex * barWidth + barWidth / 2;
          ctx.strokeStyle = 'rgba(0, 188, 212, 0.5)';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(lineX, 0);
          ctx.lineTo(lineX, height);
          ctx.stroke();
        }
      }
      
      // Draw status indicator
      ctx.fillStyle = isPlaying ? 'rgba(34, 197, 94, 0.8)' : 'rgba(156, 163, 175, 0.8)';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(isPlaying ? 'PLAYING' : 'STOPPED', width - 10, 25);
    };
    
    // Animation loop
    const animate = () => {
      draw();
      animationRef.current = requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [spectrum, isPlaying, frequency, dimensions]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-900 rounded-lg">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ maxWidth: '100%', maxHeight: '100%' }}
      />
    </div>
  );
};

export default AudioSpectrum;