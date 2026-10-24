import React from 'react';
import { Play, Loader2, Sliders } from 'lucide-react';
import {
  ExperimentConfig,
  MutationIntensity,
  MutationStrategy,
  MutationType,
} from '../../types/mutationLab';

interface ExperimentConfigBarProps {
  config: ExperimentConfig;
  onChange: (updated: Partial<ExperimentConfig>) => void;
  onRun: () => void;
  isRunning: boolean;
}

const INTENSITY_PRESETS: Array<{
  id: MutationIntensity;
  label: string;
  defaultCount: number;
  description: string;
}> = [
  {
    id: 'subtle',
    label: 'Subtle',
    defaultCount: 2,
    description: '1-2 low/medium drifts testing sensitivity',
  },
  {
    id: 'moderate',
    label: 'Moderate',
    defaultCount: 3,
    description: '3-4 typical real-world agent drifts',
  },
  {
    id: 'adversarial',
    label: 'Adversarial',
    defaultCount: 5,
    description: '5-6 aggressive mutations & boundary breaks',
  },
];

const MUTATION_TYPES_CATALOG: Array<{
  type: MutationType;
  label: string;
  description: string;
}> = [
  {
    type: 'missing',
    label: 'Missing requirement',
    description: 'Requirement omitted entirely from context payload',
  },
  {
    type: 'altered',
    label: 'Altered requirement',
    description: 'Drift in meaning, scope, or normative terms',
  },
  {
    type: 'added',
    label: 'Added requirement',
    description: 'Invented or unauthorized specifications',
  },
  {
    type: 'contradiction',
    label: 'Contradiction',
    description: 'Instructions directly opposing canonical contract',
  },
  {
    type: 'weakened',
    label: 'Constraint weakening',
    description: 'Safety boundaries, rates, or limits relaxed',
  },
  {
    type: 'ordering_loss',
    label: 'Ordering/context loss',
    description: 'Prerequisite dependencies and sequence stripped',
  },
];

export const ExperimentConfigBar: React.FC<ExperimentConfigBarProps> = ({
  config,
  onChange,
  onRun,
  isRunning,
}) => {
  const handleIntensityChange = (intensity: MutationIntensity) => {
    const preset = INTENSITY_PRESETS.find((p) => p.id === intensity);
    onChange({
      intensity,
      mutationCount: preset ? preset.defaultCount : 3,
    });
  };

  const toggleMutationType = (type: MutationType) => {
    const current = config.enabledMutationTypes;
    const exists = current.includes(type);
    if (exists) {
      if (current.length > 1) {
        onChange({ enabledMutationTypes: current.filter((t) => t !== type) });
      }
    } else {
      onChange({ enabledMutationTypes: [...current, type] });
    }
  };

  return (
    <div className="bg-neutral-950/70 border-b border-white/10 px-4 py-4 sm:px-6">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Top Line: Name, Strategy, Intensity Preset, Run Button */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
          {/* Experiment Name */}
          <div className="md:col-span-4 space-y-1">
            <label className="text-[11px] font-mono uppercase tracking-wider text-white/50 block">
              Experiment Name
            </label>
            <input
              type="text"
              value={config.name}
              onChange={(e) => onChange({ name: e.target.value })}
              className="w-full bg-neutral-900 border border-white/15 rounded px-3 py-1.5 text-xs text-white placeholder-white/30 focus:outline-none focus:border-blue-400 font-mono"
              placeholder="e.g. EXP-2026-MUT-01"
            />
          </div>

          {/* Mutation Strategy */}
          <div className="md:col-span-3 space-y-1">
            <label className="text-[11px] font-mono uppercase tracking-wider text-white/50 block">
              Mutation Strategy
            </label>
            <select
              value={config.strategy}
              onChange={(e) => onChange({ strategy: e.target.value as MutationStrategy })}
              className="w-full bg-neutral-900 border border-white/15 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-400 font-mono"
            >
              <option value="balanced_blend">Balanced Blend (All vectors)</option>
              <option value="targeted_boundary">Targeted Boundary Attack</option>
              <option value="semantic_distortion">Semantic Distortion & Drift</option>
              <option value="omission_pruning">Omission & Context Pruning</option>
              <option value="adversarial_injection">Adversarial Injection & Contradictions</option>
            </select>
          </div>

          {/* Intensity Preset Selector */}
          <div className="md:col-span-3 space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-mono uppercase tracking-wider text-white/50 block">
                Intensity Preset
              </label>
              <span className="text-[10px] font-mono text-white/40">
                {config.mutationCount} mutations
              </span>
            </div>
            <div className="grid grid-cols-3 bg-neutral-900 p-0.5 rounded border border-white/15">
              {INTENSITY_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleIntensityChange(preset.id)}
                  title={preset.description}
                  className={`py-1 text-[11px] font-mono rounded transition-colors ${
                    config.intensity === preset.id
                      ? 'bg-white/15 text-white font-medium shadow-sm'
                      : 'text-white/40 hover:text-white/80'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Run Button */}
          <div className="md:col-span-2">
            <button
              type="button"
              disabled={isRunning}
              onClick={onRun}
              className={`w-full flex items-center justify-center gap-2 py-1.5 px-4 rounded text-xs font-semibold transition-all duration-200 ${
                isRunning
                  ? 'bg-neutral-800 text-white/40 cursor-not-allowed border border-white/5'
                  : 'bg-blue-600 hover:bg-blue-500 text-white shadow-md active:scale-[0.98] border border-blue-400/30'
              }`}
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run Experiment</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Bottom Line: Mutation Types Multi-Select Grid */}
        <div className="pt-2 border-t border-white/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-white/50">
              <Sliders className="w-3 h-3" />
              <span>INJECTED MUTATION VECTORS:</span>
            </div>
            <span className="text-[10px] font-mono text-white/35">
              {config.enabledMutationTypes.length} active types
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {MUTATION_TYPES_CATALOG.map((item) => {
              const active = config.enabledMutationTypes.includes(item.type);
              return (
                <button
                  key={item.type}
                  type="button"
                  onClick={() => toggleMutationType(item.type)}
                  className={`flex flex-col text-left p-2 rounded border transition-colors ${
                    active
                      ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                      : 'bg-white/[0.02] border-white/5 text-white/40 hover:text-white/70 hover:border-white/10'
                  }`}
                  title={item.description}
                >
                  <span className="text-[11px] font-medium leading-tight truncate">
                    {item.label}
                  </span>
                  <span className="text-[9px] text-white/40 font-mono mt-0.5 truncate">
                    {item.type}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
