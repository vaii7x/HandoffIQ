import React from 'react';
import { AgentPalette } from '../types/agent';

interface OverheadSpotlightProps {
  palette: AgentPalette;
}

export const OverheadSpotlight: React.FC<OverheadSpotlightProps> = ({ palette }) => {
  return (
    <div className="absolute top-0 left-0 right-0 h-[380px] pointer-events-none overflow-hidden flex justify-center z-0">
      {/* Conical light beam descending from top */}
      <div
        className="w-[380px] sm:w-[500px] h-full opacity-35 blur-[55px] transition-all duration-700"
        style={{
          background: `radial-gradient(ellipse 70% 50% at 50% 0%, ${palette.primary} 0%, ${palette.secondary} 40%, transparent 80%)`,
        }}
      />
      {/* Top zenith intense highlight */}
      <div
        className="absolute top-0 w-[140px] h-[3px] opacity-75 blur-[2px] transition-colors duration-700"
        style={{
          backgroundColor: palette.primary,
          boxShadow: `0 0 25px 5px ${palette.primary}`,
        }}
      />
    </div>
  );
};
