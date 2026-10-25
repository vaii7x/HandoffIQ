export type AgentId = 'research' | 'coding' | 'deploy';

export type ScreenId =
  | 'input'
  | 'research'
  | 'validate'
  | 'coding'
  | 'test'
  | 'deploy';

export type WorkflowStageNumber = 1 | 2 | 3 | 4 | 5;

export interface AgentPalette {
  id: AgentId;
  background: string;
  primary: string;
  secondary: string;
  text: string;
  muted: string;
  glow: string;
  threeColorPrimary: number;
  threeColorSecondary: number;
  threeColorGlow: number;
}

export interface AgentConfig {
  id: AgentId;
  label: string; // e.g. "AGENT 01"
  heading: string; // e.g. "Researching"
  supportingText: string;
  defaultStatus: string;
  stageNumber: WorkflowStageNumber;
  stageName: string; // e.g. "Research"
  fractionText: string; // e.g. "2/5"
  palette: AgentPalette;
  statusPhrases?: string[];
}
