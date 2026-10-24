import React from 'react';
import { AgentPalette } from '../types/agent';

interface PerspectiveFloorProps {
  palette: AgentPalette;
}

export const PerspectiveFloor: React.FC<PerspectiveFloorProps> = ({ palette }) => {
  return (
    <div className="absolute inset-x-0 bottom-0 h-[48%] pointer-events-none overflow-hidden z-0">
      {/* Oval contact glow directly under the sphere */}
      <div
        className="absolute left-1/2 -translate-x-1/2 top-[5%] w-[320px] sm:w-[460px] h-[90px] rounded-[100%] blur-[40px] opacity-40 transition-colors duration-700"
        style={{
          background: `radial-gradient(ellipse at center, ${palette.primary} 0%, ${palette.secondary} 50%, transparent 80%)`,
        }}
      />

      {/* Subtle perspective grid */}
      <div
        className="w-full h-full opacity-15"
        style={{
          perspective: '600px',
        }}
      >
        <div
          className="w-full h-[200%] origin-bottom"
          style={{
            transform: 'rotateX(72deg) translateY(-30%)',
            backgroundImage: `
              linear-gradient(to right, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(255, 255, 255, 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '48px 48px',
            maskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.4) 40%, rgba(0,0,0,0) 80%)',
            WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.4) 40%, rgba(0,0,0,0) 80%)',
          }}
        />
      </div>

      {/* Vignette fade to dark bottom edge */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black via-black/60 to-transparent" />
    </div>
  );
};
