import React from 'react';
import { AgentPalette, ScreenId } from '../types/agent';
import { Plus } from 'lucide-react';

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
  const isInput = activeScreen === 'input';
  return (
    <header className={`relative z-10 ${isInput ? 'pt-3 pb-1 sm:pt-4 sm:pb-1.5' : 'pt-5 pb-2'} px-6 max-w-5xl mx-auto flex items-center justify-between gap-4`}>
      {/* Wordmark Navigation */}
      <div
        onClick={() => onSelectScreen?.('input')}
        className="flex items-center gap-1.5 cursor-pointer group select-none"
        title="Return to Task Input"
      >
        <h1 className="text-xs sm:text-sm font-semibold tracking-[0.38em] text-[#171A35] group-hover:text-[#7664E8] uppercase pl-1 transition-colors">
          H A N D O F F I Q
        </h1>
        <span
          className="w-1.5 h-1.5 rounded-full inline-block ml-1 transition-colors duration-500"
          style={{
            backgroundColor: palette.primary,
            boxShadow: `0 0 6px ${palette.primary}60`,
          }}
        />
      </div>

      {/* Decorative center divider */}
      <div className="flex-1 h-[1px] bg-gradient-to-r from-[#DFE1F2] via-[#DFE1F2]/50 to-transparent hidden sm:block" />

      {/* Visible New Task Button matching reference */}
      {activeScreen !== 'input' && (
        <button
          type="button"
          onClick={() => onSelectScreen?.('input')}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#171A35] bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] transition-all active:scale-[0.98] select-none shadow-sm"
          title="Start a new task without deleting previous work"
        >
          <Plus className="w-3.5 h-3.5 text-[#737895]" />
          <span>New Task</span>
        </button>
      )}
    </header>
  );
};
