import React from 'react';
import { AgentPalette } from '../types/agent';

interface OverheadSpotlightProps {
  palette: AgentPalette;
}

export const OverheadSpotlight: React.FC<OverheadSpotlightProps> = ({ palette }) => {
  return (
    <div className="absolute top-0 left-0 right-0 h-[380px] pointer-events-none overflow-hidden flex justify-center z-0">
      {/* Soft downward lavender glow */}
      <div
        className="w-[420px] sm:w-[560px] h-full opacity-60 blur-[65px] transition-all duration-700"
        style={{
          background: `radial-gradient(ellipse 70% 50% at 50% 0%, ${palette.primary}18 0%, #ECECFA 40%, transparent 80%)`,
        }}
      />
      {/* Top zenith subtle accent */}
      <div
        className="absolute top-0 w-[140px] h-[2px] opacity-60 blur-[1px] transition-colors duration-700"
        style={{
          backgroundColor: palette.primary,
          boxShadow: `0 0 16px 2px ${palette.primary}40`,
        }}
      />
    </div>
  );
};
