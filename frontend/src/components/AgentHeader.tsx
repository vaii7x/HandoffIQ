import React from 'react';
import { AgentPalette, ScreenId } from '../types/agent';
import { FlaskConical } from 'lucide-react';

interface AgentHeaderProps {
  palette: AgentPalette;
  onSelectScreen?: (screenId: ScreenId) => void;
  activeScreen?: ScreenId;
}

export const AgentHeader: React.FC<AgentHeaderProps> = ({
  palette,
  onSelectScreen,
  activeScreen,
}) => {
  return (
    <header className="relative z-10 pt-5 pb-2 px-4 max-w-4xl mx-auto flex items-center justify-between gap-3">
      {/* Left horizontal line */}
      <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent to-white/20" />

      {/* Center Wordmark + Navigation */}
      <div className="flex items-center gap-3 select-none">
        <div
          onClick={() => onSelectScreen?.('research')}
          className="flex items-center gap-1 cursor-pointer group"
          title="Return to agent workflow"
        >
          <h1 className="text-xs sm:text-sm font-semibold tracking-[0.38em] text-white/90 group-hover:text-white uppercase pl-1 transition-colors">
            H A N D O F F I Q
          </h1>
          <span
            className="w-1.5 h-1.5 rounded-full inline-block ml-1 transition-colors duration-500"
            style={{
              backgroundColor: palette.primary,
              boxShadow: `0 0 8px ${palette.primary}`,
            }}
          />
        </div>

        {/* Mutation Lab Header Switcher */}
        {onSelectScreen && activeScreen !== 'lab' && (
          <button
            type="button"
            onClick={() => onSelectScreen('lab')}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-amber-300/80 hover:text-amber-200 bg-amber-950/20 hover:bg-amber-950/40 border border-amber-800/30 transition-colors"
            title="Open Handoff Mutation Lab workbench"
          >
            <FlaskConical className="w-3 h-3" />
            <span className="hidden sm:inline">Mutation Lab</span>
          </button>
        )}
      </div>

      {/* Right horizontal line */}
      <div className="flex-1 h-[1px] bg-gradient-to-l from-transparent to-white/20" />
    </header>
  );
};
