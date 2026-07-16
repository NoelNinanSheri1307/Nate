'use client';

import React, { useEffect, useRef } from 'react';
import { SessionState } from '../../types';

interface WaveformProps {
  state: SessionState;
}

export const Waveform: React.FC<WaveformProps> = ({ state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;
    const waves = [
      { amplitude: 0.8, frequency: 0.05, speed: 0.15, color: '#3B82F6' },
      { amplitude: 0.5, frequency: 0.08, speed: -0.1, color: '#60A5FA' },
      { amplitude: 0.3, frequency: 0.12, speed: 0.2, color: '#2563EB' },
    ];

    const resize = () => {
      canvas.width = canvas.parentElement?.clientWidth || 300;
      canvas.height = canvas.parentElement?.clientHeight || 80;
    };
    
    resize();
    window.addEventListener('resize', resize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      phase += 0.05;

      // Adjust wave params dynamically according to state
      let scaleAmp = 0.1;
      let scaleFreq = 1.0;
      let scaleSpeed = 1.0;

      switch (state) {
        case 'LISTENING':
          scaleAmp = 1.0;
          scaleFreq = 1.5;
          scaleSpeed = 2.0;
          break;
        case 'THINKING':
          scaleAmp = 0.4;
          scaleFreq = 0.8;
          scaleSpeed = 0.5;
          // Render glowing breathing pulse
          const glow = (Math.sin(phase) + 1) / 2;
          ctx.shadowBlur = 15;
          ctx.shadowColor = `rgba(96, 165, 250, ${0.2 + glow * 0.4})`;
          break;
        case 'SPEAKING':
          scaleAmp = 0.85;
          scaleFreq = 0.9;
          scaleSpeed = 1.2;
          break;
        case 'ERROR':
          scaleAmp = 0.25;
          scaleFreq = 2.5;
          scaleSpeed = 3.0;
          // Set red color parameters
          break;
        case 'IDLE':
        default:
          scaleAmp = 0.05;
          scaleFreq = 0.5;
          scaleSpeed = 0.3;
          break;
      }

      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';

      waves.forEach((wave) => {
        ctx.beginPath();
        
        let color = wave.color;
        if (state === 'ERROR') {
          color = '#EF4444'; // Red for error
        } else if (state === 'IDLE') {
          color = '#2A2E38'; // Dim border color for idle
        }

        ctx.strokeStyle = color;

        for (let x = 0; x < width; x += 1) {
          const y =
            centerY +
            Math.sin(x * wave.frequency * scaleFreq + phase * wave.speed * scaleSpeed) *
              wave.amplitude *
              (height * 0.4) *
              scaleAmp *
              // Smooth bounds fade-out
              Math.sin((x / width) * Math.PI);
              
          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      });

      ctx.shadowBlur = 0; // Reset glow
      animationRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [state]);

  return (
    <div className="w-full h-20 relative flex items-center justify-center">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
    </div>
  );
};
