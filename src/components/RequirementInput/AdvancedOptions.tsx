import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sliders } from 'lucide-react';
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
    <div className="w-full mt-2 border-t border-[#DFE1F2] pt-2">
      {/* Disclosure Trigger Button */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex items-center gap-2 text-xs text-[#737895] hover:text-[#171A35] transition-colors py-1 focus:outline-none rounded px-1"
      >
        <Sliders className="w-3.5 h-3.5" style={{ color: palette.primary }} />
        <span className="font-medium tracking-wide">Advanced options</span>
        <span className="text-[11px] font-mono text-[#737895] ml-1 select-none">{isOpen ? "[-]" : "[+]"}</span>
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
                <label className="text-[11px] font-medium text-[#171A35] block">
                  Preferred framework / stack
                </label>
                <select
                  value={config.framework}
                  onChange={(e) => onChange({ framework: e.target.value })}
                  className="w-full bg-[#FAF9FC] border border-[#DFE1F2] rounded-xl px-3 py-1.5 text-[#171A35] text-xs focus:outline-none focus:border-[#7664E8] transition-all cursor-pointer shadow-sm"
                >
                  {FRAMEWORK_OPTIONS.map((f) => (
                    <option key={f} value={f} className="bg-white text-[#171A35]">
                      {f}
                    </option>
                  ))}
                </select>
              </div>

              {/* Technical Constraints */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium text-[#171A35] block">
                  Additional constraints (optional)
                </label>
                <input
                  type="text"
                  value={config.constraints}
                  onChange={(e) => onChange({ constraints: e.target.value })}
                  placeholder="e.g. Strict 60 FPS, WebGL, WCAG AA, Sub-200ms API"
                  className="w-full bg-[#FAF9FC] border border-[#DFE1F2] rounded-xl px-3 py-1.5 text-[#171A35] text-xs placeholder:text-[#737895]/50 focus:outline-none focus:border-[#7664E8] transition-all shadow-sm"
                />
              </div>

              {/* Auto-repair Toggle */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF9FC] border border-[#DFE1F2]">
                <div>
                  <span className="text-[11px] text-[#171A35] block font-medium">
                    Automated self-healing
                  </span>
                  <span className="text-[10px] text-[#737895] block">
                    Auto-patch test failures and rerun verification
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={config.autoRepair}
                  onChange={(e) => onChange({ autoRepair: e.target.checked })}
                  className="w-4 h-4 rounded border-[#DFE1F2] text-[#7664E8] focus:ring-0 cursor-pointer"
                />
              </div>

              {/* Backend Mode Selector */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF9FC] border border-[#DFE1F2]">
                <div>
                  <span className="text-[11px] text-[#171A35] block font-medium">
                    Execution mode
                  </span>
                  <span className="text-[10px] text-[#737895] block font-mono">
                    {isMockMode ? 'Interactive Demo Simulator' : 'Live FastAPI Backend (:8000)'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onToggleMockMode(!isMockMode)}
                  className="text-[10px] font-mono px-2.5 py-1 rounded-lg border border-[#DFE1F2] bg-white hover:bg-[#FAF9FC] text-[#171A35] transition-colors shadow-sm"
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
