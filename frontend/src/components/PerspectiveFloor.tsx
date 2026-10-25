import React from 'react';
import { AgentPalette } from '../types/agent';

interface PerspectiveFloorProps {
  palette: AgentPalette;
}

export const PerspectiveFloor: React.FC<PerspectiveFloorProps> = ({ palette }) => {
  return (
    <div className="absolute inset-x-0 bottom-0 h-[40%] pointer-events-none overflow-hidden z-0">
      {/* Oval contact glow directly under the sphere */}
      <div
        className="absolute left-1/2 -translate-x-1/2 top-[10%] w-[340px] sm:w-[480px] h-[90px] rounded-[100%] blur-[45px] opacity-35 transition-colors duration-700"
        style={{
          background: `radial-gradient(ellipse at center, ${palette.primary}20 0%, #ECECFA 50%, transparent 80%)`,
        }}
      />
    </div>
  );
};
