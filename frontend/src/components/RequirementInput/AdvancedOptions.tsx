import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Sliders } from 'lucide-react';
import { AgentPalette } from '../../types/agent';

export interface AdvancedConfigState {
  framework: string;
  constraints: string;
  autoRepair: boolean;
}

interface AdvancedOptionsProps {
  isOpen: boolean;
  onToggle: () => void;
  config: AdvancedConfigState;
  onChange: (updated: Partial<AdvancedConfigState>) => void;
  palette: AgentPalette;
  isMockMode: boolean;
  onToggleMockMode: (val: boolean) => void;
}

const FRAMEWORK_OPTIONS = [
  'React / TypeScript',
  'Next.js (App Router)',
  'Python / FastAPI',
  'Node.js / Express',
  'No preference',
];

export const AdvancedOptions: React.FC<AdvancedOptionsProps> = ({
  isOpen,
  onToggle,
  config,
  onChange,
  palette,
  isMockMode,
  onToggleMockMode,
}) => {
  return (
    <div className="w-full mt-3 border-t border-white/10 pt-3">
      {/* Disclosure Trigger Button */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex items-center gap-2 text-xs text-white/50 hover:text-white/80 transition-colors py-1 focus:outline-none focus:ring-1 focus:ring-white/20 rounded px-1"
      >
        <Sliders className="w-3.5 h-3.5" style={{ color: palette.primary }} />
        <span className="font-medium tracking-wide">Advanced options</span>
        <ChevronDown
          className={`w-3.5 h-3.5 transition-transform duration-300 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Collapsible Content */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              duration: 0.28,
              ease: [0.23, 1, 0.32, 1], // Emil Kowalski UI ease-out
            }}
            className="overflow-hidden"
          >
            <div className="pt-3 pb-1 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {/* Preferred Framework */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/70 block">
                  Preferred framework / stack
                </label>
                <select
                  value={config.framework}
                  onChange={(e) => onChange({ framework: e.target.value })}
                  className="w-full bg-white/[0.03] border border-white/10 rounded px-2.5 py-1.5 text-white/90 text-xs focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/30 transition-all cursor-pointer"
                >
                  {FRAMEWORK_OPTIONS.map((f) => (
                    <option key={f} value={f} className="bg-neutral-900 text-white">
                      {f}
                    </option>
                  ))}
                </select>
              </div>

              {/* Technical Constraints */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-white/70 block">
                  Additional constraints (optional)
                </label>
                <input
                  type="text"
                  value={config.constraints}
                  onChange={(e) => onChange({ constraints: e.target.value })}
                  placeholder="e.g. Strict 60 FPS, WebGL, WCAG AA, Sub-200ms API"
                  className="w-full bg-white/[0.03] border border-white/10 rounded px-2.5 py-1.5 text-white/90 text-xs placeholder:text-white/25 focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/30 transition-all"
                />
              </div>

              {/* Auto-repair Toggle */}
              <div className="flex items-center justify-between p-2.5 rounded bg-white/[0.02] border border-white/5">
                <div>
                  <span className="text-[11px] text-white/80 block font-medium">
                    Automated self-healing
                  </span>
                  <span className="text-[10px] text-white/40 block">
                    Auto-patch test failures and rerun verification
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={config.autoRepair}
                  onChange={(e) => onChange({ autoRepair: e.target.checked })}
                  className="w-4 h-4 rounded bg-white/10 border-white/20 text-blue-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                />
              </div>

              {/* Backend Mode Selector */}
              <div className="flex items-center justify-between p-2.5 rounded bg-white/[0.02] border border-white/5">
                <div>
                  <span className="text-[11px] text-white/80 block font-medium">
                    Execution mode
                  </span>
                  <span className="text-[10px] text-white/40 block font-mono">
                    {isMockMode ? 'Interactive Demo Simulator' : 'Live FastAPI Backend (:8000)'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onToggleMockMode(!isMockMode)}
                  className="text-[10px] font-mono px-2 py-1 rounded border border-white/10 bg-white/5 hover:bg-white/10 text-white/70 transition-colors"
                >
                  {isMockMode ? 'Switch to Live API' : 'Switch to Demo Mode'}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
